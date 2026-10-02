# PROMPT FULL: HỆ THỐNG KHẢO SÁT & PHÂN TÍCH PHẢN HỒI KHÁCH HÀNG TIẾNG VIỆT

> **Cách dùng trong VS Code**
> 1. Lưu file này vào repo: `.github/copilot-instructions.md` (GitHub Copilot) hoặc `CLAUDE.md` (Claude Code / Cline / Roo).
> 2. Mở chat ở chế độ **Agent** và gõ: `Đọc file hướng dẫn và bắt đầu Giai đoạn 0.`
> 3. Sau mỗi giai đoạn, kiểm tra rồi gõ: `Tiếp tục giai đoạn N`.
>
> Nhãn ưu tiên: **[P0]** = bắt buộc theo tài liệu yêu cầu (FR-01 → FR-24, NFR). **[P1]** = mở rộng cho giống khaosat.me, làm sau khi P0 chạy ổn.

---

## 0. VAI TRÒ & NGUYÊN TẮC

Bạn là kỹ sư full-stack senior kiêm kỹ sư NLP/MLOps. Hãy xây dựng từ đầu hệ thống trong workspace hiện tại.

Nguyên tắc bắt buộc:
- Làm **tuần tự theo giai đoạn** (mục 17). Không làm nhiều giai đoạn trong một lần.
- Trước khi code mỗi giai đoạn: nêu kế hoạch ngắn (file sẽ tạo, quyết định thiết kế). Hỏi tối đa 3 câu nếu thực sự mơ hồ, còn lại tự quyết và ghi giả định vào `docs/decisions.md`.
- Sau mỗi giai đoạn: liệt kê file đã tạo/sửa, lệnh chạy, lệnh test, FR nào đã xong, rồi **dừng chờ tôi duyệt**.
- Code sạch, có kiểu dữ liệu, xử lý lỗi, log có cấu trúc, comment tiếng Việt ở logic nghiệp vụ phức tạp.
- Không hard-code bí mật; dùng `.env`. Không bịa số liệu: chỉ báo độ chính xác từ script đánh giá thật.
- Giao diện **mô phỏng bố cục và trải nghiệm** của khaosat.me nhưng **không sao chép** logo, ảnh, văn bản marketing hay tên thương hiệu. Dùng tên/logo placeholder dễ thay (biến `APP_NAME`).
- Mọi chữ hiển thị bằng tiếng Việt, tách vào file i18n (`vi` mặc định, sẵn sàng `en`).

---

## 1. TỔNG QUAN SẢN PHẨM

Nền tảng SaaS **đa doanh nghiệp (multi-tenant)**:
1. Doanh nghiệp tạo khảo sát (đánh giá sao, CSAT/NPS, câu hỏi chọn, nhận xét văn bản…), phát hành qua link/QR/nhúng/email.
2. Khách hàng điền **không cần đăng nhập**, tối ưu điện thoại.
3. **NLP tiếng Việt** phân loại cảm xúc + chủ đề + cảnh báo khẩn cấp cho phản hồi văn bản.
4. Nhân viên **kiểm tra và hiệu chỉnh nhãn** (human-in-the-loop); lịch sử chỉnh sửa dùng để đánh giá/huấn luyện lại.
5. **Dashboard, xu hướng, word cloud, pivot, xuất Excel/PDF**, cảnh báo xử lý khiếu nại.

Vai trò: `SUPER_ADMIN` (quản trị nền tảng, tùy chọn), `ADMIN` (admin doanh nghiệp), `ANALYST` (nhân viên phân tích), `VIEWER` (chỉ xem báo cáo).

---

## 2. CÔNG NGHỆ & KIẾN TRÚC

| Lớp | Lựa chọn |
|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui, dnd-kit (kéo thả), Recharts, TanStack Query/Table, react-hook-form + zod, next-intl |
| Backend API | Python 3.11, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| CSDL | PostgreSQL 16 (JSONB cho cấu hình form/câu trả lời, Row-Level Security cho tenant) |
| Hàng đợi | Celery + Redis (NLP lô, import, gửi email, báo cáo, sao lưu) |
| NLP | HuggingFace Transformers; PhoBERT (`vinai/phobert-base-v2`) fine-tune; `underthesea`/`pyvi` tách từ; ONNX Runtime (tùy chọn) để tăng tốc suy luận |
| Lưu tệp | Hệ thống tệp cục bộ qua lớp trừu tượng `StorageBackend` (dễ đổi sang S3/MinIO) |
| Email | SMTP (MailHog khi dev) qua lớp `EmailProvider` |
| Auth | JWT access + refresh (cookie httpOnly, SameSite), mật khẩu BCrypt |
| Realtime | Server-Sent Events cho dashboard (fallback polling) |
| Triển khai | Docker Compose: `web`, `api`, `worker`, `beat`, `postgres`, `redis`, `mailhog`, `nginx` |
| Chất lượng | Ruff + mypy, ESLint + Prettier, pytest, Vitest, Playwright, pre-commit, GitHub Actions CI |

Cấu trúc thư mục gợi ý:

```
/apps/web            # Next.js
/apps/api            # FastAPI (app/, tests/, alembic/)
/apps/worker         # Celery tasks (dùng chung code với api qua package)
/packages/nlp        # pipeline NLP, train/evaluate scripts, model registry
/packages/shared     # schema chung, i18n
/infra               # docker, nginx, backup scripts
/docs                # ERD, decisions.md, API, screenshots
```

Kiến trúc backend theo lớp: `routers → services → repositories → models`. Mọi truy vấn dữ liệu đi qua repository có **tenant scope bắt buộc**.

---

## 3. MÔ HÌNH DỮ LIỆU (tối thiểu, bổ sung nếu cần)

- `tenants` (doanh nghiệp), `users`, `memberships` (user–tenant–role), `invitations`.
- `workspaces` (không gian khảo sát; thuộc tenant), `workspace_members` (quyền theo workspace).
- `topic_sets`/`topics` (bộ chủ đề theo workspace; có từ khóa gợi ý, mô tả, màu).
- `surveys` (thuộc workspace; `status`: draft/published/closed/archived; `slug`; `theme` JSONB; `settings` JSONB; `languages`), `survey_versions` (snapshot khi xuất bản để dữ liệu cũ không vỡ).
- `questions` (loại, nội dung đa ngôn ngữ, `options` JSONB, `logic` JSONB, thứ tự, `required`, điểm số cho quiz).
- `responses` (khảo sát, thời gian, nguồn kênh, thông tin định danh tùy chọn, `fingerprint_hash`, `ip_hash`, `status`), `answers` (câu hỏi, giá trị JSONB).
- `text_analyses` (answer/response, `sentiment`, `sentiment_score`, `topics[]`, `is_urgent`, `urgent_reasons`, `model_version`, `status`: pending/done/failed, `analyzed_at`).
- `label_corrections` (FR-20: ai sửa, nhãn cũ/mới, lý do, thời điểm, `used_for_training`).
- `tickets` (phản hồi tiêu cực/khẩn cấp cần xử lý: trạng thái, người phụ trách, ghi chú, hạn xử lý) **[P1]**.
- `import_jobs`, `export_jobs`, `audit_logs`, `plans`, `subscriptions` **[P1]**.
- Index: `(tenant_id, survey_id, created_at)`, `(tenant_id, sentiment)`, GIN cho `topics`.

Xuất ERD dạng Mermaid vào `docs/erd.md`.

---

## 4. XÁC THỰC, PHÂN QUYỀN, CÔ LẬP DỮ LIỆU

- **[P0] FR-01**: đăng ký doanh nghiệp (tạo tenant + admin đầu tiên), đăng nhập email/mật khẩu, đăng xuất, làm mới token; điều hướng theo vai trò. Quên/đặt lại mật khẩu qua email.
- **[P0] FR-02**: CRUD không gian khảo sát; mỗi không gian có dữ liệu, chủ đề, cấu hình riêng; xóa mềm có xác nhận.
- **[P0] FR-03**: mời thành viên qua email (link có hạn), gán vai trò và phạm vi workspace; ma trận quyền (xem báo cáo / sửa khảo sát / sửa nhãn / quản trị thành viên / xuất dữ liệu).
- **[P0] FR-04 / NFR**: cô lập tenant nhiều lớp: (1) dependency FastAPI gắn `tenant_id` từ token, (2) repository luôn lọc theo tenant, (3) **PostgreSQL RLS** với `SET LOCAL app.tenant_id`, (4) bộ test tự động chứng minh tenant A không đọc/ghi được dữ liệu tenant B qua mọi endpoint (kể cả đoán ID, link công khai, export, SSE).
- Rate limit đăng nhập, khóa tạm khi sai nhiều lần, audit log các hành động nhạy cảm.

---

## 5. ĐỘNG CƠ KHẢO SÁT (SURVEY ENGINE)

### 5.1 Loại câu hỏi
- **[P0]** Đánh giá sao 1–5; Thang CSAT (1–5 hoặc cảm xúc mặt cười); Văn bản nhận xét (ngắn/dài, giới hạn ký tự); Chọn một; Chọn nhiều.
- **[P1]** NPS 0–10; Picture Choice; Slide (thanh trượt); Ranking (sắp xếp ưu tiên); Form thông tin (họ tên, SĐT, email, có validate); Upload File (giới hạn loại/dung lượng, quét kiểm tra); Ma trận (matrix); Ngày/giờ.
- Kiến trúc **plugin**: mỗi loại có `QuestionType` gồm schema cấu hình, trình render (builder + respondent), validator, hàm tổng hợp thống kê. Thêm loại mới không sửa lõi.

### 5.2 Logic **[P1]**
- **Jump Logic**: điều hướng theo câu trả lời trước.
- **Question Display Logic / Answer Display Logic**: ẩn/hiện câu hỏi, đáp án theo điều kiện (AND/OR, toán tử bằng, khác, chứa, lớn hơn, nhỏ hơn…).
- **Carry Forward Choice**: lấy lựa chọn ở câu trước làm đáp án câu sau.
- **Quota & Limit**: giới hạn số lượng theo điều kiện (khu vực, độ tuổi…).
- Trình soạn điều kiện dạng giao diện trực quan; kiểm tra vòng lặp/điều kiện không đạt được; có công cụ "mô phỏng đường đi".

### 5.3 Thiết lập khảo sát
- **[P0]** Bắt buộc/tùy chọn từng câu; validate; lưu nháp tự động; xuất bản/đóng thủ công.
- **[P1]** Lên lịch mở/đóng; giới hạn số lần trả lời theo trình duyệt/IP/SĐT/email; giới hạn tổng số phản hồi; xáo thứ tự câu hỏi/đáp án; **đa ngôn ngữ** (nội dung theo ngôn ngữ, nút chuyển ngôn ngữ ở trang khách); phiên bản khảo sát.
- **[P1] Chế độ trắc nghiệm (Quiz)**: đáp án đúng/điểm theo câu, tự chấm, đồng hồ đếm ngược và tự thu bài, xáo đề, ngân hàng câu hỏi + random nhiều bộ đề, hiện đáp án và xếp loại theo điểm.

### 5.4 Tùy biến giao diện khảo sát
Hình nền (thư viện + tải lên), màu chữ/nút, font và cỡ chữ, logo thương hiệu, bố cục (một câu mỗi trang / cuộn dọc), nút "Tiếp theo/Quay lại", thanh tiến độ. Lưu trong `theme` JSONB và áp dụng đúng ở bản xem trước lẫn trang khách.

### 5.5 Thư viện mẫu **[P1]**
Tạo sẵn ≥ 8 mẫu tiếng Việt: CSAT nhà hàng, đánh giá khách sạn, phản hồi ứng dụng/IT, siêu thị, giáo dục, y tế, NPS tổng quát, hài lòng nhân viên. Có nút "Dùng mẫu này".

### 5.6 Import dữ liệu
- **[P0] FR-07**: import **phản hồi** từ CSV/Excel: chọn cột ánh xạ, xem trước 20 dòng, validate, chạy nền, thanh tiến độ, báo cáo dòng lỗi tải được, kích hoạt phân tích NLP theo lô.
- **[P1]** Import **bảng câu hỏi** từ Excel (mẫu file tải về được).

---

## 6. PHÁT HÀNH ĐA KÊNH

- **[P0] FR-06**: URL công khai ổn định (`/s/{slug}`), mã QR (PNG/SVG, tùy logo/màu, kích thước in), tải về/in được; mỗi QR có thể gắn tham số kênh/chi nhánh/bàn để thống kê nguồn.
- **[P1]** Mã nhúng iframe/script cho website; chế độ **Kiosk** (máy tính bảng tại quầy: tự reset sau khi gửi); gửi lời mời **email** hàng loạt qua hàng đợi (có theo dõi mở/click, link định danh khách); giao diện `ZaloZnsProvider` dạng interface + bản giả lập (mock) để sau này cắm Zalo thật; QR in trên hóa đơn có tham số định danh.

---

## 7. TRẢI NGHIỆM KHÁCH HÀNG (TRANG CÔNG KHAI)

- **[P0] FR-08**: mở form ngay khi quét QR/bấm link, không đăng nhập.
- **[P0] FR-09**: mobile-first, nhẹ (mục tiêu < 150KB JS ban đầu cho trang khảo sát, LCP < 2s trên 4G), dùng SSR/ISR, ảnh tối ưu, hoạt động tốt với bàn phím điện thoại.
- **[P0] FR-10**: chạm chọn sao, chọn mức hài lòng, nhập nhận xét; validate phía client và server (zod ↔ pydantic cùng ràng buộc); lưu tạm tiến độ trong phiên để không mất khi tải lại.
- **[P0] FR-11**: màn hình cảm ơn đẹp mắt; hiển thị **voucher/mã giảm giá** do doanh nghiệp cấu hình (mã cố định hoặc sinh theo lượt, có hạn dùng); chống spam: rate limit theo IP, token một lần cho mỗi lượt gửi, honeypot, thời gian điền tối thiểu, tùy chọn CAPTCHA (Cloudflare Turnstile/hCaptcha) khi nghi ngờ.
- Truy cập khảo sát đã đóng/hết hạn/hết quota hiển thị thông báo thân thiện.

---

## 8. CHỦ ĐỀ THEO NGÀNH

- **[P0] FR-12**: mỗi workspace tự quản lý bộ nhãn chủ đề (thêm/sửa/xóa/gộp, màu, từ khóa gợi ý, mô tả ngắn để dùng cho phân loại). Cung cấp **bộ chủ đề mẫu** theo ngành: Nhà hàng (Món ăn, Phục vụ, Giá cả, Không gian, Vệ sinh), IT (Giao diện, Tính năng, Hiệu năng, Lỗi hệ thống, Hỗ trợ), Khách sạn, Bán lẻ, Giáo dục, Y tế.
- **[P0] FR-13**: pipeline chỉ nạp **đúng** bộ chủ đề của workspace tương ứng; có test chứng minh không lẫn giữa các ngành/tenant.
- Khi sửa bộ chủ đề: cho phép "phân tích lại" các phản hồi cũ (job nền).

---

## 9. NLP ENGINE (`packages/nlp`)

### 9.1 Tiền xử lý **[P0] FR-14**
Chuẩn hóa Unicode (NFC), đưa về chữ thường có kiểm soát, bỏ HTML/URL/ký tự rác, rút gọn ký tự lặp ("ngonnnn" → "ngon"), xử lý emoji (giữ làm tín hiệu cảm xúc, ánh xạ sang token), **từ điển teencode/viết tắt** có thể cấu hình (ko→không, dc→được, k→không, vs→với, ok…), sửa lỗi dấu thường gặp, tách câu, tách từ. Tất cả có unit test với ≥ 50 ca thực tế.

### 9.2 Cảm xúc **[P0] FR-15**
- Mô hình: PhoBERT fine-tune 3 lớp (Tích cực/Tiêu cực/Trung lập), trả **điểm tin cậy** đã hiệu chỉnh (temperature scaling).
- Có thể kết hợp tín hiệu số sao: nếu văn bản mơ hồ thì dùng sao làm đặc trưng phụ nhưng **không ghi đè** nhãn văn bản.
- Phân tích theo **câu** và tổng hợp cho cả phản hồi (một phản hồi có thể vừa khen vừa chê).
- Dữ liệu: nếu chưa có bộ nhãn, tạo `data/seed/` nhỏ có gắn nhãn **được ghi rõ là dữ liệu mẫu**, kèm hướng dẫn nạp bộ dữ liệu công khai (ví dụ UIT-VSFC, VLSP) và script `train.py`.

### 9.3 Chủ đề **[P0] FR-16**
- Multi-label theo danh mục của workspace. Chiến lược lai: (a) **zero-shot/embedding similarity** dùng mô tả + từ khóa chủ đề làm "prototype" (hoạt động ngay khi chưa có dữ liệu huấn luyện), (b) **classifier fine-tune** theo workspace khi đã có đủ nhãn đã được xác nhận (FR-20).
- Ngưỡng tin cậy cấu hình được; dưới ngưỡng gán "Chưa phân loại".

### 9.4 Cảnh báo khẩn cấp **[P0] FR-17**
Luật + mô hình: từ điển cụm từ (đe dọa, kiện, báo công an, ngộ độc, đau bụng, tiêu chảy, côn trùng/dị vật, lừa đảo, báo đài…) có thể cấu hình theo workspace + điểm tiêu cực cao. Ghi `urgent_reasons` để người dùng hiểu vì sao bị gắn cờ. Kích hoạt: huy hiệu nổi bật, ghim đầu danh sách, **thông báo email tức thì** cho người phụ trách, tạo **ticket** **[P1]**.

### 9.5 Vận hành NLP **[P0 – NFR]**
- Xử lý lô bằng Celery (chunk theo 64–256 câu), không chặn UI; hiển thị tiến độ.
- **Dự phòng**: luôn lưu văn bản thô trước, `text_analyses.status = pending`; nếu mô hình lỗi/không tải được thì giữ `pending`, **retry với exponential backoff**, và có job định kỳ quét `pending/failed` để phân tích bù. Health-check endpoint cho NLP.
- Quản lý phiên bản mô hình (`model_version`), cho phép chạy lại phân tích khi nâng cấp.
- Script `evaluate.py`: Accuracy, macro-F1, precision/recall từng lớp, confusion matrix; so với nhãn người dùng đã xác nhận. **Mục tiêu NFR: F1/Accuracy ≥ 80%**; nếu chưa đạt, báo số thật và đề xuất cải thiện (thêm dữ liệu, làm sạch nhãn, fine-tune lâu hơn).
- Script `retrain.py` đọc `label_corrections` đã duyệt để huấn luyện lại, ghi báo cáo trước/sau.

---

## 10. KIỂM TRA & HIỆU CHỈNH (HUMAN-IN-THE-LOOP)

- **[P0] FR-18**: bảng phản hồi: cột nội dung, sao, cảm xúc (nhãn màu + điểm tin cậy), chủ đề (chip), nguồn, thời gian, trạng thái; lọc theo thời gian, sắc thái, chủ đề, mức khẩn cấp, khảo sát, kênh; tìm kiếm toàn văn; sắp xếp; phân trang phía server; chọn nhiều dòng để thao tác hàng loạt.
- **[P0] FR-19**: ngăn kéo chi tiết bên phải: sửa nhãn cảm xúc, thêm/bớt chủ đề, gỡ/gắn cờ khẩn cấp, ghi chú; phím tắt để duyệt nhanh; hoàn tác.
- **[P0] FR-20**: mỗi chỉnh sửa ghi vào `label_corrections` (người sửa, nhãn cũ → mới, thời điểm, lý do); trang "Chất lượng mô hình": tỷ lệ sửa, độ chính xác theo thời gian, nút export tập dữ liệu đã xác nhận (CSV/JSONL).
- **[P1]** Duyệt hai bước (analyst đề xuất, admin duyệt) cho dữ liệu dùng huấn luyện.

---

## 11. THỐNG KÊ, BÁO CÁO, DASHBOARD

- **[P0] FR-21**: thẻ chỉ số (tổng phản hồi, CSAT trung bình, % Tích cực/Tiêu cực/Trung lập, số cảnh báo khẩn, tỷ lệ hoàn thành), biểu đồ theo thời gian, so sánh giữa các khảo sát/chi nhánh. Cập nhật gần realtime (SSE).
- **[P0] FR-22**: xu hướng chủ đề theo tuần/tháng/quý, biểu đồ đường/cột chồng, phát hiện chủ đề tăng bất thường (so với kỳ trước, ghi chú trực quan).
- **[P0] FR-23**: Word Cloud riêng cho từ khen (xanh) và từ chê (đỏ); loại stop-words tiếng Việt, gộp biến thể, bấm vào từ để lọc danh sách phản hồi chứa từ đó.
- **[P0] FR-24**: xuất Excel (.xlsx nhiều sheet: tóm tắt, chi tiết, theo chủ đề) và PDF (có biểu đồ, logo, khoảng thời gian); xuất chạy nền với khối lượng lớn, tải về khi xong.
- **[P1]** Thống kê theo từng câu hỏi (phân bố đáp án, trung bình, NPS = %Promoters − %Detractors), **Pivot Table** (chọn hàng/cột/giá trị), bộ lọc nâng cao lưu được, lịch gửi báo cáo định kỳ qua email, đường dẫn báo cáo chia sẻ có hạn (read-only).
- **[P1] Ticket/Cảnh báo**: phản hồi đánh giá thấp hoặc khẩn cấp tự tạo ticket; giao người xử lý, trạng thái (Mới/Đang xử lý/Đã xong), hạn xử lý, ghi chú, thống kê thời gian xử lý trung bình.

---

## 12. GÓI DỊCH VỤ & THANH TOÁN **[P1]**
Chỉ làm khung: bảng `plans` (Free/Pro/Business) với giới hạn (số workspace, thành viên, phản hồi NLP/tháng, tính năng nâng cao), middleware kiểm tra hạn mức, trang "Gói & Thanh toán" hiển thị mức sử dụng. **Không tích hợp cổng thanh toán thật** trừ khi tôi yêu cầu; dùng adapter giả lập.

---

## 13. YÊU CẦU GIAO DIỆN (PHONG CÁCH GIỐNG KHAOSAT.ME)

### 13.1 Hệ thống thiết kế
Tailwind + shadcn/ui, font Be Vietnam Pro hoặc Inter, bo góc 12–16px, bóng nhẹ, nhiều khoảng trắng, **một màu chủ đạo** đặt trong CSS variable. Màu ngữ nghĩa cố định: **Xanh = Tích cực, Đỏ = Tiêu cực, Xám = Trung lập, Cam = Khẩn cấp**. Hỗ trợ dark mode (tùy chọn). Đạt Lighthouse Accessibility ≥ 90, thao tác được bằng bàn phím, tương phản đủ chuẩn.

### 13.2 Landing page
Header cố định (logo, Tính năng, Bảng giá, Hướng dẫn, Liên hệ, Đăng nhập, **Đăng ký miễn phí**); Hero (tiêu đề, mô tả, nút "Tạo khảo sát miễn phí ngay", ảnh dashboard); khối "Khám phá tính năng" dạng tab (Thiết kế & Tùy chỉnh · Loại câu hỏi · Thiết lập · Logic · Phân tích NLP); khối **"Tạo khảo sát trong 3 bước"** (Thiết lập → Chia sẻ → Xem báo cáo); số liệu nổi bật; FAQ accordion; footer nhiều cột.

### 13.3 Khu vực quản trị
Thanh trên: **Tạo khảo sát · Khảo sát của tôi · Trang cá nhân · Gói & Thanh toán · Quản lý**, bộ chọn workspace, menu người dùng. Trang "Khảo sát của tôi": lưới thẻ (ảnh nền thu nhỏ, tên, trạng thái, số phản hồi, CSAT, ngày tạo), tìm kiếm/lọc, menu ⋯ (sửa, nhân bản, lấy link/QR, đóng, xóa). Trang "Tạo khảo sát": từ đầu / thư viện mẫu / import Excel.

### 13.4 Trình tạo khảo sát (màn hình trọng tâm)
Bố cục 3 vùng: **trái = xem trước trực tiếp** (chuyển điện thoại/máy tính), **giữa = danh sách câu hỏi kéo thả** (thêm/nhân bản/xóa/sắp xếp), **phải = bảng thiết lập có công tắc bật/tắt** theo nhóm (Thiết kế · Loại câu hỏi · Thiết lập · Logic · Quiz). Thanh công cụ: Lưu nháp tự động, Xem trước, Xuất bản, Chia sẻ (Link / QR / Nhúng / Email). Hoàn tác/làm lại (Ctrl+Z / Ctrl+Y), phát hiện thay đổi chưa lưu.

### 13.5 Trang khách
Mobile-first, nút lớn dễ chạm, thanh tiến độ, chuyển câu mượt (tôn trọng `prefers-reduced-motion`), áp dụng đúng theme của nhà tạo, màn hình cảm ơn đẹp.

### 13.6 Trang báo cáo
Tab: Tổng quan · Phản hồi chi tiết · Chủ đề · Từ khóa · Theo câu hỏi **[P1]** · Pivot **[P1]** · Ticket **[P1]** · Xuất báo cáo. Thanh lọc cố định phía trên. Mọi bảng/biểu đồ có trạng thái loading (skeleton), rỗng, lỗi. Phản hồi khẩn cấp viền/huy hiệu cam-đỏ và ghim đầu.

### 13.7 Dữ liệu minh họa
Tạo lệnh `make seed`: sinh dữ liệu giả **tiếng Việt thực tế** (≥ 2 tenant, ≥ 3 workspace, ≥ 1.500 phản hồi nhiều sắc thái, có teencode, có vài ca khẩn cấp) để dashboard có số liệu ngay.

---

## 14. YÊU CẦU PHI CHỨC NĂNG (NFR)

- **Hiệu năng**: tra cứu, lọc, tải biểu đồ < 2s (index, phân trang, bảng tổng hợp/materialized view, cache Redis); đo bằng test tải k6/Locust với 100.000 phản hồi, ghi kết quả vào `docs/perf.md`.
- **Độ chính xác NLP**: ≥ 80% theo mục 9.5, có báo cáo từ `evaluate.py`.
- **Bảo mật**: BCrypt (cost ≥ 12); JWT ngắn hạn + refresh xoay vòng; cookie httpOnly/Secure/SameSite; CSRF cho thao tác dùng cookie; CORS chặt; validate đầu vào; chống SQLi/XSS (escape nội dung người dùng, CSP header); upload an toàn (kiểm MIME, giới hạn kích thước, đổi tên); không lộ stack trace; secrets qua env; dependency audit trong CI; **bảo vệ dữ liệu cá nhân** (băm IP/fingerprint, cho phép xóa dữ liệu theo yêu cầu, ẩn danh khi xuất nếu cấu hình).
- **Tính khả dụng**: Responsive máy tính + điện thoại; hướng tới ~99% uptime: health-check, restart policy, graceful shutdown.
- **Tin cậy & sao lưu**: script `pg_dump` định kỳ (service `backup` trong Compose) + giữ N bản + hướng dẫn khôi phục có kiểm thử; hàng đợi bền (acks late); idempotent job.
- **Quan sát**: log JSON, request-id, metrics Prometheus (độ trễ API, độ dài hàng đợi, tỷ lệ NLP lỗi), trang `/health`.
- **Khả năng mở rộng**: API không lưu trạng thái; worker mở rộng ngang; NLP có thể tách service riêng.

---

## 15. DANH SÁCH API (REST, tiền tố `/api/v1`, OpenAPI tự sinh)

`auth` (register, login, refresh, logout, forgot/reset) · `tenants/me` · `members` & `invitations` · `workspaces` · `topics` · `surveys` (CRUD, publish, duplicate, versions) · `surveys/{id}/questions` · `templates` · `share` (link, qr, embed) · `public/surveys/{slug}` (lấy cấu hình) · `public/surveys/{slug}/responses` (gửi) · `responses` (list, detail, filter) · `analyses/{id}/corrections` · `imports` · `exports` · `analytics` (overview, trends, topics, wordcloud, per-question, pivot) · `tickets` · `nlp/health` · `billing/usage`. Mọi endpoint không công khai bắt buộc xác thực + tenant scope; trả lỗi chuẩn hóa (mã lỗi + thông điệp tiếng Việt).

---

## 16. KIỂM THỬ & DEVOPS

- Backend: pytest (unit + integration với Postgres thật qua testcontainers), **test cô lập tenant**, test logic khảo sát, test pipeline NLP, độ phủ ≥ 70% ở `services/` và `packages/nlp`.
- Frontend: Vitest cho component/logic, Playwright cho luồng chính (đăng ký → tạo khảo sát → khách điền → xem dashboard → sửa nhãn → xuất báo cáo) trên viewport 375/768/1280.
- CI GitHub Actions: lint, type-check, test, build, audit.
- `README.md`: cài đặt, chạy bằng `docker compose up`, biến môi trường, kiến trúc, cách huấn luyện/đánh giá NLP, cách sao lưu/khôi phục.
- `Makefile`: `make dev`, `make test`, `make seed`, `make train`, `make evaluate`, `make backup`.

---

## 17. LỘ TRÌNH THỰC HIỆN (dừng sau mỗi giai đoạn)

| GĐ | Nội dung | Tiêu chí hoàn thành |
|---|---|---|
| **0** | Monorepo, Docker Compose, lint/CI, `.env.example`, **design system + layout khung** (header, thẻ, bảng, form, skeleton), i18n | `docker compose up` chạy; trang mẫu hiển thị đúng; ảnh chụp lưu `docs/screenshots/` |
| **1** | CSDL, migration, ERD, RLS | Migration chạy sạch; ERD trong `docs/erd.md` |
| **2** | Auth, tenant, workspace, thành viên, phân quyền (FR-01→04) | Test cô lập tenant xanh; đăng ký/đăng nhập/mời hoạt động |
| **3** | Chủ đề theo workspace + bộ mẫu (FR-12→13 phần cấu hình) | CRUD chủ đề, bộ mẫu theo ngành |
| **4** | Survey engine P0: trình tạo (kéo thả, xem trước, theme), câu hỏi P0, xuất bản, link + QR (FR-05→06) | Tạo và xuất bản khảo sát hoàn chỉnh |
| **5** | Trang khách + chống spam + voucher (FR-08→11) | Điền được trên 375px; chặn gửi lặp; test Playwright |
| **6** | NLP pipeline + Celery + dự phòng + `evaluate.py` (FR-14→17) | Phân tích phản hồi chạy nền; ngắt mô hình vẫn lưu thô và phân tích bù; báo cáo F1 thật |
| **7** | Import CSV/Excel (FR-07) | Import 10.000 dòng không treo UI; báo lỗi dòng |
| **8** | Danh sách phản hồi, sửa nhãn, lịch sử, trang chất lượng mô hình (FR-18→20) | Lọc/tìm/sửa/hoàn tác; export dữ liệu đã xác nhận |
| **9** | Dashboard, xu hướng, word cloud, xuất Excel/PDF (FR-21→24), SSE | Biểu đồ < 2s với 100k bản ghi (có số đo) |
| **10** | **[P1]** Loại câu hỏi mở rộng + logic rẽ nhánh + lịch/giới hạn + đa ngôn ngữ | Mô phỏng đường đi đúng; test logic |
| **11** | **[P1]** Quiz/trắc nghiệm, thư viện mẫu, import bảng câu hỏi Excel | Chấm điểm, hẹn giờ, xáo đề hoạt động |
| **12** | **[P1]** Email/Kiosk/Embed, ticket & cảnh báo, báo cáo theo câu hỏi, Pivot, lịch gửi báo cáo | Luồng khiếu nại hoàn chỉnh |
| **13** | **[P1]** Gói & hạn mức (giả lập thanh toán), audit log, quan sát/metrics | Middleware hạn mức; dashboard metrics |
| **14** | Hoàn thiện: test E2E toàn bộ, tối ưu hiệu năng, bảo mật (rà soát OWASP), sao lưu/khôi phục, tài liệu | Checklist Definition of Done dưới đây đạt |

---

## 18. DEFINITION OF DONE (CHO MỖI GIAI ĐOẠN)

- [ ] Chạy được từ đầu bằng lệnh trong README, không lỗi.
- [ ] Test liên quan viết và xanh; lint/type-check sạch.
- [ ] Không vi phạm cô lập tenant (có test).
- [ ] Giao diện kiểm tra ở 375/768/1280px, có trạng thái loading/rỗng/lỗi, chữ tiếng Việt chuẩn.
- [ ] Cập nhật `docs/` (ERD/API/decisions) và nhật ký FR đã hoàn thành.
- [ ] Báo cáo cuối giai đoạn: file đã đổi, cách chạy, cách kiểm thử, rủi ro/việc còn lại, rồi **dừng chờ tôi gõ "tiếp tục"**.

---

**Bắt đầu với Giai đoạn 0: tóm tắt kiến trúc và cấu trúc thư mục đề xuất, nêu giả định, rồi mới tạo file.**
