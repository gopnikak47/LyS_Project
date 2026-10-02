# Nhật ký tiến độ & yêu cầu chức năng (FR)

## Trạng thái giai đoạn

| GĐ    | Nội dung                                                                              | Trạng thái                |
| ----- | ------------------------------------------------------------------------------------- | ------------------------- |
| 0     | Monorepo, Docker Compose, lint/CI, `.env.example`, design system + layout khung, i18n | ✅ Hoàn thành — chờ duyệt |
| 1     | CSDL, migration, ERD, RLS                                                             | ⏳                        |
| 2     | Auth, tenant, workspace, thành viên, phân quyền (FR-01→04)                            | ⏳                        |
| 3     | Chủ đề theo workspace + bộ mẫu (FR-12→13)                                             | ⏳                        |
| 4     | Survey engine P0, link + QR (FR-05→06)                                                | ⏳                        |
| 5     | Trang khách, chống spam, voucher (FR-08→11)                                           | ⏳                        |
| 6     | NLP pipeline + Celery + dự phòng + evaluate (FR-14→17)                                | ⏳                        |
| 7     | Import CSV/Excel (FR-07)                                                              | ⏳                        |
| 8     | Danh sách phản hồi, sửa nhãn, chất lượng mô hình (FR-18→20)                           | ⏳                        |
| 9     | Dashboard, xu hướng, word cloud, xuất Excel/PDF, SSE (FR-21→24)                       | ⏳                        |
| 10–14 | P1 mở rộng & hoàn thiện                                                               | ⏳                        |

## Giai đoạn 0 — chi tiết

**Tiêu chí hoàn thành:** `docker compose up` chạy; trang mẫu hiển thị đúng; ảnh chụp lưu `docs/screenshots/`.

- [x] Monorepo pnpm + uv workspace; `CLAUDE.md` chứa đặc tả.
- [x] Docker Compose 8 service (`web`, `api`, `worker`, `beat`, `postgres`, `redis`, `mailpit`, `nginx`), healthcheck + restart policy + graceful shutdown cho từng service.
- [x] API khung: cấu hình qua env, log JSON, request-id, lỗi chuẩn hóa tiếng Việt, header bảo mật, CORS, health/readiness.
- [x] Celery: `acks_late`, `reject_on_worker_lost`, prefetch 1, chỉ JSON; hàng đợi `default` và `nlp`; beat heartbeat.
- [x] Design system: token màu (1 màu chủ đạo + Xanh/Đỏ/Xám/Cam ngữ nghĩa), dark mode, bo góc 12–14px, Be Vietnam Pro tự host.
- [x] Layout khung: landing (header cố định, hero, tab tính năng, 3 bước, số liệu, FAQ, footer), đăng nhập/đăng ký (UI + validate), khu quản trị (thanh trên, chọn workspace, menu người dùng, "Khảo sát của tôi"), thư viện giao diện (nút, nhãn, KPI, bảng, form, skeleton, rỗng/lỗi), 404, error boundary.
- [x] i18n `vi` mặc định + `en`, chuyển ngôn ngữ, kiểm tra khớp khóa.
- [x] Lint/type/test: ruff + mypy strict, ESLint + tsc + Prettier, pytest, Vitest, Playwright (375/768/1280 + axe a11y).
- [x] CI GitHub Actions: backend, frontend (gồm E2E), audit phụ thuộc, build Docker.
- [x] Ảnh chụp: `docs/screenshots/{landing,surveys,ui-kit,login}-{375,768,1280}.png`.

**FR hoàn thành ở GĐ 0:** chưa có FR nghiệp vụ (GĐ 0 là nền tảng). Phần nền cho NFR: log JSON + request-id, health-check, header bảo mật/CSP, không lộ stack trace, hàng đợi bền, graceful shutdown, a11y tự động.
