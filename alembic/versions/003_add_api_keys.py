"""Add API keys table for mobile/programmatic auth

Revision ID: 003
Revises: 002
Create Date: 2026-02-16

Supports multi-platform API key authentication:
- Android, iOS, web, CLI clients
- Platform-aware device tracking
- SHA-256 hashed key storage
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "organization_id",
            sa.String(36),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(11), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("platform", sa.String(20), nullable=False, server_default="web"),
        sa.Column("device_info", sa.String(255), nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
        sa.Column("is_revoked", sa.Boolean, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Indexes for fast lookups
    op.create_index("ix_api_key_hash", "api_keys", ["key_hash"])
    op.create_index("ix_api_key_user", "api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_api_key_user", table_name="api_keys")
    op.drop_index("ix_api_key_hash", table_name="api_keys")
    op.drop_table("api_keys")
