# LyS Survey — Khảo sát & phân tích phản hồi khách hàng tiếng Việt

Nền tảng SaaS đa doanh nghiệp: tạo khảo sát, phát hành qua link/QR, khách điền không cần đăng nhập,
**NLP tiếng Việt** phân loại cảm xúc · chủ đề · cảnh báo khẩn cấp, nhân viên hiệu chỉnh nhãn,
dashboard và xuất báo cáo.

> Tên "LyS Survey" là placeholder — đổi bằng biến `APP_NAME` / `NEXT_PUBLIC_APP_NAME`.
> Đặc tả đầy đủ: [`CLAUDE.md`](CLAUDE.md) · Tiến độ: [`docs/progress.md`](docs/progress.md) ·
> Quyết định thiết kế: [`docs/decisions.md`](docs/decisions.md) · Kiến trúc: [`docs/architecture.md`](docs/architecture.md)

## Chạy nhanh bằng Docker Compose

Yêu cầu: Docker 24+ với Compose v2.

```bash
cp .env.example .env        # đổi SECRET_KEY, HASH_SALT trước khi dùng thật
docker compose up -d --build
```

| Địa chỉ                             | Nội dung                            |
| ----------------------------------- | ----------------------------------- |
| http://localhost:8080               | Ứng dụng web (qua nginx)            |
| http://localhost:8080/api/docs      | Tài liệu OpenAPI (tắt ở production) |
| http://localhost:8080/api/v1/health | Tình trạng API, PostgreSQL, Redis   |
| http://localhost:8025               | Hộp thư dev (Mailpit)               |

Kiểm tra trạng thái: `docker compose ps` (mọi service phải `healthy`). Dừng: `docker compose down`
(thêm `-v` để xóa dữ liệu).

> **Mạng có proxy kiểm tra TLS (CA nội bộ):** build kèm secret tùy chọn, ví dụ
> `docker build --secret id=ca_bundle,src=/duong-dan/ca-bundle.crt -f infra/docker/python.Dockerfile -t lys/backend:dev .`
> (tương tự với `infra/docker/web.Dockerfile` → `lys/web:dev`), rồi `docker compose up -d --no-build`.

## Phát triển cục bộ (hot-reload)

Yêu cầu: Python 3.11 + [uv](https://docs.astral.sh/uv/), Node.js 22 + pnpm 10, Docker (cho hạ tầng).

```bash
make install    # uv sync + pnpm install
make dev        # postgres/redis/mailpit trong Docker; API :8000, worker, web :3000 chạy cục bộ
```

Các lệnh khác (`make help`):

| Lệnh                                  | Việc                                                          |
| ------------------------------------- | ------------------------------------------------------------- |
| `make up` / `make down` / `make logs` | Chạy / dừng / xem log toàn bộ stack Docker                    |
| `make lint`                           | ruff, mypy (strict), Prettier, kiểm tra bản dịch, ESLint, tsc |
| `make format`                         | Tự định dạng Python + TS                                      |
| `make test`                           | pytest + Vitest                                               |
| `make e2e`                            | Playwright ở 375 / 768 / 1280px, kèm kiểm tra a11y (axe)      |
| `make screenshots`                    | Chụp ảnh các trang mẫu vào `docs/screenshots/`                |
| `make migrate`, `make seed`           | Giai đoạn 1                                                   |
| `make train`, `make evaluate`         | Giai đoạn 6 (NLP)                                             |
| `make backup`                         | Giai đoạn 14 (sao lưu/khôi phục)                              |

Pre-commit: `uvx pre-commit install`.

## Biến môi trường

Xem chú thích trong [`.env.example`](.env.example). Quan trọng:

| Biến                         | Ý nghĩa                                                                                                                     |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `APP_ENV`                    | `development` · `test` · `production` (production từ chối chạy nếu `SECRET_KEY`/`HASH_SALT` yếu, tắt `/api/docs`, bật HSTS) |
| `SECRET_KEY`, `HASH_SALT`    | Bí mật ký token / muối băm IP — chuỗi ngẫu nhiên ≥ 32 ký tự                                                                 |
| `POSTGRES_*`, `DATABASE_URL` | Kết nối PostgreSQL (để trống `DATABASE_URL` thì tự ghép)                                                                    |
| `REDIS_URL`, `CELERY_*`      | Redis cho cache và hàng đợi                                                                                                 |
| `CORS_ORIGINS`               | Danh sách origin được gọi API, phân tách dấu phẩy                                                                           |
| `HTTP_PORT`                  | Cổng nginx public (mặc định 8080)                                                                                           |
| `NEXT_PUBLIC_APP_NAME`       | Tên hiển thị trên giao diện (nhúng lúc build)                                                                               |

Trong Docker Compose, tên host nội bộ (`postgres`, `redis`, `mailpit`) được cố định trong
`docker-compose.yml`; `.env` dùng `localhost` để phục vụ `make dev`.

## Kiến trúc

```
apps/web        Next.js 16 · Tailwind 4 · shadcn/ui · next-intl (vi mặc định, en)
apps/api        FastAPI · SQLAlchemy 2 async · Pydantic v2 — routers → services → repositories → models
apps/worker     Celery worker + beat (dùng chung code với API)
packages/nlp    Pipeline NLP tiếng Việt (PhoBERT) — Giai đoạn 6
packages/shared Bản dịch i18n, hằng số dùng chung
infra/          Dockerfile, nginx
docs/           Quyết định, kiến trúc, tiến độ, ảnh chụp màn hình
```

Chi tiết: [`docs/architecture.md`](docs/architecture.md).

## Huấn luyện & đánh giá NLP

Sẽ bổ sung ở Giai đoạn 6 (`make train`, `make evaluate`, báo cáo accuracy / macro-F1 thật).

## Sao lưu & khôi phục

Sẽ bổ sung ở Giai đoạn 14 (service `backup` chạy `pg_dump` định kỳ, giữ N bản, hướng dẫn khôi phục có kiểm thử).
