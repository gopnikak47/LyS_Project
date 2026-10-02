# Nhật ký tiến độ & yêu cầu chức năng (FR)

## Trạng thái giai đoạn

| GĐ    | Nội dung                                                                              | Trạng thái    |
| ----- | ------------------------------------------------------------------------------------- | ------------- |
| 0     | Monorepo, Docker Compose, lint/CI, `.env.example`, design system + layout khung, i18n | ✅ Hoàn thành |
| 1     | CSDL, migration, ERD, RLS                                                             | ✅ Hoàn thành |
| 2     | Auth, tenant, workspace, thành viên, phân quyền (FR-01→04)                            | ⏳            |
| 3     | Chủ đề theo workspace + bộ mẫu (FR-12→13)                                             | ⏳            |
| 4     | Survey engine P0, link + QR (FR-05→06)                                                | ⏳            |
| 5     | Trang khách, chống spam, voucher (FR-08→11)                                           | ⏳            |
| 6     | NLP pipeline + Celery + dự phòng + evaluate (FR-14→17)                                | ⏳            |
| 7     | Import CSV/Excel (FR-07)                                                              | ⏳            |
| 8     | Danh sách phản hồi, sửa nhãn, chất lượng mô hình (FR-18→20)                           | ⏳            |
| 9     | Dashboard, xu hướng, word cloud, xuất Excel/PDF, SSE (FR-21→24)                       | ⏳            |
| 10–14 | P1 mở rộng & hoàn thiện                                                               | ⏳            |

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

## Giai đoạn 1 — chi tiết

**Tiêu chí hoàn thành:** migration chạy sạch; ERD trong `docs/erd.md`.

- [x] 26 bảng (SQLAlchemy 2 typed models), migration `0001` (Alembic async): lên → xuống → lên lại sạch.
- [x] RLS trên 21 bảng (19 bảng tenant + `tenants` + `users`), vai trò `lys_rls`, ngữ cảnh `app.tenant_id`.
- [x] Chỉ mục theo đặc tả: `(tenant_id, survey_id, created_at)`, `(tenant_id, sentiment)`, GIN `topic_ids`, trigram không dấu.
- [x] Repository nền `TenantRepository` (lọc tenant + xóa mềm, ép `tenant_id` khi thêm).
- [x] `make seed`: 2 doanh nghiệp, 4 workspace, 4 khảo sát, 1.660 phản hồi, 1.363 nhận xét có teencode/emoji/ca khẩn cấp.
- [x] Service `migrate` trong Compose; CI có PostgreSQL thật; test dùng testcontainers khi chạy cục bộ.
- [x] Test: 16 test CSDL (RLS: đọc/ghi/sửa/xóa chéo tenant, đoán ID, thiếu ngữ cảnh, rò ngữ cảnh qua pool, quyền bảng auth, độ phủ RLS; migration; khớp model; seed; repository) + test ERD.

**FR:** nền tảng cho FR-04 (lớp RLS) — hoàn thiện kiểm thử qua mọi endpoint ở GĐ 2.

## Giai đoạn 2 — chi tiết

**Tiêu chí hoàn thành:** test cô lập tenant xanh; đăng ký/đăng nhập/mời hoạt động.

| FR    | Nội dung                                                                                                             | Trạng thái |
| ----- | -------------------------------------------------------------------------------------------------------------------- | ---------- |
| FR-01 | Đăng ký doanh nghiệp + admin, đăng nhập/đăng xuất, refresh xoay vòng, quên/đặt lại mật khẩu, điều hướng theo vai trò | ✅         |
| FR-02 | CRUD workspace, bộ chủ đề mẫu theo ngành khi tạo, xóa mềm có xác nhận tên                                            | ✅         |
| FR-03 | Mời qua email (link 7 ngày), vai trò + phạm vi workspace, ma trận quyền, đổi vai trò/xóa thành viên                  | ✅         |
| FR-04 | Cô lập tenant 4 lớp + bộ test tự kiểm tra mọi endpoint có ID                                                         | ✅         |

- Bảo mật: cookie httpOnly/SameSite, CSRF, rate limit, khóa tạm, audit log, chống dò tài khoản.
- Giao diện: đăng nhập/đăng ký/quên/đặt lại mật khẩu/nhận lời mời, header theo quyền, chọn
  workspace & doanh nghiệp, trang **Quản lý** (thành viên, lời mời, không gian, doanh nghiệp),
  **Trang cá nhân** (hồ sơ, ngôn ngữ, đổi mật khẩu).
- Test: backend 81 (gồm 2 test ghi đồng thời), Vitest 23, Playwright 30 (375/768/1280 + axe) +
  15 ảnh chụp.

## Giai đoạn 3 — chi tiết

**Tiêu chí hoàn thành:** CRUD chủ đề, bộ mẫu theo ngành.

| FR               | Nội dung                                                                                                                                                                   | Trạng thái |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| FR-12            | Thêm/sửa/xóa/gộp/bật-tắt/sắp xếp (kéo thả) chủ đề, màu, từ khóa, mô tả; 6 bộ mẫu ngành (nhà hàng, IT, khách sạn, bán lẻ, giáo dục, y tế); áp dụng mẫu (thêm hoặc thay thế) | ✅         |
| FR-13 (cấu hình) | `load_topic_catalog` chỉ nạp chủ đề đang bật của đúng workspace + tenant; có test chứng minh không lẫn ngành/tenant                                                        | ✅         |

- Xóa/gộp chủ đề cập nhật luôn nhãn trên phản hồi đã phân tích (không để ID mồ côi, không trùng).
- Mỗi thay đổi tăng `topic_sets.version`; nút "Phân tích lại" đánh dấu `pending` và xếp job
  `worker.tasks.nlp.reanalyze_workspace` (worker hiện thực ở GĐ 6).
- Test: backend 93 (gồm 8 test chủ đề + 9 endpoint mới trong bộ cô lập tenant), Playwright 33 + 15 ảnh chụp.
