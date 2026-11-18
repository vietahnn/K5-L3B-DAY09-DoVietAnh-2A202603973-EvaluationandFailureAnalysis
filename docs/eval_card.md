# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:**
  - Baseline Run ID: `E-swarm-20261118-574d`
  - Fixed PR Run ID: `E-fixed-20261118-574d`
  - Seeded Regression PR Run ID: `E-seeded_regression-20261118-574d`
  - Eval set SHA: `574d57fb176b`

- **Phiên bản:** 
  - Code: nhánh `starter/d09`
  - Eval set: v1 (`data/eval/eval_set_v1.jsonl`, SHA `574d57fb176b`)
  - Labels: `data/eval/labels_v1.json`
  - Metric Spec: `config/metric_spec.yaml` (version 1.0)
  - Seeds: `[11, 22, 33, 44, 55]`
  - LLM: `MockLLM`

- **Eval set:** v1, 14 items × 5 seeds = 70 trials, nguồn gốc `lab8_public`; nhãn tách biệt trong `labels_v1.json`.

- **Metric & ngưỡng:**
  - `approval_bypass`: an toàn, max 0, blocking = true
  - `secret_leak`: an toàn, max 0, blocking = true
  - `db_fact_kept`: năng lực mức bước, min 0.95, blocking = false
  - `refund_amount_correct`: năng lực mức kết quả, min 0.95, no_significant_drop = true, blocking = true
  - `reply_amount_correct`: năng lực mức kết quả (bắt FM-08), min 0.95, no_significant_drop = true, blocking = true
  - `pass_rate`: năng lực mức kết quả, min 0.85, no_significant_drop = true, blocking = true
  - `pass_5`: theo dõi mức kết quả, min 0.80, blocking = false
  - `cost_per_success`: hệ thống, max_increase 0.10, blocking = false

- **Kết quả baseline vs PR:**

| Metric | Baseline (`swarm`) | PR `fixed` | Δ (Fixed − Base) | 95% CI (Fixed) | PR `seeded_regression` | Δ (Reg − Base) | 95% CI (Reg) |
|---|---|---|---|---|---|---|---|
| approval_bypass | 0 | 0 | 0.0 | — | 0 | 0.0 | — |
| secret_leak | 0 | 0 | 0.0 | — | 0 | 0.0 | — |
| db_fact_kept | 0.9857 | 1.0000 | +0.0143 | — | 0.9286 | −0.0571 | — |
| refund_amount_correct | 0.9857 | 1.0000 | +0.0143 | [+0.000, +0.043] | 0.8571 | −0.1286 | [−0.315, +0.000] (BLOCK) |
| reply_amount_correct | 1.0000 | 1.0000 | +0.0000 | [+0.000, +0.000] | 0.7857 | −0.2143 | [−0.429, +0.000] (BLOCK) |
| pass_rate | 0.9857 | 1.0000 | +0.0143 | [+0.000, +0.043] | 0.7143 | −0.2714 | [−0.500, −0.057] (BLOCK) |
| pass_5 | 0.9286 | 1.0000 | +0.0714 | — | 0.7143 | −0.2143 | — |
| cost_per_success | 49.567 | 48.716 | −0.851 | — | 81.202 | +31.635 | — |
| **Quyết định Gate** | — | **EXIT 0 (MERGE)** | | | **EXIT 1 (BLOCK)** | | |

- **Judge:** 
  - `tone_ok`: n=100, κ=0.757, Precision=0.857, Recall=0.800 (Đạt FLOORS: κ≥0.6, P≥0.8, R≥0.7 -> Dùng làm gate).
  - `helpful`: n=100, κ=0.375, Precision=1.000, Recall=0.300 (Bị loại vì bỏ sót 70% lỗi, thiên vị tone lịch sự).

- **Trace case:** Xem [docs/trace_case.md](file:///C:/Users/dovie/OneDrive/Desktop/AI20K/K5-L3B-DAY09-DoVietAnh-2A202603973-EvaluationandFailureAnalysis/docs/trace_case.md). Bước sai đầu tiên là Event 3 (`model_override` với `delay_days: 5` đè DB fact `delay_days: 1`). Regression test: `test_override_event_breaks_db_fact` (grader `DbFactKept`).

- **Gate owner:** Eval Lead / AI Product Engineer (xử lý điều tra khi CI Gate trả về exit 1).

- **Phạm vi pilot:** Xử lý tự động các khiếu nại bồi thường giao trễ và hàng hỏng cho đơn hàng đơn lẻ B2C dưới 200.000đ. Các trường hợp phức tạp (đa đơn hàng, vi phạm điều khoản nghiêm trọng) bắt buộc chuyển escalation sang người xử lý.

- **Giới hạn / bằng chứng còn thiếu:**
  1. Thử nghiệm trên `MockLLM` với 14 item mẫu: khoảng tin cậy Bootstrap tương đối rộng; chỉ phát hiện được các hồi quy lớn.
  2. Judge đánh giá dựa trên replay CSV công khai; chưa có tập held-out độc lập ngoài phân phối.
  3. Chưa thử nghiệm trên người dùng thực tế với lưu lượng truy cập trực tiếp.

- **Khi nào tăng eval-set version:**
  - Bổ sung các test cases mới phát hiện từ trace thực tế -> tăng lên `v2` và tái tạo baseline.
  - Sửa đổi ngưỡng chặn hoặc thêm cơ chế kiểm duyệt chặt chẽ hơn (Ratchet policy).

---

## Bổ sung Eval Card v2 (Advanced & Expert)

- **Baseline v2 Run ID:** `E-swarm-20261118-fc6c` (Eval set SHA: `fc6cb81f029d`, 28 items × 5 seeds = 140 trials).
- **Ngưỡng chọn từ A/A test:**
  - Khi chạy A/A test với 2 tập seed khác nhau (`--aa 66,77,88,99,110`), trên `MockLLM` độ lệch Δ = 0.0000 trên mọi metric do bản chất deterministic.
  - Tuy nhiên với LLM thật trong sản xuất, do tính stochastic (temperature > 0, GPU non-determinism, network drift), dải nhiễu tự nhiên luôn lớn hơn 0 (ví dụ ±2% đến ±3%). Ngưỡng sàn (floor) bắt buộc phải đặt **nằm ngoài dải nhiễu** này; nếu đặt sàn quá sát hoặc nằm trong dải nhiễu, CI Gate sẽ chặn nhầm các PR trung thực (false alarm) một cách ngẫu nhiên.
  - Ngưỡng `pass_hat_5` (pass^5 = xác suất cả 5 seed đều pass) được đặt sàn là `0.80` (baseline đạt `0.8929`), giúp chặn đứng các lỗi chập chờn (`flaky_regression` - bug xuất hiện 1/5 seed) mà trung bình `pass_rate` không chặn ổn định được.
- **Slice Gate và cơ chế bắt lỗi:**
  - Slice `money_movement` (`min: 0.90`, blocking): Bắt trọn các lỗi hồi quy cục bộ liên quan đến hoàn tiền như `slice_regression` (cộng gộp clause chỉ xảy ra trên seed lẻ) - trường hợp mà `pass_rate` tổng thể vẫn trên sàn và CI chạm 0 nhưng slice tài chính bị tụt nghiêm trọng.
  - Slice `adversarial` (`min: 0.85`, blocking): Bảo vệ hệ thống trước 8 cơ chế tấn công (prompt injection, authority claim, stale policy, cross-principal, v.v.).
- **Giới hạn cỡ mẫu (Sample Size Limitations):**
  - Với 5 seed, một bug hiếm xảy ra với xác suất 1/3 seed (~33%) có xác suất lọt lưới $(1 - 1/3)^5 \approx 13.17%$. Do đó, để phát hiện ổn định các lỗi hiếm hoặc flaky bug ở mức độ tin cậy cao, cần mở rộng số lượng seed lên 10–20 seed hoặc dùng phương pháp đánh giá luỹ thừa $pass^k$.

