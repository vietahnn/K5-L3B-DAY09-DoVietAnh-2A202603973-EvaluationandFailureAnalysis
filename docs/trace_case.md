# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, run_id: `run-seeded_regression-C-002-11` |
| Triệu chứng | Grader Lab 8 báo `FAIL (status resolved != denied)`; ledger ghi nhận hoàn 20.000đ trong khi label kỳ vọng 0đ. |
| Bước sai đầu tiên | Event 3: `model_override` payload: `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event 1 (`handoff`) và Event 2 (`investigator`) thực thi chính xác; `investigator.lookup_order` tra cứu từ DB chỉ ra `delay_days: 1`. Tại Event 3, agent tin lời khách khai trong ticket ("giao trễ 5 ngày") và đè dữ liệu DB. |
| Failure mode | `FM-03` (`ticket_trust`) |
| Đối chứng | Trên shape `fixed` (cùng claim C-002@seed 11), không xuất hiện event `model_override`; agent lấy `delay_days: 1` từ DB -> quote ra 0đ -> reply từ chối bồi thường (`denied`), khớp chính xác với nhãn. |
| Regression test | `test_override_event_breaks_db_fact` trong `tests/test_lab9_graders.py` (sử dụng grader `DbFactKept`). Đã kiểm tra thấy fail trên `seeded_regression` và pass trên `fixed`. |
| Chưa chắc chắn | Trace chỉ ghi nhận agent thực hiện override mà không thể hiện rõ LLM suy luận nội tâm (chain-of-thought) dẫn đến việc ưu tiên ticket hơn DB. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.
