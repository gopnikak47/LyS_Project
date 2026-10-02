# lys-nlp — Pipeline NLP tiếng Việt

Gói Python dùng chung cho API và worker. Kế hoạch (Giai đoạn 6):

| Module | Nội dung | FR |
|---|---|---|
| `preprocess` | NFC, chữ thường có kiểm soát, bỏ HTML/URL, rút gọn ký tự lặp, emoji → token, teencode, tách câu/tách từ | FR-14 |
| `sentiment` | PhoBERT fine-tune 3 lớp + temperature scaling, phân tích theo câu rồi tổng hợp | FR-15 |
| `topics` | Multi-label: prototype embedding (zero-shot) + classifier theo workspace | FR-16 |
| `urgency` | Từ điển cụm từ theo workspace + điểm tiêu cực cao, ghi `urgent_reasons` | FR-17 |
| `scripts/train.py`, `evaluate.py`, `retrain.py` | Huấn luyện, đánh giá (accuracy, macro-F1, confusion matrix), huấn luyện lại từ nhãn đã sửa | NFR |

Phụ thuộc nặng (`torch`, `transformers`, `underthesea`) sẽ nằm trong extra `ml`
để image API không phải tải về.
