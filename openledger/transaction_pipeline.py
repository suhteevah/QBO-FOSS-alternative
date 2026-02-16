"""
Transaction Pipeline — Bank Import to Journal Entry

Bridges the gap between imported bank transactions and proper double-entry
journal entries by orchestrating:
1. AI classification of raw bank transaction descriptions
2. Journal entry creation from high-confidence classifications

Flow:
  Bank CSV/XLSX → BankTransaction (staging) → AI classify → JournalEntry (ledger)

Accounting rules applied:
  - Negative amounts (expenses): debit expense account, credit Cash (1000)
  - Positive amounts (income/deposits): debit Cash (1000), credit revenue account
  - All entries are balanced (debits == credits) per GAAP
  - Entries below materiality threshold are auto-approved
  - All mutations produce audit log entries
"""

import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.models import (
    Account, AccountType, BankTransaction, JournalEntry,
    JournalLineItem, EntryStatus, TransactionSource, AuditLog,
)
from openledger.schemas import JournalEntryCreate, LineItemCreate
from openledger.ai_service import AIService
from openledger.ledger import LedgerEngine

logger = logging.getLogger(__name__)

# Standard GAAP cash account number
CASH_ACCOUNT_NUMBER = "1000"


class PipelineError(Exception):
    """Base exception for pipeline operations."""
    pass


class TransactionPipeline:
    """
    Orchestrates the bank transaction → journal entry pipeline.

    Connects AIService (classification) with LedgerEngine (entry creation)
    to convert raw imported bank transactions into proper double-entry
    journal entries.
    """

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id
        self.ai = AIService(db, organization_id)
        self.ledger = LedgerEngine(db, organization_id)

    # ── Classification ─────────────────────────────────────────

    async def classify_unprocessed(self, limit: int = 50) -> dict:
        """
        Find bank transactions with no AI classification and run them
        through AIService.classify_batch.

        Updates each transaction with:
          - suggested_account_id
          - ai_category
          - ai_confidence
          - description_cleaned

        Returns:
            {
                "classified": int,
                "errors": int,
                "transactions": [{"id": ..., "ai_category": ..., "confidence": ...}, ...]
            }
        """
        # Fetch unclassified transactions
        result = await self.db.execute(
            select(BankTransaction)
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.ai_category.is_(None),
            )
            .order_by(BankTransaction.transaction_date.desc())
            .limit(limit)
        )
        transactions = result.scalars().all()

        if not transactions:
            return {"classified": 0, "errors": 0, "transactions": []}

        # Run batch classification
        classifications = await self.ai.classify_batch(transactions)

        classified_count = 0
        error_count = 0
        classified_details = []

        for txn, classification in zip(transactions, classifications):
            try:
                confidence = Decimal(
                    str(classification.get("confidence", 0))
                ).quantize(Decimal("0.0001"))

                account_id = None
                account_id_str = classification.get("account_id")
                if account_id_str:
                    try:
                        account_id = uuid.UUID(account_id_str)
                        # Validate account exists and belongs to this org
                        acct_result = await self.db.execute(
                            select(Account.id).where(
                                Account.id == account_id,
                                Account.organization_id == self.org_id,
                                Account.is_active == True,
                            )
                        )
                        if not acct_result.scalar_one_or_none():
                            account_id = None
                    except (ValueError, AttributeError):
                        account_id = None

                ai_category = classification.get(
                    "account_name",
                    classification.get("account_number", "uncategorized"),
                )
                cleaned_desc = classification.get(
                    "cleaned_description", txn.description_raw
                )

                # Capture before state for audit
                before_state = {
                    "ai_category": txn.ai_category,
                    "ai_confidence": str(txn.ai_confidence) if txn.ai_confidence else None,
                    "suggested_account_id": str(txn.suggested_account_id) if txn.suggested_account_id else None,
                    "description_cleaned": txn.description_cleaned,
                }

                # Update the transaction
                txn.suggested_account_id = account_id
                txn.ai_category = ai_category
                txn.ai_confidence = confidence
                txn.description_cleaned = cleaned_desc

                # Audit log
                await self._audit(
                    action="ai_classify",
                    entity_type="bank_transaction",
                    entity_id=txn.id,
                    before_state=before_state,
                    after_state={
                        "ai_category": ai_category,
                        "ai_confidence": str(confidence),
                        "suggested_account_id": str(account_id) if account_id else None,
                        "description_cleaned": cleaned_desc,
                        "reasoning": classification.get("reasoning", ""),
                    },
                    extra_data={
                        "import_batch_id": str(txn.import_batch_id),
                        "amount": str(txn.amount),
                    },
                )

                classified_count += 1
                classified_details.append({
                    "id": str(txn.id),
                    "description_raw": txn.description_raw,
                    "ai_category": ai_category,
                    "confidence": float(confidence),
                    "suggested_account_id": str(account_id) if account_id else None,
                })

            except Exception as e:
                logger.error(
                    f"Failed to classify transaction {txn.id}: {e}",
                    exc_info=True,
                )
                error_count += 1

        return {
            "classified": classified_count,
            "errors": error_count,
            "transactions": classified_details,
        }

    # ── Journal Entry Creation ─────────────────────────────────

    async def create_entries_from_classified(
        self,
        confidence_threshold: float = 0.7,
        auto_approve_threshold: Decimal = Decimal("50.00"),
    ) -> dict:
        """
        Find classified but un-reconciled transactions above the confidence
        threshold and create balanced journal entries for each.

        For each transaction:
          - Negative amount (expense): debit suggested account, credit Cash
          - Positive amount (income):  debit Cash, credit suggested account

        Links the created journal entry to the bank transaction via
        bank_transaction.journal_entry_id and marks it reconciled.

        Returns:
            {
                "entries_created": int,
                "errors": int,
                "entries": [{"transaction_id": ..., "journal_entry_id": ..., "amount": ...}, ...]
            }
        """
        threshold = Decimal(str(confidence_threshold)).quantize(Decimal("0.0001"))

        # Fetch classified, un-reconciled transactions above threshold
        result = await self.db.execute(
            select(BankTransaction)
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.ai_category.isnot(None),
                BankTransaction.is_reconciled == False,
                BankTransaction.journal_entry_id.is_(None),
                BankTransaction.ai_confidence >= threshold,
                BankTransaction.suggested_account_id.isnot(None),
            )
            .order_by(BankTransaction.transaction_date)
        )
        transactions = result.scalars().all()

        if not transactions:
            return {"entries_created": 0, "errors": 0, "entries": []}

        # Look up the Cash account once
        cash_account = await self._get_cash_account()
        if not cash_account:
            raise PipelineError(
                f"Cash account ({CASH_ACCOUNT_NUMBER}) not found for organization. "
                "Please create it before running the pipeline."
            )

        created_count = 0
        error_count = 0
        entry_details = []

        for txn in transactions:
            try:
                entry = await self._create_entry_for_transaction(
                    txn, cash_account, auto_approve_threshold
                )

                # Link transaction to journal entry and mark reconciled
                txn.journal_entry_id = entry.id
                txn.is_reconciled = True
                txn.reconciled_at = datetime.utcnow()

                # Audit the reconciliation
                await self._audit(
                    action="pipeline_reconcile",
                    entity_type="bank_transaction",
                    entity_id=txn.id,
                    after_state={
                        "journal_entry_id": str(entry.id),
                        "is_reconciled": True,
                        "reconciled_at": txn.reconciled_at.isoformat(),
                    },
                    extra_data={
                        "pipeline": "auto",
                        "ai_confidence": str(txn.ai_confidence),
                        "amount": str(txn.amount),
                    },
                )

                created_count += 1
                entry_details.append({
                    "transaction_id": str(txn.id),
                    "journal_entry_id": str(entry.id),
                    "amount": str(abs(txn.amount)),
                    "status": entry.status.value,
                    "description": entry.description,
                })

            except Exception as e:
                logger.error(
                    f"Failed to create entry for transaction {txn.id}: {e}",
                    exc_info=True,
                )
                error_count += 1

        return {
            "entries_created": created_count,
            "errors": error_count,
            "entries": entry_details,
        }

    # ── Single Transaction Entry ───────────────────────────────

    async def create_entry_for_single(
        self,
        transaction_id: uuid.UUID,
        account_id_override: Optional[uuid.UUID] = None,
        auto_approve_threshold: Decimal = Decimal("50.00"),
    ) -> dict:
        """
        Create a journal entry from a single bank transaction.

        Allows an optional account_id override to manually specify
        the target account instead of using the AI suggestion.

        Returns:
            {
                "transaction_id": ...,
                "journal_entry_id": ...,
                "amount": ...,
                "status": ...,
            }
        """
        # Fetch the transaction
        result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.id == transaction_id,
                BankTransaction.organization_id == self.org_id,
            )
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise PipelineError(f"Bank transaction {transaction_id} not found")

        if txn.is_reconciled:
            raise PipelineError(
                f"Transaction {transaction_id} is already reconciled "
                f"(journal_entry_id={txn.journal_entry_id})"
            )

        # Determine target account
        target_account_id = account_id_override or txn.suggested_account_id
        if not target_account_id:
            raise PipelineError(
                f"Transaction {transaction_id} has no suggested account and "
                "no account_id override was provided. Classify it first or "
                "provide an account_id."
            )

        # Validate target account
        acct_result = await self.db.execute(
            select(Account).where(
                Account.id == target_account_id,
                Account.organization_id == self.org_id,
                Account.is_active == True,
            )
        )
        target_account = acct_result.scalar_one_or_none()
        if not target_account:
            raise PipelineError(
                f"Account {target_account_id} not found or inactive"
            )

        # Get Cash account
        cash_account = await self._get_cash_account()
        if not cash_account:
            raise PipelineError(
                f"Cash account ({CASH_ACCOUNT_NUMBER}) not found for organization"
            )

        # If using an override, update the transaction's suggested account
        if account_id_override and account_id_override != txn.suggested_account_id:
            before_acct = str(txn.suggested_account_id) if txn.suggested_account_id else None
            txn.suggested_account_id = account_id_override
            await self._audit(
                action="manual_override_account",
                entity_type="bank_transaction",
                entity_id=txn.id,
                before_state={"suggested_account_id": before_acct},
                after_state={"suggested_account_id": str(account_id_override)},
            )

        # Create the journal entry
        entry = await self._create_entry_for_transaction(
            txn, cash_account, auto_approve_threshold
        )

        # Link and reconcile
        txn.journal_entry_id = entry.id
        txn.is_reconciled = True
        txn.reconciled_at = datetime.utcnow()

        await self._audit(
            action="pipeline_reconcile",
            entity_type="bank_transaction",
            entity_id=txn.id,
            after_state={
                "journal_entry_id": str(entry.id),
                "is_reconciled": True,
                "reconciled_at": txn.reconciled_at.isoformat(),
            },
            extra_data={
                "pipeline": "manual_single",
                "account_override": str(account_id_override) if account_id_override else None,
                "amount": str(txn.amount),
            },
        )

        return {
            "transaction_id": str(txn.id),
            "journal_entry_id": str(entry.id),
            "amount": str(abs(txn.amount)),
            "status": entry.status.value,
            "description": entry.description,
        }

    # ── Full Pipeline ──────────────────────────────────────────

    async def process_batch(
        self,
        limit: int = 50,
        confidence_threshold: float = 0.7,
        auto_approve_threshold: Decimal = Decimal("50.00"),
    ) -> dict:
        """
        Convenience method: classify unprocessed transactions, then create
        journal entries from the high-confidence results.

        Returns combined results from both steps.
        """
        classify_result = await self.classify_unprocessed(limit=limit)

        # Flush to ensure classification updates are visible to the next query
        await self.db.flush()

        entries_result = await self.create_entries_from_classified(
            confidence_threshold=confidence_threshold,
            auto_approve_threshold=auto_approve_threshold,
        )

        return {
            "classification": classify_result,
            "entry_creation": entries_result,
            "summary": {
                "transactions_classified": classify_result["classified"],
                "classification_errors": classify_result["errors"],
                "entries_created": entries_result["entries_created"],
                "entry_errors": entries_result["errors"],
            },
        }

    # ── Internal Helpers ───────────────────────────────────────

    async def _create_entry_for_transaction(
        self,
        txn: BankTransaction,
        cash_account: Account,
        auto_approve_threshold: Decimal,
    ) -> JournalEntry:
        """
        Build and persist a balanced journal entry for a single bank transaction.

        Accounting logic:
          - Negative amount → expense: debit expense account, credit Cash
          - Positive amount → income:  debit Cash, credit revenue/asset account
        """
        abs_amount = abs(txn.amount)
        description = txn.description_cleaned or txn.description_raw

        # Determine the transaction source based on the bank transaction source
        source = txn.source.value if txn.source else TransactionSource.BANK_IMPORT_CSV.value

        if txn.amount < 0:
            # Expense: debit the expense/category account, credit Cash
            line_items = [
                LineItemCreate(
                    account_id=txn.suggested_account_id,
                    description=description,
                    debit_amount=abs_amount,
                    credit_amount=Decimal("0.00"),
                ),
                LineItemCreate(
                    account_id=cash_account.id,
                    description=description,
                    debit_amount=Decimal("0.00"),
                    credit_amount=abs_amount,
                ),
            ]
        else:
            # Income/deposit: debit Cash, credit revenue/asset account
            line_items = [
                LineItemCreate(
                    account_id=cash_account.id,
                    description=description,
                    debit_amount=abs_amount,
                    credit_amount=Decimal("0.00"),
                ),
                LineItemCreate(
                    account_id=txn.suggested_account_id,
                    description=description,
                    debit_amount=Decimal("0.00"),
                    credit_amount=abs_amount,
                ),
            ]

        entry_data = JournalEntryCreate(
            entry_date=txn.transaction_date,
            description=f"Bank import: {description}",
            memo=f"Auto-generated from bank transaction {txn.id}",
            source=source,
            line_items=line_items,
        )

        entry = await self.ledger.create_journal_entry(
            data=entry_data,
            auto_approve_threshold=auto_approve_threshold,
        )

        # Set AI metadata on the journal entry
        entry.ai_confidence = txn.ai_confidence
        entry.ai_classification_reason = (
            f"AI classified as '{txn.ai_category}' with "
            f"{float(txn.ai_confidence):.1%} confidence"
        )

        await self.db.flush()

        return entry

    async def _get_cash_account(self) -> Optional[Account]:
        """Look up the standard Cash account (1000) for this organization."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == self.org_id,
                Account.account_number == CASH_ACCOUNT_NUMBER,
                Account.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def _audit(
        self,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        before_state: Optional[dict] = None,
        after_state: Optional[dict] = None,
        user_id: Optional[uuid.UUID] = None,
        extra_data: Optional[dict] = None,
    ) -> None:
        """Write an immutable audit log entry."""
        log = AuditLog(
            organization_id=self.org_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            extra_data=extra_data,
        )
        self.db.add(log)
