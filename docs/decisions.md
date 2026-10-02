# Nhật ký quyết định & giả định (ADR rút gọn)

Mỗi mục: **bối cảnh → quyết định → hệ quả**. Bổ sung theo từng giai đoạn.

## Giai đoạn 0

### D-001. Monorepo hai hệ sinh thái: pnpm workspace + uv workspace

- **Bối cảnh:** frontend TypeScript và backend Python cần dùng chung hằng số (nhãn cảm xúc, ngôn ngữ) và chạy CI chung.
- **Quyết định:** `pnpm-workspace.yaml` gom `apps/web`, `packages/shared`; `pyproject.toml` gốc là **uv workspace** gom `apps/api`, `apps/worker`, `packages/nlp`. Một `uv.lock` và một `pnpm-lock.yaml` cho toàn repo.
- **Hệ quả:** worker import trực tiếp package `app` của API (cấu hình, model, service) — không lặp code. Hằng số dùng chung có test chéo ngôn ngữ (`packages/nlp/tests/test_labels.py` đọc `packages/shared/src/sentiments.json`).

### D-002. Một image Python cho api / worker / beat

- **Quyết định:** `infra/docker/python.Dockerfile` build một image `lys/backend`, ba service khác nhau ở lệnh chạy.
- **Hệ quả:** build một lần, phiên bản code luôn đồng nhất giữa API và worker. Phụ thuộc NLP nặng (torch, transformers) sẽ nằm trong extra `ml` của `lys-nlp` (GĐ 6); nếu image quá lớn sẽ tách image `worker-nlp` riêng.

### D-003. i18n không dùng tiền tố URL

- **Bối cảnh:** link khảo sát công khai `/s/{slug}` phải ổn định (in lên QR, hóa đơn).
- **Quyết định:** next-intl chế độ "without i18n routing": ngôn ngữ giao diện lấy từ cookie `NEXT_LOCALE`, mặc định `vi`. Bản dịch nằm ở `packages/shared/i18n/{vi,en}.json`; khóa dịch được kiểm tra kiểu (TypeScript) và kiểm tra khớp khóa vi/en (script + Vitest + pre-commit).
- **Hệ quả:** trang đọc cookie nên render động (SSR) thay vì static. Chấp nhận được vì FR-09 yêu cầu SSR/ISR; nếu cần ISR cho trang khách sẽ tách layout riêng không đọc cookie (ngôn ngữ khảo sát do nhà tạo cấu hình — GĐ 10).

### D-004. Font Be Vietnam Pro tự host qua `@fontsource`

- **Quyết định:** không dùng `next/font/google` (cần mạng lúc build); dùng gói `@fontsource/be-vietnam-pro` — file font nằm trong `node_modules`, được bundle và phục vụ cùng ứng dụng, có `unicode-range` để trình duyệt chỉ tải subset cần thiết (vietnamese/latin).
- **Hệ quả:** build được trong mạng đóng; không gọi Google Fonts từ trình duyệt người dùng (tốt cho quyền riêng tư).

### D-005. Mailpit thay MailHog

- **Bối cảnh:** tài liệu yêu cầu MailHog khi dev; image MailHog không còn được bảo trì và không có bản ARM (máy Mac M-series phải giả lập).
- **Quyết định:** dùng `axllent/mailpit` — tương thích hoàn toàn (SMTP `1025`, giao diện `8025`).
- **Hệ quả:** service trong Compose tên `mailpit`. Mã gửi mail đi qua lớp `EmailProvider` (GĐ 2) nên đổi nhà cung cấp không ảnh hưởng nghiệp vụ.

### D-006. Định dạng lỗi API thống nhất

- **Quyết định:** mọi lỗi trả `{"error": {"code", "message", "details?", "request_id"}}`. `code` là mã ổn định (frontend có thể dịch theo mã), `message` mặc định tiếng Việt. Lỗi không bắt được → 500 `INTERNAL_ERROR`, không lộ stack trace; stack trace chỉ ghi vào log phía server kèm `request_id`.
- **Hệ quả:** có test đảm bảo không rò rỉ chi tiết nội bộ (`apps/api/tests/test_errors.py`).

### D-007. Middleware ASGI thuần, không dùng `BaseHTTPMiddleware`

- **Lý do:** `BaseHTTPMiddleware` làm hỏng streaming (SSE cho dashboard ở GĐ 9) và contextvars.
- **Hệ quả:** request-id, access log JSON, header bảo mật đều là middleware ASGI thuần.

### D-008. Health-check hai mức

- `GET /health` — liveness (tiến trình sống), dùng cho Docker healthcheck, không phụ thuộc DB.
- `GET /health/ready` và `GET /api/v1/health` — readiness: kiểm tra PostgreSQL + Redis song song, có timeout; trả 503 khi `degraded`, chỉ báo **tên loại lỗi** (không lộ thông tin hạ tầng). `nlp/health` bổ sung ở GĐ 6.

### D-009. nginx giữ nguyên `Host` kèm cổng

- **Bối cảnh:** test E2E qua nginx phát hiện Next.js từ chối Server Action vì `X-Forwarded-Host` (`localhost`) khác `Origin` (`localhost:8080`).
- **Quyết định:** nginx chuyển `Host`/`X-Forwarded-Host` bằng `$http_host`.

### D-010. nginx phân giải lại tên service động

- **Bối cảnh:** khi container `web`/`api` được tạo lại (đổi IP), nginx vẫn giữ IP cũ đã phân giải lúc khởi động → 502.
- **Quyết định:** `resolver 127.0.0.11` (DNS của Docker) + `server … resolve` trong `upstream` có `zone` (hỗ trợ trong nginx OSS ≥ 1.27.3), vẫn giữ keepalive.
- **Hệ quả:** deploy lại từng service không cần khởi động lại nginx; sẵn sàng `--scale api=N`.

### D-011. CA tùy chọn khi build Docker sau proxy TLS

- **Quyết định:** Dockerfile nhận BuildKit secret **tùy chọn** `ca_bundle` (`--secret id=ca_bundle,src=...`) chỉ dùng trong bước tải phụ thuộc; không có secret thì build bình thường. CA không bị ghi vào image.
- **Hệ quả:** build được trong mạng doanh nghiệp có proxy kiểm tra TLS mà không sửa Dockerfile.

### D-012. Phiên bản công cụ

- TypeScript **6.0** (chưa lên 7.0 vì `typescript-eslint` hiện hỗ trợ `<6.1`), ESLint **9** (plugin React chưa hỗ trợ ESLint 10).
- SQLAlchemy dải `>=2.0.40,<2.2` (2.1 tương thích API 2.0 async như tài liệu yêu cầu).
- Client test HTTP cho FastAPI dùng `httpx2` (Starlette mới khuyến nghị thay `httpx`).

### D-013. Dữ liệu minh họa ở Giai đoạn 0

- Trang "Khảo sát của tôi", bộ chọn workspace, menu người dùng và thư viện giao diện dùng **dữ liệu minh họa** (`apps/web/src/lib/demo-data.ts`), có ghi chú rõ trên giao diện. Sẽ thay bằng API thật ở GĐ 2 (workspace, người dùng) và GĐ 4 (khảo sát).
- Số liệu ở landing page mô tả **khả năng sản phẩm** (số loại câu hỏi, số bộ chủ đề…), không phải số liệu khách hàng — có dòng chú thích ngay dưới.

### Giả định

- Tên thương hiệu placeholder: **"LyS Survey"** — đổi qua `APP_NAME` / `NEXT_PUBLIC_APP_NAME`; logo là chữ viết tắt sinh tự động (`apps/web/src/components/layout/logo.tsx`).
- Màu chủ đạo: xanh chàm `oklch(0.5 0.19 265)` trong biến CSS `--primary` (`apps/web/src/app/globals.css`).
- Múi giờ hiển thị mặc định `Asia/Ho_Chi_Minh`; lưu trữ thời gian ở UTC.
- Cổng truy cập mặc định `8080` (tránh xung đột cổng 80); đổi bằng `HTTP_PORT`.
