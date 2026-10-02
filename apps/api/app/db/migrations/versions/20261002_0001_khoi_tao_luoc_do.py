"""Khởi tạo lược đồ: bảng nghiệp vụ, chỉ mục tìm kiếm, Row-Level Security theo tenant.

Revision ID: 0001
Revises:
Create Date: 2026-10-02 03:42:50.770569
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bảng chịu RLS theo cột tenant_id. Danh sách được "đóng băng" trong migration này;
# bảng mới ở migration sau phải tự bật RLS (xem test_rls_covers_all_tenant_tables).
TENANT_TABLES = (
    "audit_logs",
    "answers",
    "export_jobs",
    "import_jobs",
    "invitations",
    "label_corrections",
    "memberships",
    "questions",
    "responses",
    "subscriptions",
    "survey_channels",
    "survey_versions",
    "surveys",
    "text_analyses",
    "tickets",
    "topic_sets",
    "topics",
    "workspace_members",
    "workspaces",
)
RLS_ROLE = "lys_rls"


def _enable_rls() -> None:
    # Vai trò không đăng nhập; kết nối ứng dụng `SET LOCAL ROLE lys_rls` trong mỗi transaction
    # đã xác thực. Vì không phải chủ sở hữu bảng nên luôn bị chính sách RLS ràng buộc.
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RLS_ROLE}') THEN
            CREATE ROLE {RLS_ROLE} NOLOGIN;
          END IF;
        END
        $$;
        """
    )
    op.execute(f"GRANT {RLS_ROLE} TO CURRENT_USER")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {RLS_ROLE}")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid
        LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_user() RETURNS uuid
        LANGUAGE sql STABLE AS
        $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$;
        """
    )

    for table in TENANT_TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO {RLS_ROLE}")
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = app_current_tenant()) "
            "WITH CHECK (tenant_id = app_current_tenant())"
        )

    # tenants: chỉ thấy/sửa chính doanh nghiệp của mình; tạo/xóa tenant đi qua phiên hệ thống.
    op.execute(f"GRANT SELECT, UPDATE ON tenants TO {RLS_ROLE}")
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_isolation ON tenants "
        "USING (id = app_current_tenant()) WITH CHECK (id = app_current_tenant())"
    )

    # users là bảng toàn cục: chỉ thấy chính mình hoặc thành viên cùng tenant
    # (truy vấn con trên memberships cũng bị RLS lọc theo tenant hiện tại).
    op.execute(f"GRANT SELECT, UPDATE ON users TO {RLS_ROLE}")
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_members ON users USING ("
        "id = app_current_user() OR EXISTS ("
        "SELECT 1 FROM memberships m WHERE m.user_id = users.id))"
    )

    # Bảng tham chiếu chỉ đọc.
    op.execute(f"GRANT SELECT ON plans, nlp_models TO {RLS_ROLE}")


def _disable_rls() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_members ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenants")
    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY")
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION IF EXISTS app_current_tenant()")
    op.execute("DROP FUNCTION IF EXISTS app_current_user()")
    # Thu hồi mọi quyền để có thể downgrade/upgrade lặp lại; giữ lại role (có thể dùng chung).
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RLS_ROLE}') THEN
            REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {RLS_ROLE};
          END IF;
        END
        $$;
        """
    )


def _search_support() -> None:
    # Tìm kiếm toàn văn không phân biệt dấu: "dau bung" khớp "đau bụng".
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
        $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$;
        """
    )
    op.execute(
        "CREATE INDEX ix_text_analyses_text_trgm ON text_analyses "
        "USING gin (f_unaccent(lower(text)) gin_trgm_ops)"
    )


def _seed_plans() -> None:
    plans = sa.table(
        "plans",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("price_vnd", sa.Integer),
        sa.column("limits", postgresql.JSONB),
        sa.column("sort_order", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        plans,
        [
            {
                "code": "free",
                "name": "Miễn phí",
                "price_vnd": 0,
                "limits": {
                    "workspaces": 1,
                    "members": 3,
                    "surveys": 5,
                    "nlp_responses_per_month": 500,
                    "features": [],
                },
                "sort_order": 1,
                "is_active": True,
            },
            {
                "code": "pro",
                "name": "Pro",
                "price_vnd": 490000,
                "limits": {
                    "workspaces": 5,
                    "members": 15,
                    "surveys": 100,
                    "nlp_responses_per_month": 20000,
                    "features": ["logic", "quiz", "export_pdf", "email_invites"],
                },
                "sort_order": 2,
                "is_active": True,
            },
            {
                "code": "business",
                "name": "Business",
                "price_vnd": 1990000,
                "limits": {
                    "workspaces": 50,
                    "members": 200,
                    "surveys": 2000,
                    "nlp_responses_per_month": 500000,
                    "features": [
                        "logic",
                        "quiz",
                        "export_pdf",
                        "email_invites",
                        "pivot",
                        "scheduled_reports",
                        "tickets",
                    ],
                },
                "sort_order": 3,
                "is_active": True,
            },
        ],
    )


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "nlp_models",
        sa.Column("task", sa.String(length=32), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("artifact_path", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nlp_models")),
        sa.UniqueConstraint("task", "version", name="uq_nlp_models_task_version"),
    )
    op.create_table(
        "plans",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price_vnd", sa.Integer(), nullable=False),
        sa.Column("limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_plans")),
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("locale", sa.String(length=8), server_default="vi", nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "password_reset_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_password_reset_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_password_reset_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_password_reset_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_password_reset_tokens_user_id"), "password_reset_tokens", ["user_id"], unique=False
    )
    op.create_table(
        "tenants",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("industry", sa.String(length=32), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "suspended",
                name="tenant_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("plan_code", sa.String(length=32), server_default="free", nullable=False),
        sa.Column(
            "settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_code"], ["plans.code"], name=op.f("fk_tenants_plan_code_plans")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenants")),
        sa.UniqueConstraint("slug", name=op.f("uq_tenants_slug")),
    )
    op.create_table(
        "audit_logs",
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column(
            "data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_audit_logs_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_audit_logs_user_id_users"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        "ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_audit_logs_tenant_id"), "audit_logs", ["tenant_id"], unique=False)
    op.create_table(
        "invitations",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "ANALYST",
                "VIEWER",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "workspace_ids", postgresql.ARRAY(sa.UUID()), server_default="{}", nullable=False
        ),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name=op.f("fk_invitations_invited_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_invitations_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invitations")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invitations_token_hash")),
    )
    op.create_index(op.f("ix_invitations_tenant_id"), "invitations", ["tenant_id"], unique=False)
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "ADMIN",
                "ANALYST",
                "VIEWER",
                name="role",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "disabled",
                name="membership_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("all_workspaces", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_memberships_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_memberships_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_memberships")),
        sa.UniqueConstraint("tenant_id", "user_id", name="uq_memberships_tenant_user"),
    )
    op.create_index(op.f("ix_memberships_tenant_id"), "memberships", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)
    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("family_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.UUID(), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_refresh_tokens_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_tokens_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(
        op.f("ix_refresh_tokens_family_id"), "refresh_tokens", ["family_id"], unique=False
    )
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)
    op.create_table(
        "subscriptions",
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_ref", sa.String(length=200), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_code"], ["plans.code"], name=op.f("fk_subscriptions_plan_code_plans")
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_subscriptions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subscriptions")),
    )
    op.create_index(
        op.f("ix_subscriptions_tenant_id"), "subscriptions", ["tenant_id"], unique=False
    )
    op.create_table(
        "workspaces",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=32), nullable=True),
        sa.Column("color", sa.String(length=16), server_default="#4f46e5", nullable=False),
        sa.Column(
            "settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_workspaces_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_workspaces_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_index(op.f("ix_workspaces_tenant_id"), "workspaces", ["tenant_id"], unique=False)
    op.create_table(
        "export_jobs",
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "xlsx",
                "pdf",
                "dataset_csv",
                "dataset_jsonl",
                "responses_csv",
                name="export_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "done",
                "failed",
                name="job_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("file_key", sa.String(length=500), nullable=True),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_export_jobs_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_export_jobs_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_export_jobs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_export_jobs")),
    )
    op.create_index(op.f("ix_export_jobs_tenant_id"), "export_jobs", ["tenant_id"], unique=False)
    op.create_table(
        "surveys",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "closed",
                "archived",
                name="survey_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "theme", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "settings", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "languages",
            postgresql.ARRAY(sa.String(length=8)),
            server_default="{vi}",
            nullable=False,
        ),
        sa.Column("default_language", sa.String(length=8), server_default="vi", nullable=False),
        sa.Column("is_quiz", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("current_version_id", sa.UUID(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_surveys_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_surveys_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_surveys_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_surveys")),
        sa.UniqueConstraint("slug", name=op.f("uq_surveys_slug")),
    )
    op.create_index(op.f("ix_surveys_tenant_id"), "surveys", ["tenant_id"], unique=False)
    op.create_index(
        "ix_surveys_tenant_workspace_status",
        "surveys",
        ["tenant_id", "workspace_id", "status"],
        unique=False,
    )
    op.create_index(op.f("ix_surveys_workspace_id"), "surveys", ["workspace_id"], unique=False)
    op.create_table(
        "topic_sets",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("template_code", sa.String(length=32), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_topic_sets_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_topic_sets_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topic_sets")),
        sa.UniqueConstraint("workspace_id", name=op.f("uq_topic_sets_workspace_id")),
    )
    op.create_index(op.f("ix_topic_sets_tenant_id"), "topic_sets", ["tenant_id"], unique=False)
    op.create_table(
        "workspace_members",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_workspace_members_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workspace_members_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_workspace_members_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspace_members")),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
    )
    op.create_index(
        op.f("ix_workspace_members_tenant_id"), "workspace_members", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_workspace_members_user_id"), "workspace_members", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_workspace_members_workspace_id"),
        "workspace_members",
        ["workspace_id"],
        unique=False,
    )
    op.create_table(
        "import_jobs",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=True),
        sa.Column(
            "kind",
            sa.Enum(
                "responses",
                "questions",
                name="import_kind",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "running",
                "done",
                "failed",
                name="job_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=300), nullable=False),
        sa.Column("file_key", sa.String(length=500), nullable=False),
        sa.Column(
            "mapping", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("total_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("success_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_rows", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_report_key", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_import_jobs_created_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_import_jobs_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_import_jobs_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_import_jobs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_jobs")),
    )
    op.create_index(op.f("ix_import_jobs_tenant_id"), "import_jobs", ["tenant_id"], unique=False)
    op.create_table(
        "questions",
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("title", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "description",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "options", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column(
            "logic", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("points", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_questions_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_questions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_questions")),
    )
    op.create_index(
        "ix_questions_survey_position", "questions", ["survey_id", "position"], unique=False
    )
    op.create_index(op.f("ix_questions_tenant_id"), "questions", ["tenant_id"], unique=False)
    op.create_table(
        "survey_channels",
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "link",
                "qr",
                "embed",
                "email",
                "kiosk",
                "zalo",
                "import",
                name="channel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column(
            "params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_survey_channels_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_survey_channels_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_channels")),
        sa.UniqueConstraint("survey_id", "code", name="uq_survey_channels_code"),
    )
    op.create_index(
        op.f("ix_survey_channels_survey_id"), "survey_channels", ["survey_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_channels_tenant_id"), "survey_channels", ["tenant_id"], unique=False
    )
    op.create_table(
        "survey_versions",
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_by", sa.UUID(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["published_by"],
            ["users.id"],
            name=op.f("fk_survey_versions_published_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_survey_versions_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_survey_versions_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_survey_versions")),
        sa.UniqueConstraint("survey_id", "version", name="uq_survey_versions_version"),
    )
    op.create_index(
        op.f("ix_survey_versions_survey_id"), "survey_versions", ["survey_id"], unique=False
    )
    op.create_index(
        op.f("ix_survey_versions_tenant_id"), "survey_versions", ["tenant_id"], unique=False
    )
    op.create_table(
        "topics",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("topic_set_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "keywords", postgresql.ARRAY(sa.String(length=100)), server_default="{}", nullable=False
        ),
        sa.Column("color", sa.String(length=16), server_default="#6366f1", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_topics_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["topic_set_id"],
            ["topic_sets.id"],
            name=op.f("fk_topics_topic_set_id_topic_sets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_topics_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
        sa.UniqueConstraint("topic_set_id", "name", name="uq_topics_set_name"),
    )
    op.create_index(op.f("ix_topics_tenant_id"), "topics", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_topics_topic_set_id"), "topics", ["topic_set_id"], unique=False)
    op.create_index(op.f("ix_topics_workspace_id"), "topics", ["workspace_id"], unique=False)
    op.create_table(
        "responses",
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("survey_version_id", sa.UUID(), nullable=True),
        sa.Column(
            "channel",
            sa.Enum(
                "link",
                "qr",
                "embed",
                "email",
                "kiosk",
                "zalo",
                "import",
                name="channel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("channel_id", sa.UUID(), nullable=True),
        sa.Column(
            "source_params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "respondent",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("language", sa.String(length=8), server_default="vi", nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "completed",
                "partial",
                "spam",
                name="response_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("fingerprint_hash", sa.String(length=128), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("rating", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("csat", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("nps", sa.SmallInteger(), nullable=True),
        sa.Column("score", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("external_id", sa.String(length=128), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["survey_channels.id"],
            name=op.f("fk_responses_channel_id_survey_channels"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_responses_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["survey_version_id"],
            ["survey_versions.id"],
            name=op.f("fk_responses_survey_version_id_survey_versions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_responses_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_responses_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_responses")),
    )
    op.create_index(op.f("ix_responses_ip_hash"), "responses", ["ip_hash"], unique=False)
    op.create_index(op.f("ix_responses_tenant_id"), "responses", ["tenant_id"], unique=False)
    op.create_index(
        "ix_responses_tenant_survey_created",
        "responses",
        ["tenant_id", "survey_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_responses_tenant_workspace_created",
        "responses",
        ["tenant_id", "workspace_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "answers",
        sa.Column("response_id", sa.UUID(), nullable=False),
        sa.Column("question_id", sa.UUID(), nullable=True),
        sa.Column("question_code", sa.String(length=64), nullable=False),
        sa.Column("question_type", sa.String(length=32), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            name=op.f("fk_answers_question_id_questions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["responses.id"],
            name=op.f("fk_answers_response_id_responses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_answers_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_answers")),
    )
    op.create_index(op.f("ix_answers_question_id"), "answers", ["question_id"], unique=False)
    op.create_index(op.f("ix_answers_response_id"), "answers", ["response_id"], unique=False)
    op.create_index(op.f("ix_answers_tenant_id"), "answers", ["tenant_id"], unique=False)
    op.create_table(
        "text_analyses",
        sa.Column("response_id", sa.UUID(), nullable=False),
        sa.Column("answer_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("survey_id", sa.UUID(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "link",
                "qr",
                "embed",
                "email",
                "kiosk",
                "zalo",
                "import",
                name="channel",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("rating", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column(
            "responded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column(
            "sentiment",
            sa.Enum(
                "positive",
                "negative",
                "neutral",
                name="sentiment",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
        sa.Column("sentiment_score", sa.Float(), nullable=True),
        sa.Column(
            "sentiment_detail",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("topic_ids", postgresql.ARRAY(sa.UUID()), server_default="{}", nullable=False),
        sa.Column(
            "topic_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("is_urgent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "urgent_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "keywords", postgresql.ARRAY(sa.String(length=64)), server_default="{}", nullable=False
        ),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("topic_set_version", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "done",
                "failed",
                "skipped",
                name="analysis_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_by", sa.UUID(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["answer_id"],
            ["answers.id"],
            name=op.f("fk_text_analyses_answer_id_answers"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["responses.id"],
            name=op.f("fk_text_analyses_response_id_responses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["survey_id"],
            ["surveys.id"],
            name=op.f("fk_text_analyses_survey_id_surveys"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_text_analyses_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["users.id"],
            name=op.f("fk_text_analyses_verified_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_text_analyses_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_text_analyses")),
        sa.UniqueConstraint("answer_id", name=op.f("uq_text_analyses_answer_id")),
    )
    op.create_index(
        op.f("ix_text_analyses_response_id"), "text_analyses", ["response_id"], unique=False
    )
    op.create_index("ix_text_analyses_status", "text_analyses", ["status"], unique=False)
    op.create_index(
        op.f("ix_text_analyses_tenant_id"), "text_analyses", ["tenant_id"], unique=False
    )
    op.create_index(
        "ix_text_analyses_tenant_sentiment",
        "text_analyses",
        ["tenant_id", "sentiment"],
        unique=False,
    )
    op.create_index(
        "ix_text_analyses_tenant_survey_created",
        "text_analyses",
        ["tenant_id", "survey_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_text_analyses_tenant_urgent", "text_analyses", ["tenant_id", "is_urgent"], unique=False
    )
    op.create_index(
        "ix_text_analyses_topic_ids",
        "text_analyses",
        ["topic_ids"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_table(
        "label_corrections",
        sa.Column("analysis_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "field",
            sa.Enum(
                "sentiment",
                "topics",
                "urgent",
                name="correction_field",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("old_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("new_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_for_training", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "review_status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                name="review_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["text_analyses.id"],
            name=op.f("fk_label_corrections_analysis_id_text_analyses"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["users.id"],
            name=op.f("fk_label_corrections_reviewed_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_label_corrections_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_label_corrections_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_label_corrections")),
    )
    op.create_index(
        op.f("ix_label_corrections_analysis_id"), "label_corrections", ["analysis_id"], unique=False
    )
    op.create_index(
        "ix_label_corrections_tenant_created",
        "label_corrections",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_label_corrections_tenant_id"), "label_corrections", ["tenant_id"], unique=False
    )
    op.create_table(
        "tickets",
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("response_id", sa.UUID(), nullable=True),
        sa.Column("analysis_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "in_progress",
                "done",
                name="ticket_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "normal",
                "high",
                "urgent",
                name="ticket_priority",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "notes", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_id"],
            ["text_analyses.id"],
            name=op.f("fk_tickets_analysis_id_text_analyses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name=op.f("fk_tickets_assignee_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["responses.id"],
            name=op.f("fk_tickets_response_id_responses"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name=op.f("fk_tickets_tenant_id_tenants"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_tickets_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tickets")),
        sa.UniqueConstraint("analysis_id", name=op.f("uq_tickets_analysis_id")),
    )
    op.create_index(op.f("ix_tickets_tenant_id"), "tickets", ["tenant_id"], unique=False)
    op.create_index("ix_tickets_tenant_status", "tickets", ["tenant_id", "status"], unique=False)
    # ### end Alembic commands ###

    # Khóa ngoại vòng surveys <-> survey_versions phải tạo sau khi cả hai bảng tồn tại.
    op.create_foreign_key(
        op.f("fk_surveys_current_version_id_survey_versions"),
        "surveys",
        "survey_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    _search_support()
    _enable_rls()
    _seed_plans()


def downgrade() -> None:
    _disable_rls()
    op.execute("DROP INDEX IF EXISTS ix_text_analyses_text_trgm")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
    op.drop_constraint(
        op.f("fk_surveys_current_version_id_survey_versions"), "surveys", type_="foreignkey"
    )
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_tickets_tenant_status", table_name="tickets")
    op.drop_index(op.f("ix_tickets_tenant_id"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_index(op.f("ix_label_corrections_tenant_id"), table_name="label_corrections")
    op.drop_index("ix_label_corrections_tenant_created", table_name="label_corrections")
    op.drop_index(op.f("ix_label_corrections_analysis_id"), table_name="label_corrections")
    op.drop_table("label_corrections")
    op.drop_index("ix_text_analyses_topic_ids", table_name="text_analyses", postgresql_using="gin")
    op.drop_index("ix_text_analyses_tenant_urgent", table_name="text_analyses")
    op.drop_index("ix_text_analyses_tenant_survey_created", table_name="text_analyses")
    op.drop_index("ix_text_analyses_tenant_sentiment", table_name="text_analyses")
    op.drop_index(op.f("ix_text_analyses_tenant_id"), table_name="text_analyses")
    op.drop_index("ix_text_analyses_status", table_name="text_analyses")
    op.drop_index(op.f("ix_text_analyses_response_id"), table_name="text_analyses")
    op.drop_table("text_analyses")
    op.drop_index(op.f("ix_answers_tenant_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_response_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_question_id"), table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_responses_tenant_workspace_created", table_name="responses")
    op.drop_index("ix_responses_tenant_survey_created", table_name="responses")
    op.drop_index(op.f("ix_responses_tenant_id"), table_name="responses")
    op.drop_index(op.f("ix_responses_ip_hash"), table_name="responses")
    op.drop_table("responses")
    op.drop_index(op.f("ix_topics_workspace_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_topic_set_id"), table_name="topics")
    op.drop_index(op.f("ix_topics_tenant_id"), table_name="topics")
    op.drop_table("topics")
    op.drop_index(op.f("ix_survey_versions_tenant_id"), table_name="survey_versions")
    op.drop_index(op.f("ix_survey_versions_survey_id"), table_name="survey_versions")
    op.drop_table("survey_versions")
    op.drop_index(op.f("ix_survey_channels_tenant_id"), table_name="survey_channels")
    op.drop_index(op.f("ix_survey_channels_survey_id"), table_name="survey_channels")
    op.drop_table("survey_channels")
    op.drop_index(op.f("ix_questions_tenant_id"), table_name="questions")
    op.drop_index("ix_questions_survey_position", table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_import_jobs_tenant_id"), table_name="import_jobs")
    op.drop_table("import_jobs")
    op.drop_index(op.f("ix_workspace_members_workspace_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_user_id"), table_name="workspace_members")
    op.drop_index(op.f("ix_workspace_members_tenant_id"), table_name="workspace_members")
    op.drop_table("workspace_members")
    op.drop_index(op.f("ix_topic_sets_tenant_id"), table_name="topic_sets")
    op.drop_table("topic_sets")
    op.drop_index(op.f("ix_surveys_workspace_id"), table_name="surveys")
    op.drop_index("ix_surveys_tenant_workspace_status", table_name="surveys")
    op.drop_index(op.f("ix_surveys_tenant_id"), table_name="surveys")
    op.drop_table("surveys")
    op.drop_index(op.f("ix_export_jobs_tenant_id"), table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index(op.f("ix_workspaces_tenant_id"), table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_subscriptions_tenant_id"), table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_family_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index(op.f("ix_memberships_user_id"), table_name="memberships")
    op.drop_index(op.f("ix_memberships_tenant_id"), table_name="memberships")
    op.drop_table("memberships")
    op.drop_index(op.f("ix_invitations_tenant_id"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("tenants")
    op.drop_index(op.f("ix_password_reset_tokens_user_id"), table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("users")
    op.drop_table("plans")
    op.drop_table("nlp_models")
    # ### end Alembic commands ###
