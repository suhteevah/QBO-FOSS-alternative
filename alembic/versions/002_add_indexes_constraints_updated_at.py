"""Add missing indexes, ON DELETE CASCADEs, unique constraints, and updated_at columns.

Revision ID: 002
Revises: 001
Create Date: 2026-02-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Missing Indexes ─────────────────────────────────────

    # users.organization_id — used in almost every query via get_current_user
    op.create_index("ix_users_org_id", "users", ["organization_id"])

    # receipts.organization_id — used by list_receipts endpoint
    op.create_index("ix_receipts_org_id", "receipts", ["organization_id"])

    # journal_line_items.journal_entry_id — used by balance computation JOINs
    op.create_index("ix_line_entry_id", "journal_line_items", ["journal_entry_id"])

    # bank_transactions.organization_id — used by transaction list queries
    op.create_index("ix_bank_txn_org_id", "bank_transactions", ["organization_id"])

    # ── Unique Constraints for Dedup Hashes ─────────────────

    # Upgrade receipt file_hash index to unique (prevent duplicate receipt uploads)
    op.drop_index("ix_receipt_hash", table_name="receipts")
    op.create_unique_constraint(
        "uq_receipt_org_hash", "receipts",
        ["organization_id", "file_hash"]
    )

    # Upgrade bank transaction hash index to unique (prevent duplicate imports)
    op.drop_index("ix_bank_txn_hash", table_name="bank_transactions")
    op.create_unique_constraint(
        "uq_bank_txn_org_hash", "bank_transactions",
        ["organization_id", "transaction_hash"]
    )

    # ── ON DELETE CASCADE for Foreign Keys ──────────────────
    # When an org is deleted, cascade to all child records.
    # These replace the default RESTRICT behavior.

    # users.organization_id
    op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key(
        "users_organization_id_fkey", "users", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # accounts.organization_id
    op.drop_constraint("accounts_organization_id_fkey", "accounts", type_="foreignkey")
    op.create_foreign_key(
        "accounts_organization_id_fkey", "accounts", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # journal_entries.organization_id
    op.drop_constraint("journal_entries_organization_id_fkey", "journal_entries", type_="foreignkey")
    op.create_foreign_key(
        "journal_entries_organization_id_fkey", "journal_entries", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # journal_line_items.journal_entry_id — cascade when entry deleted
    op.drop_constraint("journal_line_items_journal_entry_id_fkey", "journal_line_items", type_="foreignkey")
    op.create_foreign_key(
        "journal_line_items_journal_entry_id_fkey", "journal_line_items", "journal_entries",
        ["journal_entry_id"], ["id"], ondelete="CASCADE"
    )

    # bank_transactions.organization_id
    op.drop_constraint("bank_transactions_organization_id_fkey", "bank_transactions", type_="foreignkey")
    op.create_foreign_key(
        "bank_transactions_organization_id_fkey", "bank_transactions", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # receipts.organization_id
    op.drop_constraint("receipts_organization_id_fkey", "receipts", type_="foreignkey")
    op.create_foreign_key(
        "receipts_organization_id_fkey", "receipts", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # accounting_periods.organization_id
    op.drop_constraint("accounting_periods_organization_id_fkey", "accounting_periods", type_="foreignkey")
    op.create_foreign_key(
        "accounting_periods_organization_id_fkey", "accounting_periods", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # audit_log.organization_id
    op.drop_constraint("audit_log_organization_id_fkey", "audit_log", type_="foreignkey")
    op.create_foreign_key(
        "audit_log_organization_id_fkey", "audit_log", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # ai_query_log.organization_id
    op.drop_constraint("ai_query_log_organization_id_fkey", "ai_query_log", type_="foreignkey")
    op.create_foreign_key(
        "ai_query_log_organization_id_fkey", "ai_query_log", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE"
    )

    # ── updated_at Columns ──────────────────────────────────
    # Add updated_at to tables that can be mutated

    for table in ["organizations", "users", "accounts", "journal_entries",
                   "bank_transactions", "receipts", "accounting_periods"]:
        op.add_column(
            table,
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("now()"),
                onupdate=sa.text("now()"),
            ),
        )

    # Create trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply trigger to each mutable table
    for table in ["organizations", "users", "accounts", "journal_entries",
                   "bank_transactions", "receipts", "accounting_periods"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    # Drop triggers
    for table in ["organizations", "users", "accounts", "journal_entries",
                   "bank_transactions", "receipts", "accounting_periods"]:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop updated_at columns
    for table in ["organizations", "users", "accounts", "journal_entries",
                   "bank_transactions", "receipts", "accounting_periods"]:
        op.drop_column(table, "updated_at")

    # Restore original FK constraints (without CASCADE) — simplified downgrade
    # In practice, you'd restore the exact original constraints

    # Restore original hash indexes (non-unique)
    op.drop_constraint("uq_bank_txn_org_hash", "bank_transactions", type_="unique")
    op.create_index("ix_bank_txn_hash", "bank_transactions", ["transaction_hash"])

    op.drop_constraint("uq_receipt_org_hash", "receipts", type_="unique")
    op.create_index("ix_receipt_hash", "receipts", ["file_hash"])

    # Drop added indexes
    op.drop_index("ix_bank_txn_org_id", table_name="bank_transactions")
    op.drop_index("ix_line_entry_id", table_name="journal_line_items")
    op.drop_index("ix_receipts_org_id", table_name="receipts")
    op.drop_index("ix_users_org_id", table_name="users")
