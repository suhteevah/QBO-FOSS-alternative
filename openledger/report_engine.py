"""
Financial Report Generation Engine

Generates GAAP-compliant financial statements:
- Profit & Loss (Income Statement)
- Balance Sheet (Statement of Financial Position)
- Trial Balance

All reports pull from approved/auto-approved journal entries only,
grouping by account type and subtype per GAAP presentation.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.models import (
    Account, AccountType, JournalEntry, JournalLineItem, EntryStatus,
)
from openledger.schemas import (
    ReportResponse, ReportSection, ReportLineItem,
)


APPROVED_STATUSES = [EntryStatus.APPROVED, EntryStatus.AUTO_APPROVED]


class ReportEngine:
    """Generates financial reports from the general ledger."""

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id

    # ── Profit & Loss ──────────────────────────────────────

    async def profit_and_loss(
        self,
        start_date: date,
        end_date: date,
        accounting_basis: str = "accrual",
    ) -> ReportResponse:
        """
        Generate a Profit & Loss (Income Statement) for the period.

        Structure:
          Revenue
            - Sales Revenue, Service Revenue, etc.
          Less: Cost of Goods Sold
          = Gross Profit
          Operating Expenses
            - Advertising, Rent, Utilities, etc.
          = Operating Income
          Other Income / (Expenses)
          = Net Income
        """
        balances = await self._get_period_balances(start_date, end_date)

        # Partition accounts into P&L categories
        revenue_items = []
        contra_revenue_items = []
        cogs_items = []
        opex_items = []
        other_expense_items = []

        for row in balances:
            acct_type = row.account_type
            amount = self._compute_balance(row)
            if amount == Decimal("0.00"):
                continue

            item = ReportLineItem(
                account_number=row.account_number,
                account_name=row.name,
                amount=amount,
            )

            if acct_type in (AccountType.REVENUE,):
                revenue_items.append(item)
            elif acct_type == AccountType.CONTRA_REVENUE:
                contra_revenue_items.append(item)
            elif acct_type == AccountType.EXPENSE:
                subtype = row.account_subtype
                if subtype and subtype.value == "cost_of_goods":
                    cogs_items.append(item)
                elif subtype and subtype.value in ("other_expense", "tax_expense"):
                    other_expense_items.append(item)
                else:
                    opex_items.append(item)

        revenue_total = sum(i.amount for i in revenue_items)
        contra_rev_total = sum(i.amount for i in contra_revenue_items)
        net_revenue = revenue_total - contra_rev_total
        cogs_total = sum(i.amount for i in cogs_items)
        gross_profit = net_revenue - cogs_total
        opex_total = sum(i.amount for i in opex_items)
        operating_income = gross_profit - opex_total
        other_total = sum(i.amount for i in other_expense_items)
        net_income = operating_income - other_total

        sections = []

        if revenue_items or contra_revenue_items:
            all_rev = revenue_items + [
                ReportLineItem(
                    account_number=i.account_number,
                    account_name=f"Less: {i.account_name}",
                    amount=-i.amount,
                )
                for i in contra_revenue_items
            ]
            sections.append(ReportSection(
                title="Revenue",
                items=all_rev,
                subtotal=net_revenue,
            ))

        if cogs_items:
            sections.append(ReportSection(
                title="Cost of Goods Sold",
                items=cogs_items,
                subtotal=cogs_total,
            ))

        sections.append(ReportSection(
            title="Gross Profit",
            items=[],
            subtotal=gross_profit,
        ))

        if opex_items:
            sections.append(ReportSection(
                title="Operating Expenses",
                items=opex_items,
                subtotal=opex_total,
            ))

        sections.append(ReportSection(
            title="Operating Income",
            items=[],
            subtotal=operating_income,
        ))

        if other_expense_items:
            sections.append(ReportSection(
                title="Other Expenses",
                items=other_expense_items,
                subtotal=other_total,
            ))

        return ReportResponse(
            report_type="profit_loss",
            period=f"{start_date} to {end_date}",
            generated_at=datetime.utcnow(),
            accounting_basis=accounting_basis,
            sections=sections,
            net_total=net_income,
        )

    # ── Balance Sheet ──────────────────────────────────────

    async def balance_sheet(
        self,
        as_of: date,
        accounting_basis: str = "accrual",
    ) -> ReportResponse:
        """
        Generate a Balance Sheet as of a specific date.

        Structure:
          Assets
            Current Assets (cash, AR, inventory, prepaid)
            Fixed Assets
            Less: Accumulated Depreciation
          = Total Assets

          Liabilities
            Current Liabilities (AP, credit card, accrued)
            Long-Term Liabilities
          = Total Liabilities

          Equity
            Owner's Equity
            Retained Earnings
            Net Income (current period)
          = Total Equity

          Total Liabilities + Equity (must == Total Assets)
        """
        balances = await self._get_cumulative_balances(as_of)

        # Also compute net income for retained earnings
        # Net income = Revenue - Expenses for all time up to as_of
        # (In a real system, this would use the fiscal year start)
        net_income = Decimal("0.00")

        current_asset_items = []
        fixed_asset_items = []
        contra_asset_items = []
        current_liability_items = []
        long_term_liability_items = []
        equity_items = []

        for row in balances:
            acct_type = row.account_type
            amount = self._compute_balance(row)
            if amount == Decimal("0.00"):
                continue

            item = ReportLineItem(
                account_number=row.account_number,
                account_name=row.name,
                amount=amount,
            )

            if acct_type == AccountType.ASSET:
                subtype = row.account_subtype
                if subtype and subtype.value == "fixed_asset":
                    fixed_asset_items.append(item)
                else:
                    current_asset_items.append(item)
            elif acct_type == AccountType.CONTRA_ASSET:
                contra_asset_items.append(item)
            elif acct_type == AccountType.LIABILITY:
                subtype = row.account_subtype
                if subtype and subtype.value == "long_term_debt":
                    long_term_liability_items.append(item)
                else:
                    current_liability_items.append(item)
            elif acct_type in (AccountType.EQUITY, AccountType.CONTRA_EQUITY):
                equity_items.append(item)
            elif acct_type in (AccountType.REVENUE, AccountType.CONTRA_REVENUE):
                if acct_type == AccountType.REVENUE:
                    net_income += amount
                else:
                    net_income -= amount
            elif acct_type == AccountType.EXPENSE:
                net_income -= amount

        # Build sections
        sections = []

        # Assets
        all_asset_items = current_asset_items + fixed_asset_items + [
            ReportLineItem(
                account_number=i.account_number,
                account_name=i.account_name,
                amount=-i.amount,  # Contra assets reduce total
            )
            for i in contra_asset_items
        ]
        total_assets = (
            sum(i.amount for i in current_asset_items)
            + sum(i.amount for i in fixed_asset_items)
            - sum(i.amount for i in contra_asset_items)
        )
        sections.append(ReportSection(
            title="Assets",
            items=all_asset_items,
            subtotal=total_assets,
        ))

        # Liabilities
        all_liability_items = current_liability_items + long_term_liability_items
        total_liabilities = sum(i.amount for i in all_liability_items)
        sections.append(ReportSection(
            title="Liabilities",
            items=all_liability_items,
            subtotal=total_liabilities,
        ))

        # Equity (including net income as current-period retained earnings)
        if net_income != Decimal("0.00"):
            equity_items.append(ReportLineItem(
                account_number="—",
                account_name="Net Income (Current Period)",
                amount=net_income,
            ))
        total_equity = sum(i.amount for i in equity_items)
        sections.append(ReportSection(
            title="Equity",
            items=equity_items,
            subtotal=total_equity,
        ))

        return ReportResponse(
            report_type="balance_sheet",
            period=f"As of {as_of}",
            generated_at=datetime.utcnow(),
            accounting_basis=accounting_basis,
            sections=sections,
            net_total=total_liabilities + total_equity,  # Should equal total_assets
        )

    # ── Trial Balance ──────────────────────────────────────

    async def trial_balance(
        self,
        as_of: Optional[date] = None,
    ) -> ReportResponse:
        """
        Generate a trial balance — all accounts with debit/credit totals.
        """
        balances = await self._get_cumulative_balances(as_of)

        debit_items = []
        credit_items = []

        for row in balances:
            amount = self._compute_balance(row)
            if amount == Decimal("0.00"):
                continue

            item = ReportLineItem(
                account_number=row.account_number,
                account_name=row.name,
                amount=abs(amount),
            )

            if row.normal_balance == "debit":
                debit_items.append(item)
            else:
                credit_items.append(item)

        sections = [
            ReportSection(
                title="Debit Balances",
                items=debit_items,
                subtotal=sum(i.amount for i in debit_items),
            ),
            ReportSection(
                title="Credit Balances",
                items=credit_items,
                subtotal=sum(i.amount for i in credit_items),
            ),
        ]

        return ReportResponse(
            report_type="trial_balance",
            period=f"As of {as_of or 'current'}",
            generated_at=datetime.utcnow(),
            accounting_basis="accrual",
            sections=sections,
            net_total=sum(i.amount for i in debit_items) - sum(i.amount for i in credit_items),
        )

    # ── Internal Queries ───────────────────────────────────

    async def _get_period_balances(self, start_date: date, end_date: date):
        """Get account balances for a specific period (P&L use)."""
        query = (
            select(
                Account.account_number,
                Account.name,
                Account.account_type,
                Account.account_subtype,
                Account.normal_balance,
                func.coalesce(func.sum(JournalLineItem.debit_amount), 0).label("total_debits"),
                func.coalesce(func.sum(JournalLineItem.credit_amount), 0).label("total_credits"),
            )
            .outerjoin(JournalLineItem, Account.id == JournalLineItem.account_id)
            .outerjoin(JournalEntry, and_(
                JournalLineItem.journal_entry_id == JournalEntry.id,
                JournalEntry.entry_date >= start_date,
                JournalEntry.entry_date <= end_date,
                JournalEntry.status.in_(APPROVED_STATUSES),
                JournalEntry.organization_id == self.org_id,
            ))
            .where(
                Account.organization_id == self.org_id,
                Account.is_active == True,
                Account.account_type.in_([
                    AccountType.REVENUE, AccountType.EXPENSE,
                    AccountType.CONTRA_REVENUE, AccountType.CONTRA_EXPENSE,
                ]),
            )
            .group_by(
                Account.account_number, Account.name,
                Account.account_type, Account.account_subtype,
                Account.normal_balance,
            )
            .order_by(Account.account_number)
        )
        result = await self.db.execute(query)
        return result.all()

    async def _get_cumulative_balances(self, as_of: Optional[date] = None):
        """Get cumulative account balances up to a date (balance sheet use)."""
        join_conditions = [
            JournalLineItem.journal_entry_id == JournalEntry.id,
            JournalEntry.status.in_(APPROVED_STATUSES),
            JournalEntry.organization_id == self.org_id,
        ]
        if as_of:
            join_conditions.append(JournalEntry.entry_date <= as_of)

        query = (
            select(
                Account.account_number,
                Account.name,
                Account.account_type,
                Account.account_subtype,
                Account.normal_balance,
                func.coalesce(func.sum(JournalLineItem.debit_amount), 0).label("total_debits"),
                func.coalesce(func.sum(JournalLineItem.credit_amount), 0).label("total_credits"),
            )
            .outerjoin(JournalLineItem, Account.id == JournalLineItem.account_id)
            .outerjoin(JournalEntry, and_(*join_conditions))
            .where(
                Account.organization_id == self.org_id,
                Account.is_active == True,
            )
            .group_by(
                Account.account_number, Account.name,
                Account.account_type, Account.account_subtype,
                Account.normal_balance,
            )
            .order_by(Account.account_number)
        )
        result = await self.db.execute(query)
        return result.all()

    @staticmethod
    def _compute_balance(row) -> Decimal:
        """Compute net balance based on normal balance side."""
        debits = Decimal(str(row.total_debits))
        credits = Decimal(str(row.total_credits))
        if row.normal_balance == "debit":
            return debits - credits
        else:
            return credits - debits
