# Vận hành và khôi phục

Chạy `docker compose up -d --build` sau khi sao chép `.env.example` sang `.env` và cấu hình secrets.
Production cần HTTPS tại reverse proxy, domain/CORS chính xác và SMTP thật. Không public cổng
PostgreSQL/Redis. Backup chứa dữ liệu cá nhân: mã hóa volume/object storage, chỉ cấp quyền cho
người vận hành và ghi nhật ký truy cập. Không commit `.env`, dump hay model khách hàng.

## Sao lưu

`docker compose --profile backup up -d backup` tạo dump custom mỗi 24 giờ, kiểm tra mục lục,
ghi checksum và giữ 14 bản thành công. `make backup` tạo ngay một bản. Thiết lập BACKUP_KEEP
và BACKUP_INTERVAL_SECONDS trong `.env`. Sao chép backup ra máy khác; volume cùng máy không
bảo vệ khi mất ổ đĩa. Sao lưu cả volume `storage` và model artifacts cùng thời điểm dừng ghi
nếu cần khôi phục nhất quán các tệp. Dump PostgreSQL riêng không chứa tệp upload/export.

## Khôi phục

Thực hành trên database thử nghiệm trước khi dùng production. Ghi lại commit ứng dụng và
phiên bản Alembic của bản sao lưu. Dừng `api worker beat`, tạo database đích rỗng; role `lys_rls`
phải tồn tại (chạy migration bootstrap trước nếu server mới). Chọn dump và kiểm tra checksum:

```sh
docker compose stop api worker beat
docker compose --profile backup run --rm -e RESTORE_CONFIRM=lys backup sh /scripts/restore.sh /backups/lys-TIMESTAMP.dump
docker compose run --rm migrate
docker compose up -d api worker beat
```

Restore dùng một transaction và dừng ở lỗi đầu tiên. Kiểm tra `/api/v1/health`, đăng nhập,
tenant isolation, số lượng phản hồi và một báo cáo trước khi mở traffic. Workflow nghiệm thu có bước kiểm tra restore trên PostgreSQL thử nghiệm; bước này
chưa được chạy nếu GitHub CLI chưa có quyền workflow. Không tự restore database của người dùng.

## Xóa dữ liệu theo yêu cầu

Admin dùng `DELETE /api/v1/privacy/responses/{id}` với body `confirm_response_id` khớp ID,
sau khi xác minh yêu cầu ngoài hệ thống. Xóa phản hồi, câu trả lời, nhãn/lịch sử và ticket;
thu hồi toàn bộ export/import của workspace để tránh tải lại hoặc nhập lại bản cũ.
Tệp nguồn, export đã thu hồi và upload được xóa sau commit DB. Theo dõi log
`erasure_file_cleanup_failed` để xử lý lỗi filesystem; dọn cả tệp tạm/báo cáo lỗi từng lô trong
cửa sổ bảo trì. Người vận hành xử lý bản tải về/email/backup theo chính sách lưu giữ.
Nếu restore backup trước thời điểm xóa, phải áp dụng lại nhật ký `privacy.erase` trước khi mở
traffic. Không coi thao tác DB là đã xóa mọi bản sao ngoài hệ thống.

## NLP, upload và hàng đợi

PhoBERT cần artifact đã fine-tune và metadata/calibration. Không có artifact: phản hồi thô
vẫn lưu; analysis thất bại/retry có giới hạn. `NLP_BACKEND=rules` chỉ dùng demo, không chứng
minh accuracy production. Docker bật `NLP_WITH_ML=true` để cài extra `ml`, đặt `NLP_MODEL_PATH=/data/models`
trong Compose và `NLP_MODEL_HOST_DIR=./var/models` để mount artifact read-only. Chạy ngoài
Docker dùng `uv sync --all-packages --all-extras` và đường dẫn artifact thật. Đây là dependency
build tùy chọn vì Torch/transformers lớn; ảnh mặc định chưa chứa chúng.
Upload khách yêu cầu ClamAV; bật profile `uploads` và đặt `UPLOAD_SCANNER_HOST=clamav`.
Email là at-least-once; theo dõi outbox lỗi và job quá lâu, không xóa Redis khi còn task.
Dashboard `/observability`, Prometheus `/metrics` chỉ dành admin. Kiểm tra quyền tenant và
scope workspace trên mọi tài nguyên có ID; role `lys_rls` không được BYPASSRLS.

## Nghiệm thu còn phụ thuộc môi trường

Chạy `make lint test e2e`, CI Docker build và dependency audit. Benchmark 100k phản hồi,
import 10k dòng, model accuracy ≥80%, fine-tune trên corpus thực, tải public JS và khả năng
phục hồi ngoài máy cần số đo riêng. CSV demo không đủ để xác nhận các tiêu chí đó.
