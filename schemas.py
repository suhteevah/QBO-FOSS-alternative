"""
Pydantic schemas for API validation and serialization.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ── Accounts ────────────────────────────────────────────────

class AccountCreate(BaseModel):
    account_number: str = Field(..., max_length=20, examples=["1000"])
    name: str = Field(..., max_length=255, examples=["Cash"])
    description: Optional[str] = None
    account_type: str  # AccountType enum value
    account_subtype: Optional[str] = None
    parent_id: Optional[UUID] = None

class AccountResponse(BaseModel):
    id: UUID
    account_number: str
    name: str
    description: Optional[str]
    account_type: str
    account_subtype: Optional[str]
    normal_balance: str
    is_active: bool
    model_config = {"from_attributes": True}


# ── Journal Entries ─────────────────────────────────────────

class LineItemCreate(BaseModel):
    account_id: UUID
    description: Optional[str] = None
    debit_amount: Decimal = Decimal("0.00")
    credit_amount: Decimal = Decimal("0.00")

    @model_validator(mode="after")
    def validate_single_side(self):
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValueError("A line item cannot have both debit and credit amounts")
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValueError("A line item must have either a debit or credit amount")
        return self


class JournalEntryCreate(BaseModel):
    entry_date: date
    description: str
    memo: Optional[str] = None
    source: str = "manual"
    line_items: list[LineItemCreate] = Field(..., min_length=2)

    @model_validator(mode="after")
    def validate_balanced(self):
        total_debits = sum(li.debit_amount for li in self.line_items)
        total_credits = sum(li.credit_amount for li in self.line_items)
        if total_debits != total_credits:
            raise ValueError(
                f"Entry is unbalanced: debits ({total_debits}) != credits ({total_credits})"
            )
        return self


class LineItemResponse(BaseModel):
    id: UUID
    account_id: UUID
    description: Optional[str]
    debit_amount: Decimal
    credit_amount: Decimal
    model_config = {"from_attributes": True}


class JournalEntryResponse(BaseModel):
    id: UUID
    entry_number: Optional[str]
    entry_date: date
    description: Optional[str]
    source: str
    status: str
    ai_confidence: Optional[Decimal]
    line_items: list[LineItemResponse] = []
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Bank Transaction Import ────────────────────────────────

class BankTransactionRow(BaseModel):
    """A single row from a bank CSV/XLSX import."""
    transaction_date: date
    description: str
    amount: Decimal
    post_date: Optional[date] = None
    balance: Optional[Decimal] = None
    reference_number: Optional[str] = None
    category: Optional[str] = None


class BankImportResponse(BaseModel):
    batch_id: UUID
    total_rows: int
    imported: int
    duplicates_skipped: int
    errors: list[str] = []


class BankTransactionResponse(BaseModel):
    id: UUID
    transaction_date: date
    description_raw: str
    description_cleaned: Optional[str]
    amount: Decimal
    ai_category: Optional[str]
    ai_confidence: Optional[Decimal]
    is_reconciled: bool
    suggested_account_id: Optional[UUID]
    model_config = {"from_attributes": True}


# ── Receipts ────────────────────────────────────────────────

class ReceiptResponse(BaseModel):
    id: UUID
    merchant_name: Optional[str]
    transaction_date: Optional[date]
    total_amount: Optional[Decimal]
    tax_amount: Optional[Decimal]
    line_items_json: Optional[dict]
    ocr_confidence: Optional[Decimal]
    is_processed: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── AI Query ────────────────────────────────────────────────

class AIQueryRequest(BaseModel):
    """Natural language query against the ledger."""
    query: str = Field(..., max_length=1000, examples=["What did I spend on supplies in Q3?"])


class AIQueryResponse(BaseModel):
    query: str
    interpreted_as: str  # How Sonnet parsed the intent
    sql_generated: Optional[str] = None  # The query it built (for transparency)
    results: list[dict]
    token_hash: str
    cached: bool = False
    model_config = {"from_attributes": True}


# ── Reports ─────────────────────────────────────────────────

class ReportRequest(BaseModel):
    report_type: str = Field(..., examples=["profit_loss", "balance_sheet", "trial_balance", "cash_flow"])
    start_date: date
    end_date: date
    accounting_basis: Optional[str] = None  # Override org default


class ReportLineItem(BaseModel):
    account_number: str
    account_name: str
    amount: Decimal


class ReportSection(BaseModel):
    title: str
    items: list[ReportLineItem]
    subtotal: Decimal


class ReportResponse(BaseModel):
    report_type: str
    period: str
    generated_at: datetime
    accounting_basis: str
    sections: list[ReportSection]
    net_total: Decimal


# ── Audit ───────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID]
    action: str
    entity_type: str
    entity_id: UUID
    before_state: Optional[dict]
    after_state: Optional[dict]
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Auth ────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
