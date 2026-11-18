# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | ĐẠT (κ≥0.6, P≥0.8, R≥0.7) | Dùng làm gate |
| helpful | 100 | 0.375 | 1.000 | 0.300 | KHÔNG ĐẠT (Recall 0.3 < 0.7; κ 0.375 < 0.6) | Loại bỏ, không được làm gate |

## ≥5 case audit thủ công (từ `judge_helpful_public.csv` và `judge_tone_public.csv`)

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | HL-015 | PASS | FAIL | Người đúng | Câu trả lời chỉ thông báo hoàn tiền ngắn gọn nhưng không giải thích nguyên nhân hoặc bước tiếp theo, không giải quyết thắc mắc chính của khách hàng. Judge bị lừa bởi tone lịch sự. |
| 2 | HL-016 | PASS | FAIL | Người đúng | Câu trả lời chỉ là văn mẫu xin lỗi sáo rỗng ("rất trân trọng sự kiên nhẫn...") mà không đưa ra bất kỳ hành động giải quyết cụ thể nào. Judge thiên vị câu từ lịch sự (sycophancy / politeness bias). |
| 3 | HL-020 | PASS | FAIL | Người đúng | Hoàn tiền nhưng không trả lời khiếu nại về hàng bị vỡ/hỏng mà khách nêu trong ticket. Phản hồi thiếu thông tin cần thiết. |
| 4 | HL-028 | PASS | FAIL | Người đúng | Văn mẫu xin lỗi lặp lại, không cung cấp trạng thái thực tế của đơn hàng. Judge chấm PASS vì không phát hiện được sự thiếu hụt thông tin (omission). |
| 5 | H-008 | PASS | FAIL | Người đúng | "Em đã hoàn tiền cho anh rồi nha, anh check giúp em" — Giọng điệu quá suồng sã, thiếu chuẩn mực dịch vụ chuyên nghiệp của doanh nghiệp logistics B2C. Rubric về tone cần làm rõ quy chuẩn xưng hô. |

## Kết luận
- **Tiêu chí bị loại và lý do**: 
  - `judge_helpful` bị loại hoàn toàn khỏi pipeline thẩm định và gate kiểm duyệt.
  - Ma trận nhầm lẫn của `judge_helpful`: `{'tp': 9, 'fp': 0, 'fn': 21, 'tn': 70}`. 
  - Dù Precision đạt 1.0 (khi bắt lỗi thì chắc chắn đúng), nhưng Recall chỉ đạt 0.30 (bỏ lọt 21/30 trường hợp câu trả lời vô dụng, tỉ lệ bỏ sót lỗi lên tới 70%). Hệ số thỏa thuận Cohen's $\kappa = 0.375$ quá thấp so với sàn 0.6. Nếu dùng judge này làm gate, hệ thống sẽ để lọt hàng loạt phản hồi kém chất lượng ra cho khách hàng.
  - **Hướng sửa Rubric**: Cần định nghĩa chi tiết tiêu chí "helpful" thành các câu hỏi cụ thể dạng checklist: (1) Đã giải quyết đúng vấn đề khách hỏi chưa? (2) Có mốc thời gian/bước tiếp theo rõ ràng không? (3) Không chấp nhận câu trả lời chỉ có lời xin lỗi mà không kèm hành động.
- **Rủi ro còn lại**: 
  - Judge chỉ được kiểm chuẩn trên tập dữ liệu replay đã công khai (`judge_tone_public.csv`); khi gặp các mẫu prompt mới ngoài phân phối (OOD), độ tin cậy có thể suy giảm. Cần thu thập nhãn chuyên gia định kỳ để tạo tập kiểm thử ẩn (held-out validation set) thực sự.
