# Lệnh thường dùng. Chạy `make help` để xem danh sách.
SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
WEB := pnpm --filter @lys/web

.PHONY: help
help: ## Hiển thị danh sách lệnh
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------- cài đặt
.PHONY: install
install: ## Cài phụ thuộc Python (uv) và Node (pnpm)
	uv sync --all-packages
	pnpm install

.env:
	cp .env.example .env
	@echo "Đã tạo .env từ .env.example — nhớ đổi SECRET_KEY/HASH_SALT."

# ---------------------------------------------------------------- chạy
.PHONY: up
up: .env ## Chạy toàn bộ hệ thống bằng Docker Compose (http://localhost:8080)
	$(COMPOSE) up -d --build

.PHONY: down
down: ## Dừng toàn bộ container
	$(COMPOSE) down

.PHONY: logs
logs: ## Xem log tất cả service
	$(COMPOSE) logs -f --tail=100

.PHONY: infra
infra: .env ## Chỉ chạy hạ tầng (postgres, redis, mailpit) để dev ngoài Docker
	$(COMPOSE) up -d postgres redis mailpit

.PHONY: dev
dev: infra ## Dev có hot-reload: API :8000, worker, web :3000 (Ctrl+C để dừng)
	cd apps/api && uv run python -m app.cli migrate
	@trap 'kill 0' EXIT; \
	(cd apps/api && uv run uvicorn app.main:create_app --factory --reload --port 8000) & \
	(cd apps/worker && uv run celery -A worker.celery_app worker -Q default,nlp -l INFO) & \
	$(WEB) dev & \
	wait

# ---------------------------------------------------------------- chất lượng
.PHONY: lint
lint: ## Lint + kiểm tra kiểu toàn repo
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy apps/api/app apps/worker/worker packages/nlp/src apps/api/tests apps/worker/tests packages/nlp/tests
	pnpm format:check
	pnpm --filter @lys/shared test
	$(WEB) lint
	$(WEB) typecheck

.PHONY: format
format: ## Tự định dạng mã nguồn
	uv run ruff check --fix .
	uv run ruff format .
	pnpm format

.PHONY: test
test: ## Chạy unit test backend + frontend
	uv run pytest
	$(WEB) test

.PHONY: e2e
e2e: ## Test Playwright ở 375/768/1280px (tự khởi động Next.js dev server)
	$(WEB) exec playwright test --project=mobile-375 --project=tablet-768 --project=desktop-1280

.PHONY: screenshots
screenshots: ## Chụp ảnh màn hình các trang mẫu vào docs/screenshots/
	$(WEB) screenshots

# ---------------------------------------------------------------- dữ liệu & NLP (các giai đoạn sau)
# Lệnh CSDL chạy trong container nếu stack Docker đang chạy, ngược lại chạy cục bộ bằng uv.
API_RUN = $(shell $(COMPOSE) ps --status running --services 2>/dev/null | grep -qx api \
	&& echo "$(COMPOSE) exec -T api" || echo "cd apps/api && uv run")

.PHONY: migrate
migrate: ## Chạy migration Alembic tới bản mới nhất
	$(API_RUN) python -m app.cli migrate

.PHONY: seed
seed: ## Sinh dữ liệu minh họa tiếng Việt (xóa dữ liệu minh họa cũ)
	$(API_RUN) python -m app.cli seed --reset

.PHONY: erd
erd: ## Sinh lại docs/erd.md từ model
	cd apps/api && uv run python -m app.db.erd > ../../docs/erd.md

.PHONY: train
train: ## (GĐ 6) Huấn luyện mô hình cảm xúc
	uv run --extra ml python -m lys_nlp.train --train $(TRAIN) --validation $(VALIDATION) --output $(MODEL) --version $(VERSION)

.PHONY: evaluate
evaluate: ## (GĐ 6) Đánh giá mô hình (accuracy, macro-F1)
	uv run python -m lys_nlp.evaluate --data $(DATA) --model $(MODEL) --output $(REPORT)

.PHONY: backup
backup: ## (GĐ 14) Sao lưu PostgreSQL bằng pg_dump
	@echo "Chưa triển khai — Giai đoạn 14 (sao lưu/khôi phục)."
