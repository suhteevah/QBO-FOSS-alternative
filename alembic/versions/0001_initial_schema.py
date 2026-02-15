"""Initial schema — all core OpenLedger tables

Revision ID: 0001
Revises: None
Create Date: 2026-02-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ──────────────────────────────────────────────
    account_type = postgresql.ENUM(
        "asset", "liability", "equity", "revenue", "expense",
        "contra_asset", "contra_liability", "contra_equity",
        "contra_revenue", "contra_expense",
        name="accounttype", create_type=True,
    )
    account_subtype = postgresql.ENUM(
        "cash", "accounts_receivable", "inventory", "prepaid", "fixed_asset", "other_asset",
        "accounts_payable", "credit_card", "accrued_liability", "long_term_debt", "other_liability",
        "owners_equity", "retained_earnings",
        "sales", "service_revenue", "other_income",
        "cost_of_goods", "operating_expense", "payroll", "tax_expense", "depreciation", "other_expense",
        name="accountsubtype", create_type=True,
    )
    entry_status = postgresql.ENUM(
        "draft", "pending", "approved", "auto", "voided",
        name="entrystatus", create_type=True,
    )
    transaction_source = postgresql.ENUM(
        "bank_csv", "bank_xlsx", "manual", "receipt_ocr", "api",
        name="transactionsource", create_type=True,
    )
    user_role = postgresql.ENUM(
        "admin", "accountant", "client",
        name="userrole", create_type=True,
    )
    period_status = postgresql.ENUM(
        "open", "closed",
        name="periodstatus", create_type=True,
    )

    account_type.create(op.get_bind(), checkfirst=True)
    account_subtype.create(op.get_bind(), checkfirst=True)
    entry_status.create(op.get_bind(), checkfirst=True)
    transaction_source.create(op.get_bind(), checkfirst=True)
    user_role.create(op.get_bind(), checkfirst=True)
    period_status.create(op.get_bind(), checkfirst=True)

    # ── Organizations ──────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("accounting_basis", sa.String(10), nullable=False, server_default="accrual"),
        sa.Column("fiscal_year_start_month", sa.Numeric(), nullable=False, server_default="1"),
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # ── Users ──────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.Enum("admin", "accountant", "client", name="userrole", create_type=False), nullable=False, server_default="client"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # ── Chart of Accounts ──────────────────────────────────
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("account_number", sa.String(20), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("account_type", sa.Enum(
            "asset", "liability", "equity", "revenue", "expense",
            "contra_asset", "contra_liability", "contra_equity",
            "contra_revenue", "contra_expense",
            name="accounttype", create_type=False,
        ), nullable=False),
        sa.Column("account_subtype", sa.Enum(
            "cash", "accounts_receivable", "inventory", "prepaid", "fixed_asset", "other_asset",
            "accounts_payable", "credit_card", "accrued_liability", "long_term_debt", "other_liability",
            "owners_equity", "retained_earnings",
            "sales", "service_revenue", "other_income",
            "cost_of_goods", "operating_expense", "payroll", "tax_expense", "depreciation", "other_expense",
            name="accountsubtype", create_type=False,
        )),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_system", sa.Boolean(), server_default="false"),
        sa.Column("normal_balance", sa.String(6), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "account_number", name="uq_org_account_number"),
    )
    op.create_index("ix_account_type", "accounts", ["organization_id", "account_type"])

    # ── Receipts ───────────────────────────────────────────
    op.create_table(
        "receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("merchant_name", sa.String(255)),
        sa.Column("transaction_date", sa.Date()),
        sa.Column("total_amount", sa.Numeric(15, 2)),
        sa.Column("tax_amount", sa.Numeric(15, 2)),
        sa.Column("currency", sa.String(3), server_default="USD"),
        sa.Column("line_items_json", postgresql.JSONB()),
        sa.Column("raw_ocr_text", sa.Text()),
        sa.Column("ocr_engine_used", sa.String(50)),
        sa.Column("ocr_confidence", sa.Numeric(5, 4)),
        sa.Column("is_processed", sa.Boolean(), server_default="false"),
        sa.Column("processing_errors", sa.Text()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_receipt_hash", "receipts", ["file_hash"])

    # ── Journal Entries ────────────────────────────────────
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("entry_number", sa.String(20)),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("memo", sa.Text()),
        sa.Column("source", sa.Enum(
            "bank_csv", "bank_xlsx", "manual", "receipt_ocr", "api",
            name="transactionsource", create_type=False,
        ), nullable=False, server_default="manual"),
        sa.Column("status", sa.Enum(
            "draft", "pending", "approved", "auto", "voided",
            name="entrystatus", create_type=False,
        ), nullable=False, server_default="draft"),
        sa.Column("ai_confidence", sa.Numeric(5, 4)),
        sa.Column("ai_classification_reason", sa.Text()),
        sa.Column("ai_query_token_hash", sa.String(64)),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_notes", sa.Text()),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("receipts.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_journal_date", "journal_entries", ["organization_id", "entry_date"])
    op.create_index("ix_journal_status", "journal_entries", ["organization_id", "status"])

    # ── Journal Line Items ─────────────────────────────────
    op.create_table(
        "journal_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id"), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("debit_amount", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.Column("credit_amount", sa.Numeric(15, 2), nullable=False, server_default="0.00"),
        sa.CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="ck_single_side_entry",
        ),
    )
    op.create_index("ix_line_account", "journal_line_items", ["account_id"])

    # ── Bank Transactions ──────────────────────────────────
    op.create_table(
        "bank_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.Enum(
            "bank_csv", "bank_xlsx", "manual", "receipt_ocr", "api",
            name="transactionsource", create_type=False,
        ), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("post_date", sa.Date()),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("balance", sa.Numeric(15, 2)),
        sa.Column("reference_number", sa.String(100)),
        sa.Column("category_raw", sa.String(255)),
        sa.Column("description_cleaned", sa.Text()),
        sa.Column("suggested_account_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("accounts.id"), nullable=True),
        sa.Column("ai_confidence", sa.Numeric(5, 4)),
        sa.Column("ai_category", sa.String(255)),
        sa.Column("is_reconciled", sa.Boolean(), server_default="false"),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("journal_entries.id"), nullable=True),
        sa.Column("reconciled_at", sa.DateTime()),
        sa.Column("transaction_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_bank_txn_date", "bank_transactions", ["organization_id", "transaction_date"])
    op.create_index("ix_bank_txn_hash", "bank_transactions", ["transaction_hash"])
    op.create_index("ix_bank_txn_reconciled", "bank_transactions", ["organization_id", "is_reconciled"])

    # ── Accounting Periods ─────────────────────────────────
    op.create_table(
        "accounting_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Enum("open", "closed", name="periodstatus", create_type=False), nullable=False, server_default="open"),
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", "start_date", "end_date", name="uq_org_period"),
    )

    # ── Audit Log ──────────────────────────────────────────
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("before_state", postgresql.JSONB()),
        sa.Column("after_state", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("extra_data", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("ix_audit_time", "audit_log", ["organization_id", "created_at"])
    op.create_index("ix_audit_user", "audit_log", ["user_id", "created_at"])

    # ── AI Query Log ───────────────────────────────────────
    op.create_table(
        "ai_query_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("query_type", sa.String(50), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("query_token_hash", sa.String(64), nullable=False),
        sa.Column("response_text", sa.Text()),
        sa.Column("response_structured", postgresql.JSONB()),
        sa.Column("input_tokens", sa.Numeric()),
        sa.Column("output_tokens", sa.Numeric()),
        sa.Column("cost_usd", sa.Numeric(10, 6)),
        sa.Column("model_used", sa.String(100)),
        sa.Column("latency_ms", sa.Numeric()),
        sa.Column("cached_hit", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_query_hash", "ai_query_log", ["query_token_hash"])
    op.create_index("ix_ai_query_type", "ai_query_log", ["organization_id", "query_type"])


def downgrade() -> None:
    op.drop_table("ai_query_log")
    op.drop_table("audit_log")
    op.drop_table("accounting_periods")
    op.drop_table("bank_transactions")
    op.drop_table("journal_line_items")
    op.drop_table("journal_entries")
    op.drop_table("receipts")
    op.drop_table("accounts")
    op.drop_table("users")
    op.drop_table("organizations")

    op.execute("DROP TYPE IF EXISTS accounttype")
    op.execute("DROP TYPE IF EXISTS accountsubtype")
    op.execute("DROP TYPE IF EXISTS entrystatus")
    op.execute("DROP TYPE IF EXISTS transactionsource")
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS periodstatus")
