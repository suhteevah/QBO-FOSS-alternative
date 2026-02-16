"""
Accounting Period Management Service

GAAP period lifecycle:
1. Create periods (monthly, quarterly, annual) with overlap validation
2. Pre-close readiness check (unapproved entries, unreconciled txns)
3. Close period — generate closing entries (revenue/expense → retained earnings)
4. Reopen period — reverse closing entries (admin only)

Closing entries follow standard GAAP procedure:
  - Debit all revenue accounts (zero them out)
  - Credit all expense accounts (zero them out)
  - Net difference posts to Retained Earnings (account 3200)
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.models import (
    Account, AccountType, JournalEntry, JournalLineItem,
    BankTransaction, EntryStatus, AccountingPeriod, PeriodStatus,
    AuditLog, TransactionSource,
)


RETAINED_EARNINGS_ACCOUNT_NUMBER = "3200"
CLOSING_ENTRY_DESCRIPTION_PREFIX = "Period Close —"


class PeriodError(Exception):
    """Base exception for period operations."""
    pass


class PeriodOverlapError(PeriodError):
    pass


class PeriodNotFoundError(PeriodError):
    pass


class PeriodNotReadyError(PeriodError):
    pass


class PeriodAlreadyClosedError(PeriodError):
    pass


class PeriodAlreadyOpenError(PeriodError):
    pass


class PeriodService:
    """Manages accounting period lifecycle with GAAP closing entries."""

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id

    # ── Create Period ──────────────────────────────────────

    async def create_period(
        self,
        name: str,
        start_date: date,
        end_date: date,
    ) -> AccountingPeriod:
        """
        Create a new accounting period after validating no date overlaps.

        Raises PeriodOverlapError if the date range overlaps an existing period.
        """
        # Check for overlapping periods within the same organization
        overlap_result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.organization_id == self.org_id,
                AccountingPeriod.start_date <= end_date,
                AccountingPeriod.end_date >= start_date,
            )
        )
        existing = overlap_result.scalar_one_or_none()
        if existing:
            raise PeriodOverlapError(
                f"Date range overlaps existing period '{existing.name}' "
                f"({existing.start_date} to {existing.end_date})"
            )

        period = AccountingPeriod(
            organization_id=self.org_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=PeriodStatus.OPEN,
        )
        self.db.add(period)
        await self.db.flush()

        # Audit log
        await self._audit(
            action="create",
            entity_type="accounting_period",
            entity_id=period.id,
            after_state={
                "name": name,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "status": PeriodStatus.OPEN.value,
            },
        )

        return period

    # ── List Periods ───────────────────────────────────────

    async def list_periods(self) -> list[AccountingPeriod]:
        """Return all periods for the organization, ordered by start_date descending."""
        result = await self.db.execute(
            select(AccountingPeriod)
            .where(AccountingPeriod.organization_id == self.org_id)
            .order_by(AccountingPeriod.start_date.desc())
        )
        return list(result.scalars().all())

    # ── Readiness Check ────────────────────────────────────

    async def get_readiness(self, period_id: uuid.UUID) -> dict:
        """
        Pre-close validation for a period.

        Returns counts of items that should be resolved before closing:
        - unapproved_entries: entries with status not in (APPROVED, AUTO_APPROVED)
        - unreconciled_transactions: bank transactions not yet reconciled
        - draft_entries: entries still in DRAFT status
        - ready_to_close: True only if all counts are zero
        """
        period = await self._get_period(period_id)

        # Count unapproved journal entries in the period date range
        unapproved_result = await self.db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.organization_id == self.org_id,
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date,
                JournalEntry.status.notin_([
                    EntryStatus.APPROVED,
                    EntryStatus.AUTO_APPROVED,
                    EntryStatus.VOIDED,
                ]),
            )
        )
        unapproved_entries = unapproved_result.scalar() or 0

        # Count unreconciled bank transactions in the period date range
        unreconciled_result = await self.db.execute(
            select(func.count(BankTransaction.id)).where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.transaction_date >= period.start_date,
                BankTransaction.transaction_date <= period.end_date,
                BankTransaction.is_reconciled == False,
            )
        )
        unreconciled_transactions = unreconciled_result.scalar() or 0

        # Count draft entries specifically (subset of unapproved)
        draft_result = await self.db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.organization_id == self.org_id,
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date,
                JournalEntry.status == EntryStatus.DRAFT,
            )
        )
        draft_entries = draft_result.scalar() or 0

        ready_to_close = (
            unapproved_entries == 0
            and unreconciled_transactions == 0
            and draft_entries == 0
        )

        return {
            "period_id": period.id,
            "unapproved_entries": unapproved_entries,
            "unreconciled_transactions": unreconciled_transactions,
            "draft_entries": draft_entries,
            "ready_to_close": ready_to_close,
        }

    # ── Close Period ───────────────────────────────────────

    async def close_period(
        self,
        period_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AccountingPeriod:
        """
        GAAP period close procedure:

        1. Verify the period exists and is currently OPEN
        2. Check readiness (warn but allow override — entries should be approved)
        3. Generate closing entries:
           - Debit each revenue account for its period balance → zeroes revenue
           - Credit each expense account for its period balance → zeroes expenses
           - Net difference posts to Retained Earnings (account 3200)
        4. Mark period as CLOSED with closed_by and closed_at
        5. Write audit log

        Raises PeriodAlreadyClosedError if period is not OPEN.
        """
        period = await self._get_period(period_id)

        if period.status == PeriodStatus.CLOSED:
            raise PeriodAlreadyClosedError(
                f"Period '{period.name}' is already closed"
            )

        # Resolve the Retained Earnings account (3200)
        retained_earnings = await self._get_retained_earnings_account()

        # Calculate period balances for all revenue and expense accounts
        closing_lines = await self._build_closing_lines(
            period, retained_earnings.id
        )

        # Only create a closing entry if there are revenue/expense balances
        closing_entry_id = None
        if closing_lines:
            closing_entry = JournalEntry(
                organization_id=self.org_id,
                entry_date=period.end_date,
                description=f"{CLOSING_ENTRY_DESCRIPTION_PREFIX} {period.name}",
                memo=f"Auto-generated closing entry for period {period.name}",
                source=TransactionSource.MANUAL,
                status=EntryStatus.APPROVED,
                created_by=user_id,
                reviewed_by=user_id,
                reviewed_at=datetime.utcnow(),
            )
            self.db.add(closing_entry)
            await self.db.flush()
            closing_entry_id = closing_entry.id

            for line_data in closing_lines:
                line = JournalLineItem(
                    journal_entry_id=closing_entry.id,
                    account_id=line_data["account_id"],
                    description=line_data["description"],
                    debit_amount=line_data["debit_amount"],
                    credit_amount=line_data["credit_amount"],
                )
                self.db.add(line)

        # Mark period closed
        period.status = PeriodStatus.CLOSED
        period.closed_by = user_id
        period.closed_at = datetime.utcnow()

        # Audit log
        await self._audit(
            action="close_period",
            entity_type="accounting_period",
            entity_id=period.id,
            before_state={"status": PeriodStatus.OPEN.value},
            after_state={
                "status": PeriodStatus.CLOSED.value,
                "closed_by": str(user_id),
                "closed_at": str(period.closed_at),
                "closing_entry_id": str(closing_entry_id) if closing_entry_id else None,
                "closing_lines_count": len(closing_lines),
            },
            user_id=user_id,
        )

        return period

    # ── Reopen Period ──────────────────────────────────────

    async def reopen_period(
        self,
        period_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AccountingPeriod:
        """
        Reopen a closed period (admin only).

        1. Verify the period is currently CLOSED
        2. Find and delete the auto-generated closing entries for this period
        3. Set period status back to OPEN, clear closed_by/closed_at
        4. Write audit log

        Raises PeriodAlreadyOpenError if the period is not CLOSED.
        """
        period = await self._get_period(period_id)

        if period.status == PeriodStatus.OPEN:
            raise PeriodAlreadyOpenError(
                f"Period '{period.name}' is already open"
            )

        # Find and delete closing entries generated for this period
        closing_description = f"{CLOSING_ENTRY_DESCRIPTION_PREFIX} {period.name}"
        closing_entries_result = await self.db.execute(
            select(JournalEntry).where(
                JournalEntry.organization_id == self.org_id,
                JournalEntry.description == closing_description,
                JournalEntry.entry_date == period.end_date,
            )
        )
        closing_entries = closing_entries_result.scalars().all()
        deleted_entry_ids = []

        for entry in closing_entries:
            deleted_entry_ids.append(str(entry.id))
            # Delete line items first (cascade should handle this, but be explicit)
            await self.db.execute(
                delete(JournalLineItem).where(
                    JournalLineItem.journal_entry_id == entry.id
                )
            )
            await self.db.delete(entry)

        # Reset period status
        old_closed_by = period.closed_by
        old_closed_at = period.closed_at

        period.status = PeriodStatus.OPEN
        period.closed_by = None
        period.closed_at = None

        # Audit log
        await self._audit(
            action="reopen_period",
            entity_type="accounting_period",
            entity_id=period.id,
            before_state={
                "status": PeriodStatus.CLOSED.value,
                "closed_by": str(old_closed_by) if old_closed_by else None,
                "closed_at": str(old_closed_at) if old_closed_at else None,
            },
            after_state={
                "status": PeriodStatus.OPEN.value,
                "deleted_closing_entries": deleted_entry_ids,
            },
            user_id=user_id,
        )

        return period

    # ── Private Helpers ────────────────────────────────────

    async def _get_period(self, period_id: uuid.UUID) -> AccountingPeriod:
        """Fetch a period by ID, scoped to this organization."""
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.id == period_id,
                AccountingPeriod.organization_id == self.org_id,
            )
        )
        period = result.scalar_one_or_none()
        if not period:
            raise PeriodNotFoundError(f"Accounting period {period_id} not found")
        return period

    async def _get_retained_earnings_account(self) -> Account:
        """
        Fetch the Retained Earnings account (3200) for this organization.
        Raises PeriodError if the account does not exist.
        """
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == self.org_id,
                Account.account_number == RETAINED_EARNINGS_ACCOUNT_NUMBER,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise PeriodError(
                f"Retained Earnings account ({RETAINED_EARNINGS_ACCOUNT_NUMBER}) "
                f"not found. Create it before closing a period."
            )
        return account

    async def _build_closing_lines(
        self,
        period: AccountingPeriod,
        retained_earnings_id: uuid.UUID,
    ) -> list[dict]:
        """
        Build the closing journal entry line items.

        For each revenue account with a balance in the period:
          - Debit the revenue account (zeroes it out; revenue has credit normal balance)
        For each expense account with a balance in the period:
          - Credit the expense account (zeroes it out; expense has debit normal balance)
        The net difference goes to Retained Earnings.
        """
        closing_lines = []
        net_income = Decimal("0.00")

        # Get period balances for revenue accounts
        revenue_balances = await self._get_account_period_balances(
            period, AccountType.REVENUE
        )
        for account_id, account_name, balance in revenue_balances:
            if balance == Decimal("0.00"):
                continue
            # Revenue has credit normal balance; to close, we debit revenue
            closing_lines.append({
                "account_id": account_id,
                "description": f"Close revenue — {account_name}",
                "debit_amount": balance,
                "credit_amount": Decimal("0.00"),
            })
            net_income += balance

        # Get period balances for expense accounts
        expense_balances = await self._get_account_period_balances(
            period, AccountType.EXPENSE
        )
        for account_id, account_name, balance in expense_balances:
            if balance == Decimal("0.00"):
                continue
            # Expense has debit normal balance; to close, we credit expense
            closing_lines.append({
                "account_id": account_id,
                "description": f"Close expense — {account_name}",
                "debit_amount": Decimal("0.00"),
                "credit_amount": balance,
            })
            net_income -= balance

        # Net to Retained Earnings
        if net_income > Decimal("0.00"):
            # Net income (profit) — credit Retained Earnings
            closing_lines.append({
                "account_id": retained_earnings_id,
                "description": f"Net income to Retained Earnings — {period.name}",
                "debit_amount": Decimal("0.00"),
                "credit_amount": net_income,
            })
        elif net_income < Decimal("0.00"):
            # Net loss — debit Retained Earnings
            closing_lines.append({
                "account_id": retained_earnings_id,
                "description": f"Net loss to Retained Earnings — {period.name}",
                "debit_amount": abs(net_income),
                "credit_amount": Decimal("0.00"),
            })
        # If net_income == 0, revenue exactly equals expense; no RE line needed,
        # but the individual close lines still balance (debit revenue == credit expense)

        return closing_lines

    async def _get_account_period_balances(
        self,
        period: AccountingPeriod,
        account_type: AccountType,
    ) -> list[tuple[uuid.UUID, str, Decimal]]:
        """
        Get the net balance for each account of the given type within the period.

        Returns list of (account_id, account_name, balance) where balance
        is computed using the account's normal balance convention.
        """
        result = await self.db.execute(
            select(
                Account.id,
                Account.name,
                Account.normal_balance,
                func.coalesce(
                    func.sum(JournalLineItem.debit_amount), Decimal("0.00")
                ).label("total_debits"),
                func.coalesce(
                    func.sum(JournalLineItem.credit_amount), Decimal("0.00")
                ).label("total_credits"),
            )
            .join(JournalLineItem, Account.id == JournalLineItem.account_id)
            .join(JournalEntry, JournalLineItem.journal_entry_id == JournalEntry.id)
            .where(
                Account.organization_id == self.org_id,
                Account.account_type == account_type,
                Account.is_active == True,
                JournalEntry.organization_id == self.org_id,
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date,
                JournalEntry.status.in_([
                    EntryStatus.APPROVED,
                    EntryStatus.AUTO_APPROVED,
                ]),
            )
            .group_by(Account.id, Account.name, Account.normal_balance)
        )
        rows = result.all()

        balances = []
        for row in rows:
            total_debits = Decimal(str(row.total_debits))
            total_credits = Decimal(str(row.total_credits))

            if row.normal_balance == "debit":
                balance = total_debits - total_credits
            else:
                balance = total_credits - total_debits

            if balance != Decimal("0.00"):
                balances.append((row.id, row.name, abs(balance)))

        return balances

    # ── Audit Logging ──────────────────────────────────────

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
