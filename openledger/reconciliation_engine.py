"""
Reconciliation Engine

Matches imported bank transactions to journal entries using:
1. Exact amount matching
2. Date proximity (within configurable window)
3. Description similarity (simple token overlap)

Workflow:
  1. Fetch unreconciled bank transactions
  2. For each, find candidate journal entries
  3. Score and rank matches
  4. Return suggestions for user review
  5. Apply confirmed matches (link txn → journal entry, mark reconciled)
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from openledger.models import (
    BankTransaction, JournalEntry, JournalLineItem,
    Account, AccountType, EntryStatus, AuditLog,
)


class ReconciliationEngine:
    """Matches bank transactions to journal entries."""

    def __init__(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        date_window_days: int = 3,
        min_score: float = 0.4,
    ):
        self.db = db
        self.org_id = organization_id
        self.date_window = timedelta(days=date_window_days)
        self.min_score = min_score

    # ── Auto-Match ─────────────────────────────────────────

    async def find_matches(
        self,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find match suggestions for all unreconciled bank transactions.

        Returns a list of:
        {
            "bank_transaction": {...},
            "suggestions": [
                {"journal_entry_id": ..., "score": ..., "reason": ...},
                ...
            ]
        }
        """
        # Get unreconciled transactions
        txn_result = await self.db.execute(
            select(BankTransaction)
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.is_reconciled == False,
            )
            .order_by(BankTransaction.transaction_date.desc())
            .limit(limit)
        )
        transactions = txn_result.scalars().all()

        if not transactions:
            return []

        # Get unmatched journal entries (approved, not yet linked to a bank txn)
        # Build a date range covering all transactions +/- window
        min_date = min(t.transaction_date for t in transactions) - self.date_window
        max_date = max(t.transaction_date for t in transactions) + self.date_window

        entry_result = await self.db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.line_items).selectinload(JournalLineItem.account))
            .where(
                JournalEntry.organization_id == self.org_id,
                JournalEntry.status.in_([EntryStatus.APPROVED, EntryStatus.AUTO_APPROVED]),
                JournalEntry.entry_date >= min_date,
                JournalEntry.entry_date <= max_date,
            )
        )
        entries = entry_result.scalars().unique().all()

        # Get already-reconciled entry IDs to exclude
        reconciled_result = await self.db.execute(
            select(BankTransaction.journal_entry_id)
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.is_reconciled == True,
                BankTransaction.journal_entry_id != None,
            )
        )
        reconciled_entry_ids = {row[0] for row in reconciled_result.all()}

        available_entries = [e for e in entries if e.id not in reconciled_entry_ids]

        # Score each transaction against available entries
        results = []
        for txn in transactions:
            suggestions = []
            for entry in available_entries:
                score, reason = self._score_match(txn, entry)
                if score >= self.min_score:
                    suggestions.append({
                        "journal_entry_id": str(entry.id),
                        "entry_date": str(entry.entry_date),
                        "description": entry.description,
                        "entry_total": str(self._entry_total(entry)),
                        "score": round(score, 3),
                        "reason": reason,
                    })

            suggestions.sort(key=lambda s: s["score"], reverse=True)

            results.append({
                "bank_transaction": {
                    "id": str(txn.id),
                    "transaction_date": str(txn.transaction_date),
                    "description_raw": txn.description_raw,
                    "description_cleaned": txn.description_cleaned,
                    "amount": str(txn.amount),
                },
                "suggestions": suggestions[:5],  # Top 5
            })

        return results

    # ── Apply Match ────────────────────────────────────────

    async def reconcile(
        self,
        bank_transaction_id: uuid.UUID,
        journal_entry_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Link a bank transaction to a journal entry and mark it reconciled.
        """
        # Fetch the transaction
        txn_result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.id == bank_transaction_id,
                BankTransaction.organization_id == self.org_id,
            )
        )
        txn = txn_result.scalar_one_or_none()
        if not txn:
            raise ValueError(f"Bank transaction {bank_transaction_id} not found")
        if txn.is_reconciled:
            raise ValueError("Transaction is already reconciled")

        # Verify the journal entry exists and belongs to this org
        entry_result = await self.db.execute(
            select(JournalEntry).where(
                JournalEntry.id == journal_entry_id,
                JournalEntry.organization_id == self.org_id,
            )
        )
        entry = entry_result.scalar_one_or_none()
        if not entry:
            raise ValueError(f"Journal entry {journal_entry_id} not found")

        # Apply the match
        txn.is_reconciled = True
        txn.journal_entry_id = journal_entry_id
        txn.reconciled_at = datetime.utcnow()

        # Audit log
        audit = AuditLog(
            organization_id=self.org_id,
            user_id=user_id,
            action="reconcile",
            entity_type="bank_transaction",
            entity_id=txn.id,
            after_state={
                "journal_entry_id": str(journal_entry_id),
                "amount": str(txn.amount),
                "transaction_date": str(txn.transaction_date),
            },
        )
        self.db.add(audit)

        return {
            "bank_transaction_id": str(txn.id),
            "journal_entry_id": str(journal_entry_id),
            "reconciled": True,
        }

    # ── Undo Reconciliation ────────────────────────────────

    async def unreconcile(
        self,
        bank_transaction_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """Undo a reconciliation — unlink the bank transaction from its journal entry."""
        txn_result = await self.db.execute(
            select(BankTransaction).where(
                BankTransaction.id == bank_transaction_id,
                BankTransaction.organization_id == self.org_id,
            )
        )
        txn = txn_result.scalar_one_or_none()
        if not txn:
            raise ValueError(f"Bank transaction {bank_transaction_id} not found")
        if not txn.is_reconciled:
            raise ValueError("Transaction is not reconciled")

        old_entry_id = txn.journal_entry_id
        txn.is_reconciled = False
        txn.journal_entry_id = None
        txn.reconciled_at = None

        audit = AuditLog(
            organization_id=self.org_id,
            user_id=user_id,
            action="unreconcile",
            entity_type="bank_transaction",
            entity_id=txn.id,
            before_state={"journal_entry_id": str(old_entry_id)},
            after_state={"journal_entry_id": None},
        )
        self.db.add(audit)

        return {
            "bank_transaction_id": str(txn.id),
            "reconciled": False,
        }

    # ── Summary ────────────────────────────────────────────

    async def get_summary(self) -> dict:
        """Get reconciliation summary statistics."""
        total = await self.db.execute(
            select(func.count(BankTransaction.id))
            .where(BankTransaction.organization_id == self.org_id)
        )
        reconciled = await self.db.execute(
            select(func.count(BankTransaction.id))
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.is_reconciled == True,
            )
        )
        unreconciled_amount = await self.db.execute(
            select(func.coalesce(func.sum(func.abs(BankTransaction.amount)), 0))
            .where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.is_reconciled == False,
            )
        )

        total_count = total.scalar() or 0
        reconciled_count = reconciled.scalar() or 0
        unreconciled_sum = unreconciled_amount.scalar() or Decimal("0.00")

        return {
            "total_transactions": total_count,
            "reconciled": reconciled_count,
            "unreconciled": total_count - reconciled_count,
            "unreconciled_amount": str(unreconciled_sum),
            "reconciliation_rate": round(
                reconciled_count / total_count * 100, 1
            ) if total_count > 0 else 0.0,
        }

    # ── Scoring ────────────────────────────────────────────

    def _score_match(self, txn: BankTransaction, entry: JournalEntry) -> tuple[float, str]:
        """
        Score how well a bank transaction matches a journal entry.

        Factors:
          - Amount match (0.0 - 0.5): exact match = 0.5, close = partial
          - Date proximity (0.0 - 0.3): same day = 0.3, within window = partial
          - Description overlap (0.0 - 0.2): token-level similarity
        """
        score = 0.0
        reasons = []

        # Amount matching (most important signal)
        txn_amount = abs(txn.amount)
        entry_total = self._entry_total(entry)

        if txn_amount == entry_total:
            score += 0.50
            reasons.append("exact amount match")
        elif entry_total > 0:
            diff_pct = abs(txn_amount - entry_total) / entry_total
            if diff_pct <= 0.01:  # Within 1%
                score += 0.40
                reasons.append("amount within 1%")
            elif diff_pct <= 0.05:  # Within 5%
                score += 0.20
                reasons.append("amount within 5%")

        # Date proximity
        date_diff = abs((txn.transaction_date - entry.entry_date).days)
        if date_diff == 0:
            score += 0.30
            reasons.append("same date")
        elif date_diff <= 1:
            score += 0.25
            reasons.append("1 day apart")
        elif date_diff <= self.date_window.days:
            proximity = 1.0 - (date_diff / self.date_window.days)
            score += 0.15 * proximity
            reasons.append(f"{date_diff} days apart")
        else:
            return 0.0, "outside date window"

        # Description similarity (simple token overlap)
        txn_desc = (txn.description_cleaned or txn.description_raw or "").lower()
        entry_desc = (entry.description or "").lower()

        txn_tokens = set(txn_desc.split())
        entry_tokens = set(entry_desc.split())

        if txn_tokens and entry_tokens:
            overlap = txn_tokens & entry_tokens
            # Remove common words
            noise = {"the", "a", "an", "of", "to", "for", "in", "on", "at", "and", "or"}
            overlap -= noise
            if overlap:
                similarity = len(overlap) / max(len(txn_tokens - noise), len(entry_tokens - noise), 1)
                score += 0.20 * min(similarity, 1.0)
                reasons.append(f"description overlap: {', '.join(list(overlap)[:3])}")

        return score, "; ".join(reasons) if reasons else "weak match"

    @staticmethod
    def _entry_total(entry: JournalEntry) -> Decimal:
        """Get the total debit amount of a journal entry."""
        if not entry.line_items:
            return Decimal("0.00")
        return sum(li.debit_amount for li in entry.line_items)
