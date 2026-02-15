"""
OpenLedger Database Models

Core double-entry bookkeeping schema enforcing GAAP principles:
- Every JournalEntry must have balanced debits and credits
- Accounts follow standard GAAP hierarchy
- All mutations produce audit log entries
- Periods can be closed to prevent retroactive changes
"""

import uuid
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Text, Numeric, DateTime, Date, Boolean,
    ForeignKey, Enum, CheckConstraint, Index, UniqueConstraint,
    event,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship, validates


# ── Base ────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Enums ───────────────────────────────────────────────────

class AccountType(str, PyEnum):
    """Standard GAAP account categories."""
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    CONTRA_ASSET = "contra_asset"
    CONTRA_LIABILITY = "contra_liability"
    CONTRA_EQUITY = "contra_equity"
    CONTRA_REVENUE = "contra_revenue"
    CONTRA_EXPENSE = "contra_expense"


class AccountSubtype(str, PyEnum):
    """Common GAAP subtypes for chart of accounts."""
    # Assets
    CASH = "cash"
    ACCOUNTS_RECEIVABLE = "accounts_receivable"
    INVENTORY = "inventory"
    PREPAID = "prepaid"
    FIXED_ASSET = "fixed_asset"
    OTHER_ASSET = "other_asset"
    # Liabilities
    ACCOUNTS_PAYABLE = "accounts_payable"
    CREDIT_CARD = "credit_card"
    ACCRUED_LIABILITY = "accrued_liability"
    LONG_TERM_DEBT = "long_term_debt"
    OTHER_LIABILITY = "other_liability"
    # Equity
    OWNERS_EQUITY = "owners_equity"
    RETAINED_EARNINGS = "retained_earnings"
    # Revenue
    SALES = "sales"
    SERVICE_REVENUE = "service_revenue"
    OTHER_INCOME = "other_income"
    # Expenses
    COST_OF_GOODS = "cost_of_goods"
    OPERATING_EXPENSE = "operating_expense"
    PAYROLL = "payroll"
    TAX_EXPENSE = "tax_expense"
    DEPRECIATION = "depreciation"
    OTHER_EXPENSE = "other_expense"


class EntryStatus(str, PyEnum):
    """Journal entry lifecycle."""
    DRAFT = "draft"               # AI-generated, awaiting review
    PENDING_REVIEW = "pending"    # Flagged for accountant review
    APPROVED = "approved"         # Accountant-approved
    AUTO_APPROVED = "auto"        # Below materiality threshold, auto-approved
    VOIDED = "voided"             # Reversed / cancelled


class TransactionSource(str, PyEnum):
    """Where the transaction data came from."""
    BANK_IMPORT_CSV = "bank_csv"
    BANK_IMPORT_XLSX = "bank_xlsx"
    MANUAL = "manual"
    RECEIPT_OCR = "receipt_ocr"
    API = "api"


class UserRole(str, PyEnum):
    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    CLIENT = "client"


class PeriodStatus(str, PyEnum):
    OPEN = "open"
    CLOSED = "closed"


# ── Organizations ───────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    accounting_basis = Column(String(10), nullable=False, default="accrual")
    fiscal_year_start_month = Column(Numeric, nullable=False, default=1)
    default_currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime, default=datetime.utcnow)

    accounts = relationship("Account", back_populates="organization")
    users = relationship("User", back_populates="organization")


# ── Users ───────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="users")


# ── Chart of Accounts ──────────────────────────────────────

class Account(Base):
    """
    GAAP-standard chart of accounts.
    
    account_number follows standard numbering:
      1000-1999: Assets
      2000-2999: Liabilities
      3000-3999: Equity
      4000-4999: Revenue
      5000-9999: Expenses
    """
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    account_number = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    account_type = Column(Enum(AccountType), nullable=False)
    account_subtype = Column(Enum(AccountSubtype))
    parent_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # Prevent deletion of core accounts
    normal_balance = Column(String(6), nullable=False)  # "debit" or "credit"
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="accounts")
    parent = relationship("Account", remote_side=[id])
    line_items = relationship("JournalLineItem", back_populates="account")

    __table_args__ = (
        UniqueConstraint("organization_id", "account_number", name="uq_org_account_number"),
        Index("ix_account_type", "organization_id", "account_type"),
    )

    @validates("normal_balance")
    def validate_normal_balance(self, key, value):
        if value not in ("debit", "credit"):
            raise ValueError("normal_balance must be 'debit' or 'credit'")
        return value


# ── Journal Entries ─────────────────────────────────────────

class JournalEntry(Base):
    """
    The core accounting record. Each entry contains 2+ line items
    that MUST balance (total debits == total credits).
    """
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    entry_number = Column(String(20))  # Auto-generated sequence
    entry_date = Column(Date, nullable=False)
    description = Column(Text)
    memo = Column(Text)
    source = Column(Enum(TransactionSource), nullable=False, default=TransactionSource.MANUAL)
    status = Column(Enum(EntryStatus), nullable=False, default=EntryStatus.DRAFT)

    # AI classification metadata
    ai_confidence = Column(Numeric(5, 4))  # 0.0000 - 1.0000
    ai_classification_reason = Column(Text)
    ai_query_token_hash = Column(String(64))  # For caching/dedup

    # Review tracking
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text)

    # Linked receipt
    receipt_id = Column(UUID(as_uuid=True), ForeignKey("receipts.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    line_items = relationship("JournalLineItem", back_populates="journal_entry", cascade="all, delete-orphan")
    receipt = relationship("Receipt", back_populates="journal_entries")

    __table_args__ = (
        Index("ix_journal_date", "organization_id", "entry_date"),
        Index("ix_journal_status", "organization_id", "status"),
    )


class JournalLineItem(Base):
    """
    Individual debit or credit within a journal entry.
    Enforced: exactly one of (debit_amount, credit_amount) must be > 0.
    """
    __tablename__ = "journal_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    description = Column(Text)
    debit_amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    credit_amount = Column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))

    journal_entry = relationship("JournalEntry", back_populates="line_items")
    account = relationship("Account", back_populates="line_items")

    __table_args__ = (
        # At least one side must be positive
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)",
            name="ck_single_side_entry",
        ),
        Index("ix_line_account", "account_id"),
    )


# ── Bank Transactions (Import Staging) ─────────────────────

class BankTransaction(Base):
    """
    Raw imported bank transactions before they become journal entries.
    This is the staging table for CSV/XLSX imports.
    """
    __tablename__ = "bank_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    import_batch_id = Column(UUID(as_uuid=True), nullable=False)  # Groups a single file import
    source = Column(Enum(TransactionSource), nullable=False)

    # Raw fields from bank export
    transaction_date = Column(Date, nullable=False)
    post_date = Column(Date)
    description_raw = Column(Text, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)  # Negative = debit/expense
    balance = Column(Numeric(15, 2))
    reference_number = Column(String(100))
    category_raw = Column(String(255))  # Bank's own category if provided

    # AI-enriched fields
    description_cleaned = Column(Text)
    suggested_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=True)
    ai_confidence = Column(Numeric(5, 4))
    ai_category = Column(String(255))

    # Reconciliation
    is_reconciled = Column(Boolean, default=False)
    journal_entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=True)
    reconciled_at = Column(DateTime)

    # Dedup
    transaction_hash = Column(String(64), nullable=False)  # SHA-256 of date+amount+desc

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_bank_txn_date", "organization_id", "transaction_date"),
        Index("ix_bank_txn_hash", "transaction_hash"),
        Index("ix_bank_txn_reconciled", "organization_id", "is_reconciled"),
    )


# ── Receipts ────────────────────────────────────────────────

class Receipt(Base):
    """
    Uploaded receipt images with OCR-extracted data.
    """
    __tablename__ = "receipts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # File storage
    file_path = Column(String(500), nullable=False)  # Path to original image/PDF
    file_hash = Column(String(64), nullable=False)    # SHA-256 for dedup
    mime_type = Column(String(100))

    # OCR-extracted fields
    merchant_name = Column(String(255))
    transaction_date = Column(Date)
    total_amount = Column(Numeric(15, 2))
    tax_amount = Column(Numeric(15, 2))
    currency = Column(String(3), default="USD")
    line_items_json = Column(JSONB)  # [{description, qty, unit_price, amount}]
    raw_ocr_text = Column(Text)

    # Processing metadata
    ocr_engine_used = Column(String(50))
    ocr_confidence = Column(Numeric(5, 4))
    is_processed = Column(Boolean, default=False)
    processing_errors = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    journal_entries = relationship("JournalEntry", back_populates="receipt")

    __table_args__ = (
        Index("ix_receipt_hash", "file_hash"),
    )


# ── Accounting Periods ──────────────────────────────────────

class AccountingPeriod(Base):
    """
    Fiscal periods that can be opened/closed.
    Closed periods reject new journal entries.
    """
    __tablename__ = "accounting_periods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(50), nullable=False)  # e.g., "2025-Q1", "2025-01"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(PeriodStatus), nullable=False, default=PeriodStatus.OPEN)
    closed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    closed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "start_date", "end_date", name="uq_org_period"),
    )


# ── Audit Log ───────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable log of every data mutation.
    Critical for GAAP compliance and accountant review.
    """
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # Null for system/AI actions
    action = Column(String(50), nullable=False)  # create, update, delete, approve, void, close_period
    entity_type = Column(String(50), nullable=False)  # journal_entry, account, bank_transaction, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    before_state = Column(JSONB)  # Snapshot before change
    after_state = Column(JSONB)   # Snapshot after change
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    extra_data = Column(JSONB)  # Extra context (e.g., AI confidence, import batch ID)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_time", "organization_id", "created_at"),
        Index("ix_audit_user", "user_id", "created_at"),
    )


# ── AI Query Cache ──────────────────────────────────────────

class AIQueryLog(Base):
    """
    Tracks all Sonnet API calls for cost management, caching, and audit.
    Token hashing enables dedup of similar queries.
    """
    __tablename__ = "ai_query_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    query_type = Column(String(50), nullable=False)  # classify, nl_query, ocr_enhance
    query_text = Column(Text, nullable=False)
    query_token_hash = Column(String(64), nullable=False)  # SHA-256 of normalized query
    response_text = Column(Text)
    response_structured = Column(JSONB)  # Parsed response data
    input_tokens = Column(Numeric)
    output_tokens = Column(Numeric)
    cost_usd = Column(Numeric(10, 6))
    model_used = Column(String(100))
    latency_ms = Column(Numeric)
    cached_hit = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ai_query_hash", "query_token_hash"),
        Index("ix_ai_query_type", "organization_id", "query_type"),
    )
