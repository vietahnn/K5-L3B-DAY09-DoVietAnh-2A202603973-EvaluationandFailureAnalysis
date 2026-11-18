"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate."""
    problems: list[str] = []

    # 1. Any metric value in pr["metrics"] that is NaN or inf
    for k, v in (pr.get("metrics") or {}).items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            problems.append(f"metric {k} is NaN or Inf")

    # 2. Row count matches manifest items x len(manifest seeds)
    manifest = pr.get("manifest") or {}
    expected_rows = manifest.get("items", 0) * len(manifest.get("seeds") or [])
    rows = pr.get("rows") or []
    if len(rows) != expected_rows:
        problems.append(f"row count {len(rows)} != manifest expected {expected_rows}")

    # 3. The (item_id, seed) set of PR differs from the baseline's
    pr_keys = {(r.get("item_id"), r.get("seed")) for r in rows}
    base_rows = base.get("rows") or []
    base_keys = {(r.get("item_id"), r.get("seed")) for r in base_rows}
    if pr_keys != base_keys:
        problems.append("PR (item_id, seed) set differs from baseline")

    # 4. Evaluator failures non-empty or row has None for a graded spec metric
    if pr.get("evaluator_failures"):
        problems.append("evaluator_failures non-empty")

    graded_metrics = {
        m["id"] for m in spec.get("metrics") or []
        if m.get("grader") not in ("lab8.metrics.summarize", "lab8.metrics.trial_pass")
    }
    for r in rows:
        for mid in graded_metrics:
            if mid in r and r[mid] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} has None for graded metric {mid}")
                break

    # 5. Item slice tags differ from baseline's
    base_slices = {
        (r.get("item_id"), r.get("seed")): tuple(sorted(r.get("slices") or []))
        for r in base_rows
    }
    for r in rows:
        k = (r.get("item_id"), r.get("seed"))
        if k in base_slices and tuple(sorted(r.get("slices") or [])) != base_slices[k]:
            problems.append(f"item {k[0]}@{k[1]} changed slice tags compared to baseline")
            break

    # 6. Ratchet check when base_spec is provided (or if same eval_set_version)
    check_spec = base_spec
    if check_spec is not None and check_spec.get("eval_set_version") == spec.get("eval_set_version"):
        base_m_map = {m["id"]: m for m in check_spec.get("metrics", [])}
        spec_m_map = {m["id"]: m for m in spec.get("metrics", [])}
        for mid, bm in base_m_map.items():
            if mid not in spec_m_map:
                problems.append(f"metric {mid} dropped from spec (ratchet violation)")
                continue
            sm = spec_m_map[mid]
            if bm.get("blocking") and not sm.get("blocking"):
                problems.append(f"blocking metric {mid} made non-blocking (ratchet violation)")
            b_th = bm.get("threshold", {})
            s_th = sm.get("threshold", {})
            if "min" in b_th and s_th.get("min", float("-inf")) < b_th["min"]:
                problems.append(f"metric {mid} min threshold loosened from {b_th['min']} to {s_th.get('min')}")
            if "max" in b_th and s_th.get("max", float("inf")) > b_th["max"]:
                problems.append(f"metric {mid} max threshold loosened")
            if b_th.get("no_significant_drop") and not s_th.get("no_significant_drop"):
                problems.append(f"metric {mid} dropped no_significant_drop (ratchet violation)")

        base_s_map = {s["name"]: s for s in check_spec.get("slices", [])}
        spec_s_map = {s["name"]: s for s in spec.get("slices", [])}
        for sname, bs in base_s_map.items():
            if sname not in spec_s_map:
                problems.append(f"slice {sname} dropped from spec (ratchet violation)")
                continue
            ss = spec_s_map[sname]
            if bs.get("blocking") and not ss.get("blocking"):
                problems.append(f"slice {sname} made non-blocking")
            if "min" in bs and ss.get("min", float("-inf")) < bs["min"]:
                problems.append(f"slice {sname} min threshold loosened")
            if bs.get("no_significant_drop") and not ss.get("no_significant_drop"):
                problems.append(f"slice {sname} dropped no_significant_drop")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})

    for sl in spec.get("slices", []):
        name = sl["name"]
        metric = sl["metric"]
        min_val = sl.get("min")
        blocking = sl.get("blocking", True)
        slice_id = f"slice:{name}/{metric}"

        pr_items = per_item(pr, metric, slice_name=name)
        val = sum(pr_items.values()) / len(pr_items) if pr_items else None
        verdict = "ok"
        note = ""

        if val is None:
            verdict = "missing"
        elif min_val is not None and val < min_val:
            verdict = "fail"

        if sl.get("no_significant_drop") and val is not None:
            base_items = per_item(base, metric, slice_name=name)
            keys = sorted(set(pr_items) & set(base_items))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [pr_items[k] for k in keys],
                    [base_items[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        if verdict != "ok" and blocking:
            blocked.append(slice_id)

        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if blocking else "warn")
        val_str = f"{round(val, 4)}" if val is not None else "None"
        th_str = json.dumps({k: v for k, v in sl.items() if k not in ("name", "metric", "blocking")})
        lines.append(f"  {slice_id:<28} {val_str:<8} {th_str:<34} {note:<28} {label}")

    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
