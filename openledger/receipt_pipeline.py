"""
Receipt OCR -> Journal Entry Pipeline

Bridges the gap between receipt data extraction (OCR) and accounting entries.

Pipeline:
1. Receipt is uploaded and OCR-processed (ocr_service.py) -> Receipt record
2. AI classifies the receipt into a chart of accounts category (this module)
3. A balanced journal entry is created from the receipt data (this module)

Handles:
- AI-powered expense classification via AIService
- Tax-splitting (separate debit for sales tax vs. expense)
- Idempotency (prevents duplicate entries for the same receipt)
- Audit logging for GAAP compliance
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from openledger.ai_service import AIService
from openledger.ledger import LedgerEngine, LedgerError
from openledger.models import (
    Account,
    AccountSubtype,
    AccountType,
    JournalEntry,
    Receipt,
    TransactionSource,
)
from openledger.schemas import JournalEntryCreate, LineItemCreate


# ── Default Account Numbers ────────────────────────────────
# Standard GAAP chart of accounts numbers used as fallbacks.

DEFAULT_CASH_ACCOUNT_NUMBER = "1000"
DEFAULT_TAX_EXPENSE_ACCOUNT_NUMBER = "6900"


class ReceiptPipelineError(Exception):
    """Base exception for receipt pipeline operations."""
    pass


class ReceiptNotFoundError(ReceiptPipelineError):
    pass


class ReceiptNotProcessedError(ReceiptPipelineError):
    pass


class ReceiptAlreadyLinkedError(ReceiptPipelineError):
    pass


class ReceiptMissingDataError(ReceiptPipelineError):
    pass


class AccountNotFoundError(ReceiptPipelineError):
    pass


class ReceiptPipeline:
    """
    Converts OCR-processed receipts into GAAP-compliant journal entries.

    Usage:
        pipeline = ReceiptPipeline(db, organization_id)
        classification = await pipeline.classify_receipt(receipt_id)
        entry = await pipeline.create_entry_from_receipt(receipt_id)
    """

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id
        self.ledger = LedgerEngine(db, organization_id)
        self.ai = AIService(db, organization_id)

    # ── Receipt Classification ─────────────────────────────

    async def classify_receipt(self, receipt_id: uuid.UUID) -> dict:
        """
        Use AI to classify a receipt into a chart of accounts category.

        Returns:
            {
                "receipt_id": str (UUID),
                "suggested_account_id": str (UUID) or None,
                "suggested_account_name": str,
                "suggested_account_number": str,
                "confidence": float,
                "reasoning": str,
            }
        """
        receipt = await self._get_receipt(receipt_id)
        self._validate_receipt_processed(receipt)

        # Build a descriptive string for the AI classifier
        description = self._build_classification_description(receipt)

        # Use the existing AIService classification pipeline
        classification = await self.ai.classify_transaction(
            description=description,
            amount=-(receipt.total_amount or Decimal("0.00")),  # Expenses are negative
        )

        return {
            "receipt_id": str(receipt_id),
            "suggested_account_id": classification.get("account_id"),
            "suggested_account_name": classification.get("account_name", ""),
            "suggested_account_number": classification.get("account_number", ""),
            "confidence": classification.get("confidence", 0.0),
            "reasoning": classification.get("reasoning", ""),
        }

    # ── Journal Entry Creation ─────────────────────────────

    async def create_entry_from_receipt(
        self,
        receipt_id: uuid.UUID,
        account_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        """
        Create a balanced double-entry journal entry from receipt data.

        If account_id is provided, it is used as the expense account.
        Otherwise, AI classification determines the expense account.

        Accounting logic:
        - If no tax: Debit Expense for total, Credit Cash for total
        - If tax exists: Debit Expense for (total - tax),
                         Debit Tax Expense for tax,
                         Credit Cash for total

        Args:
            receipt_id: The receipt to create an entry from.
            account_id: Optional override for the expense account.
            created_by: The user creating the entry.

        Returns:
            The created JournalEntry with line_items loaded.

        Raises:
            ReceiptNotFoundError: Receipt does not exist in this org.
            ReceiptNotProcessedError: Receipt has not been OCR-processed.
            ReceiptAlreadyLinkedError: Receipt is already linked to a journal entry.
            ReceiptMissingDataError: Receipt is missing total_amount.
            AccountNotFoundError: Specified or resolved account not found.
        """
        receipt = await self._get_receipt(receipt_id)
        self._validate_receipt_processed(receipt)
        await self._validate_receipt_not_linked(receipt)
        self._validate_receipt_has_total(receipt)

        # ── Step 1: Resolve the expense account ────────────
        ai_confidence = None
        ai_reasoning = None

        if account_id:
            # Explicit account — validate it exists in this org
            expense_account_id = await self._validate_account(account_id)
        else:
            # No explicit account — use AI classification
            classification = await self.classify_receipt(receipt_id)
            if classification["suggested_account_id"]:
                expense_account_id = uuid.UUID(classification["suggested_account_id"])
                ai_confidence = Decimal(str(classification["confidence"]))
                ai_reasoning = classification["reasoning"]
            else:
                raise AccountNotFoundError(
                    "AI classification could not determine an expense account. "
                    "Please provide an account_id explicitly."
                )

        # ── Step 2: Resolve the cash account (credit side) ─
        cash_account = await self._find_account_by_number(DEFAULT_CASH_ACCOUNT_NUMBER)
        if not cash_account:
            raise AccountNotFoundError(
                f"Cash account ({DEFAULT_CASH_ACCOUNT_NUMBER}) not found. "
                "Ensure the chart of accounts is initialized."
            )

        # ── Step 3: Resolve tax account if needed ──────────
        tax = receipt.tax_amount or Decimal("0.00")
        tax_account_id = None
        if tax > 0:
            tax_account_id = await self._resolve_tax_account_id()
            # If no dedicated tax account, lump tax into the expense account
            if not tax_account_id:
                tax_account_id = expense_account_id

        # ── Step 4: Build balanced line items ──────────────
        line_items = self._build_line_items(
            receipt, expense_account_id, cash_account.id, tax_account_id
        )

        # ── Step 5: Create journal entry via LedgerEngine ──
        entry_data = JournalEntryCreate(
            entry_date=receipt.transaction_date or date.today(),
            description=self._build_entry_description(receipt),
            memo=f"Auto-generated from receipt: {receipt.merchant_name or 'Unknown'}",
            source=TransactionSource.RECEIPT_OCR.value,
            line_items=line_items,
        )

        entry = await self.ledger.create_journal_entry(
            data=entry_data,
            created_by=created_by,
        )

        # ── Step 6: Link receipt and set AI metadata ───────
        entry.receipt_id = receipt_id

        if ai_confidence is not None:
            entry.ai_confidence = ai_confidence
            entry.ai_classification_reason = ai_reasoning

        await self.db.flush()

        # ── Step 7: Audit the receipt-to-entry linkage ─────
        await self.ledger._audit(
            action="link_receipt",
            entity_type="journal_entry",
            entity_id=entry.id,
            after_state={
                "receipt_id": str(receipt_id),
                "merchant": receipt.merchant_name,
                "total": str(receipt.total_amount),
                "tax": str(receipt.tax_amount) if receipt.tax_amount else None,
                "expense_account_id": str(expense_account_id),
                "ai_classified": account_id is None,
            },
            user_id=created_by,
        )

        # ── Step 8: Reload with line items for response ────
        result = await self.db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.line_items))
            .where(JournalEntry.id == entry.id)
        )
        return result.scalar_one()

    # ── Line Item Construction ─────────────────────────────

    def _build_line_items(
        self,
        receipt: Receipt,
        expense_account_id: uuid.UUID,
        cash_account_id: uuid.UUID,
        tax_account_id: Optional[uuid.UUID],
    ) -> list[LineItemCreate]:
        """
        Build balanced journal entry line items from receipt data.

        If tax exists, splits into separate expense and tax debit line items.
        Total debits always equal total credits (GAAP balanced entry).
        """
        total = receipt.total_amount
        tax = receipt.tax_amount or Decimal("0.00")
        expense_amount = total - tax
        merchant = receipt.merchant_name or "Unknown"

        items = []

        # Debit: Expense account (net of tax)
        if expense_amount > 0:
            items.append(
                LineItemCreate(
                    account_id=expense_account_id,
                    description=f"Receipt expense: {merchant}",
                    debit_amount=expense_amount,
                    credit_amount=Decimal("0.00"),
                )
            )

        # Debit: Tax expense account (if tax exists)
        if tax > 0 and tax_account_id:
            items.append(
                LineItemCreate(
                    account_id=tax_account_id,
                    description=f"Sales tax: {merchant}",
                    debit_amount=tax,
                    credit_amount=Decimal("0.00"),
                )
            )

        # Credit: Cash account for full total
        items.append(
            LineItemCreate(
                account_id=cash_account_id,
                description=f"Cash payment: {merchant}",
                debit_amount=Decimal("0.00"),
                credit_amount=total,
            )
        )

        return items

    # ── Account Resolution ─────────────────────────────────

    async def _validate_account(self, account_id: uuid.UUID) -> uuid.UUID:
        """Validate that an account exists and is active in this org."""
        result = await self.db.execute(
            select(Account).where(
                Account.id == account_id,
                Account.organization_id == self.org_id,
                Account.is_active == True,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise AccountNotFoundError(
                f"Account {account_id} not found or inactive"
            )
        return account.id

    async def _resolve_tax_account_id(self) -> Optional[uuid.UUID]:
        """
        Find a tax expense account for this organization.

        Search order:
        1. Account with subtype TAX_EXPENSE
        2. Account with number 6900 (default tax expense)
        3. None (caller will fall back to expense account)
        """
        # Try by subtype
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == self.org_id,
                Account.account_subtype == AccountSubtype.TAX_EXPENSE,
                Account.is_active == True,
            ).limit(1)
        )
        tax_account = result.scalar_one_or_none()
        if tax_account:
            return tax_account.id

        # Try by account number
        tax_account = await self._find_account_by_number(DEFAULT_TAX_EXPENSE_ACCOUNT_NUMBER)
        if tax_account:
            return tax_account.id

        return None

    async def _find_account_by_number(self, account_number: str) -> Optional[Account]:
        """Look up an account by its number within the organization."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == self.org_id,
                Account.account_number == account_number,
            )
        )
        return result.scalar_one_or_none()

    # ── Validation Helpers ─────────────────────────────────

    async def _get_receipt(self, receipt_id: uuid.UUID) -> Receipt:
        """Fetch a receipt, scoped to the organization."""
        result = await self.db.execute(
            select(Receipt).where(
                Receipt.id == receipt_id,
                Receipt.organization_id == self.org_id,
            )
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise ReceiptNotFoundError(
                f"Receipt {receipt_id} not found in this organization"
            )
        return receipt

    def _validate_receipt_processed(self, receipt: Receipt) -> None:
        """Ensure the receipt has been OCR-processed."""
        if not receipt.is_processed:
            raise ReceiptNotProcessedError(
                f"Receipt {receipt.id} has not been processed by OCR. "
                "Process the receipt before creating a journal entry."
            )

    async def _validate_receipt_not_linked(self, receipt: Receipt) -> None:
        """Ensure the receipt is not already linked to a journal entry."""
        result = await self.db.execute(
            select(JournalEntry.id).where(
                JournalEntry.receipt_id == receipt.id,
                JournalEntry.organization_id == self.org_id,
            ).limit(1)
        )
        existing_entry = result.scalar_one_or_none()
        if existing_entry:
            raise ReceiptAlreadyLinkedError(
                f"Receipt {receipt.id} is already linked to journal entry "
                f"{existing_entry}. Void the existing entry before creating a new one."
            )

    def _validate_receipt_has_total(self, receipt: Receipt) -> None:
        """Ensure the receipt has a total amount."""
        if not receipt.total_amount or receipt.total_amount <= 0:
            raise ReceiptMissingDataError(
                f"Receipt {receipt.id} has no total_amount. "
                "OCR may have failed to extract the total."
            )

    # ── Description Builders ───────────────────────────────

    def _build_classification_description(self, receipt: Receipt) -> str:
        """Build a descriptive string for AI classification."""
        parts = []
        if receipt.merchant_name:
            parts.append(receipt.merchant_name)
        if receipt.line_items_json:
            items = receipt.line_items_json
            if isinstance(items, list):
                item_descriptions = [
                    item.get("description", "") for item in items[:5]
                ]
                parts.append("Items: " + ", ".join(filter(None, item_descriptions)))
        if not parts:
            parts.append("Receipt purchase")
        return " | ".join(parts)

    def _build_entry_description(self, receipt: Receipt) -> str:
        """Build a human-readable journal entry description."""
        merchant = receipt.merchant_name or "Unknown merchant"
        date_str = (
            receipt.transaction_date.isoformat()
            if receipt.transaction_date
            else "unknown date"
        )
        return f"Receipt: {merchant} on {date_str}"
