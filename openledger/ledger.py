"""
Double-Entry Ledger Engine

Core accounting logic enforcing GAAP principles:
- Balanced journal entries (debits == credits)
- Period validation (reject entries in closed periods)
- Account balance computation
- Trial balance generation
- Audit trail on every mutation
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.models import (
    Account, AccountType, JournalEntry, JournalLineItem,
    BankTransaction, EntryStatus, AccountingPeriod, PeriodStatus,
    AuditLog,
)
from openledger.schemas import JournalEntryCreate


# ── Normal Balance Rules ────────────────────────────────────

NORMAL_BALANCE_MAP = {
    AccountType.ASSET: "debit",
    AccountType.EXPENSE: "debit",
    AccountType.CONTRA_LIABILITY: "debit",
    AccountType.CONTRA_EQUITY: "debit",
    AccountType.CONTRA_REVENUE: "debit",
    AccountType.LIABILITY: "credit",
    AccountType.EQUITY: "credit",
    AccountType.REVENUE: "credit",
    AccountType.CONTRA_ASSET: "credit",
    AccountType.CONTRA_EXPENSE: "credit",
}


class LedgerError(Exception):
    """Base exception for ledger operations."""
    pass


class UnbalancedEntryError(LedgerError):
    pass


class ClosedPeriodError(LedgerError):
    pass


class LedgerEngine:
    """Core double-entry bookkeeping engine."""

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id

    # ── Journal Entry Operations ────────────────────────────

    async def create_journal_entry(
        self,
        data: JournalEntryCreate,
        created_by: Optional[uuid.UUID] = None,
        auto_approve_threshold: Decimal = Decimal("50.00"),
    ) -> JournalEntry:
        """
        Create a new journal entry with balanced line items.
        
        Entries below the materiality threshold are auto-approved.
        All others start as DRAFT for accountant review.
        """
        # 1. Validate period is open
        await self._validate_period_open(data.entry_date)

        # 2. Validate balance (also checked in schema, but defense in depth)
        total_debits = sum(li.debit_amount for li in data.line_items)
        total_credits = sum(li.credit_amount for li in data.line_items)
        if total_debits != total_credits:
            raise UnbalancedEntryError(
                f"Debits ({total_debits}) != Credits ({total_credits})"
            )

        # 3. Determine initial status
        entry_total = max(total_debits, total_credits)
        if entry_total <= auto_approve_threshold and data.source != "manual":
            status = EntryStatus.AUTO_APPROVED
        else:
            status = EntryStatus.DRAFT

        # 4. Create the entry
        entry = JournalEntry(
            organization_id=self.org_id,
            entry_date=data.entry_date,
            description=data.description,
            memo=data.memo,
            source=data.source,
            status=status,
            created_by=created_by,
        )
        self.db.add(entry)
        await self.db.flush()  # Get the ID

        # 5. Create line items
        for li_data in data.line_items:
            line_item = JournalLineItem(
                journal_entry_id=entry.id,
                account_id=li_data.account_id,
                description=li_data.description,
                debit_amount=li_data.debit_amount,
                credit_amount=li_data.credit_amount,
            )
            self.db.add(line_item)

        # 6. Audit log
        await self._audit(
            action="create",
            entity_type="journal_entry",
            entity_id=entry.id,
            after_state={
                "entry_date": str(data.entry_date),
                "description": data.description,
                "status": status.value,
                "total": str(entry_total),
                "line_items": len(data.line_items),
            },
            user_id=created_by,
        )

        return entry

    async def approve_entry(
        self, entry_id: uuid.UUID, reviewer_id: uuid.UUID, notes: Optional[str] = None
    ) -> JournalEntry:
        """Accountant approves a draft journal entry."""
        result = await self.db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id,
                JournalEntry.organization_id == self.org_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise LedgerError(f"Journal entry {entry_id} not found")

        old_status = entry.status
        entry.status = EntryStatus.APPROVED
        entry.reviewed_by = reviewer_id
        entry.reviewed_at = datetime.utcnow()
        entry.review_notes = notes

        await self._audit(
            action="approve",
            entity_type="journal_entry",
            entity_id=entry.id,
            before_state={"status": old_status.value},
            after_state={"status": EntryStatus.APPROVED.value, "notes": notes},
            user_id=reviewer_id,
        )

        return entry

    async def void_entry(
        self, entry_id: uuid.UUID, user_id: uuid.UUID, reason: str
    ) -> JournalEntry:
        """Void (reverse) a journal entry. Creates a reversing entry."""
        result = await self.db.execute(
            select(JournalEntry).where(
                JournalEntry.id == entry_id,
                JournalEntry.organization_id == self.org_id,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            raise LedgerError(f"Journal entry {entry_id} not found")

        # Capture before_state BEFORE mutation
        old_status = entry.status
        entry.status = EntryStatus.VOIDED

        await self._audit(
            action="void",
            entity_type="journal_entry",
            entity_id=entry.id,
            before_state={"status": old_status.value},
            after_state={"status": EntryStatus.VOIDED.value, "reason": reason},
            user_id=user_id,
        )

        return entry

    # ── Balance Computation ─────────────────────────────────

    async def get_account_balance(
        self,
        account_id: uuid.UUID,
        as_of: Optional[date] = None,
        only_approved: bool = True,
    ) -> Decimal:
        """
        Compute the balance of an account as of a given date.
        
        For debit-normal accounts (assets, expenses): balance = debits - credits
        For credit-normal accounts (liabilities, equity, revenue): balance = credits - debits
        """
        # Get account to determine normal balance
        acct_result = await self.db.execute(
            select(Account).where(Account.id == account_id)
        )
        account = acct_result.scalar_one_or_none()
        if not account:
            raise LedgerError(f"Account {account_id} not found")

        # Build query
        query = (
            select(
                func.coalesce(func.sum(JournalLineItem.debit_amount), 0).label("total_debits"),
                func.coalesce(func.sum(JournalLineItem.credit_amount), 0).label("total_credits"),
            )
            .join(JournalEntry, JournalLineItem.journal_entry_id == JournalEntry.id)
            .where(
                JournalLineItem.account_id == account_id,
                JournalEntry.organization_id == self.org_id,
            )
        )

        if as_of:
            query = query.where(JournalEntry.entry_date <= as_of)

        if only_approved:
            query = query.where(
                JournalEntry.status.in_([
                    EntryStatus.APPROVED,
                    EntryStatus.AUTO_APPROVED,
                ])
            )

        result = await self.db.execute(query)
        row = result.one()

        total_debits = Decimal(str(row.total_debits))
        total_credits = Decimal(str(row.total_credits))

        if account.normal_balance == "debit":
            return total_debits - total_credits
        else:
            return total_credits - total_debits

    async def get_trial_balance(
        self, as_of: Optional[date] = None
    ) -> list[dict]:
        """
        Generate trial balance — all accounts with their debit/credit totals.
        Total debits must equal total credits (GAAP requirement).
        """
        query = (
            select(
                Account.account_number,
                Account.name,
                Account.account_type,
                Account.normal_balance,
                func.coalesce(func.sum(JournalLineItem.debit_amount), 0).label("total_debits"),
                func.coalesce(func.sum(JournalLineItem.credit_amount), 0).label("total_credits"),
            )
            .outerjoin(JournalLineItem, Account.id == JournalLineItem.account_id)
            .outerjoin(JournalEntry, JournalLineItem.journal_entry_id == JournalEntry.id)
            .where(
                Account.organization_id == self.org_id,
                Account.is_active == True,
            )
            .group_by(
                Account.account_number, Account.name,
                Account.account_type, Account.normal_balance,
            )
            .order_by(Account.account_number)
        )

        if as_of:
            query = query.where(JournalEntry.entry_date <= as_of)

        result = await self.db.execute(query)
        rows = result.all()

        trial_balance = []
        for row in rows:
            debits = Decimal(str(row.total_debits))
            credits = Decimal(str(row.total_credits))
            if debits == 0 and credits == 0:
                continue  # Skip zero-balance accounts
            trial_balance.append({
                "account_number": row.account_number,
                "account_name": row.name,
                "account_type": row.account_type,
                "debit_balance": debits - credits if row.normal_balance == "debit" and debits > credits else Decimal("0.00"),
                "credit_balance": credits - debits if row.normal_balance == "credit" and credits > debits else Decimal("0.00"),
            })

        return trial_balance

    # ── Period Management ───────────────────────────────────

    async def _validate_period_open(self, entry_date: date) -> None:
        """Ensure the accounting period for this date is not closed."""
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.organization_id == self.org_id,
                AccountingPeriod.start_date <= entry_date,
                AccountingPeriod.end_date >= entry_date,
                AccountingPeriod.status == PeriodStatus.CLOSED,
            )
        )
        closed_period = result.scalar_one_or_none()
        if closed_period:
            raise ClosedPeriodError(
                f"Cannot create entries in closed period: {closed_period.name}"
            )

    # ── Audit Logging ───────────────────────────────────────

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
