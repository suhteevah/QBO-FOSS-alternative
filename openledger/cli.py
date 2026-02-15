"""
OpenLedger CLI — Administrative tools.

Usage:
    python -m openledger.cli seed-accounts
    python -m openledger.cli create-org "My Company"
"""

import sys
import uuid
from openledger.models import Account, AccountType, AccountSubtype, Organization, Base
from openledger.database import sync_engine, SyncSessionLocal


# ── Standard GAAP Chart of Accounts Seed ────────────────────

SEED_ACCOUNTS = [
    # Assets (1000-1999)
    ("1000", "Cash", AccountType.ASSET, AccountSubtype.CASH, "debit"),
    ("1010", "Petty Cash", AccountType.ASSET, AccountSubtype.CASH, "debit"),
    ("1100", "Accounts Receivable", AccountType.ASSET, AccountSubtype.ACCOUNTS_RECEIVABLE, "debit"),
    ("1200", "Inventory", AccountType.ASSET, AccountSubtype.INVENTORY, "debit"),
    ("1300", "Prepaid Expenses", AccountType.ASSET, AccountSubtype.PREPAID, "debit"),
    ("1400", "Equipment", AccountType.ASSET, AccountSubtype.FIXED_ASSET, "debit"),
    ("1410", "Vehicles", AccountType.ASSET, AccountSubtype.FIXED_ASSET, "debit"),
    ("1420", "Furniture & Fixtures", AccountType.ASSET, AccountSubtype.FIXED_ASSET, "debit"),
    ("1500", "Accumulated Depreciation", AccountType.CONTRA_ASSET, None, "credit"),

    # Liabilities (2000-2999)
    ("2000", "Accounts Payable", AccountType.LIABILITY, AccountSubtype.ACCOUNTS_PAYABLE, "credit"),
    ("2100", "Credit Card Payable", AccountType.LIABILITY, AccountSubtype.CREDIT_CARD, "credit"),
    ("2200", "Accrued Liabilities", AccountType.LIABILITY, AccountSubtype.ACCRUED_LIABILITY, "credit"),
    ("2300", "Sales Tax Payable", AccountType.LIABILITY, AccountSubtype.OTHER_LIABILITY, "credit"),
    ("2400", "Payroll Liabilities", AccountType.LIABILITY, AccountSubtype.OTHER_LIABILITY, "credit"),
    ("2500", "Notes Payable (Short-Term)", AccountType.LIABILITY, AccountSubtype.OTHER_LIABILITY, "credit"),
    ("2600", "Long-Term Debt", AccountType.LIABILITY, AccountSubtype.LONG_TERM_DEBT, "credit"),

    # Equity (3000-3999)
    ("3000", "Owner's Equity", AccountType.EQUITY, AccountSubtype.OWNERS_EQUITY, "credit"),
    ("3100", "Owner's Draws", AccountType.EQUITY, AccountSubtype.OWNERS_EQUITY, "debit"),
    ("3200", "Retained Earnings", AccountType.EQUITY, AccountSubtype.RETAINED_EARNINGS, "credit"),

    # Revenue (4000-4999)
    ("4000", "Sales Revenue", AccountType.REVENUE, AccountSubtype.SALES, "credit"),
    ("4100", "Service Revenue", AccountType.REVENUE, AccountSubtype.SERVICE_REVENUE, "credit"),
    ("4200", "Interest Income", AccountType.REVENUE, AccountSubtype.OTHER_INCOME, "credit"),
    ("4300", "Other Income", AccountType.REVENUE, AccountSubtype.OTHER_INCOME, "credit"),
    ("4900", "Sales Returns & Allowances", AccountType.CONTRA_REVENUE, None, "debit"),

    # Cost of Goods Sold (5000-5999)
    ("5000", "Cost of Goods Sold", AccountType.EXPENSE, AccountSubtype.COST_OF_GOODS, "debit"),
    ("5100", "Freight & Shipping", AccountType.EXPENSE, AccountSubtype.COST_OF_GOODS, "debit"),

    # Operating Expenses (6000-6999)
    ("6000", "Advertising & Marketing", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6100", "Bank Fees & Charges", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6200", "Insurance", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6300", "Office Supplies", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6400", "Rent Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6500", "Utilities", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6600", "Telephone & Internet", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6700", "Travel & Entertainment", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6800", "Professional Services", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("6900", "Repairs & Maintenance", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),

    # Payroll (7000-7999)
    ("7000", "Wages & Salaries", AccountType.EXPENSE, AccountSubtype.PAYROLL, "debit"),
    ("7100", "Payroll Taxes", AccountType.EXPENSE, AccountSubtype.PAYROLL, "debit"),
    ("7200", "Employee Benefits", AccountType.EXPENSE, AccountSubtype.PAYROLL, "debit"),
    ("7300", "Contractor Payments", AccountType.EXPENSE, AccountSubtype.PAYROLL, "debit"),

    # Other Expenses (8000-8999)
    ("8000", "Depreciation Expense", AccountType.EXPENSE, AccountSubtype.DEPRECIATION, "debit"),
    ("8100", "Interest Expense", AccountType.EXPENSE, AccountSubtype.OTHER_EXPENSE, "debit"),
    ("8200", "Taxes (Income)", AccountType.EXPENSE, AccountSubtype.TAX_EXPENSE, "debit"),
    ("8300", "Miscellaneous Expense", AccountType.EXPENSE, AccountSubtype.OTHER_EXPENSE, "debit"),
    ("8400", "Software & Subscriptions", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("8500", "Meals & Entertainment", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
    ("8600", "Vehicle Expense", AccountType.EXPENSE, AccountSubtype.OPERATING_EXPENSE, "debit"),
]


def seed_accounts(org_id: uuid.UUID):
    """Populate the chart of accounts with GAAP-standard defaults."""
    session = SyncSessionLocal()
    try:
        for number, name, acct_type, subtype, normal_bal in SEED_ACCOUNTS:
            existing = session.query(Account).filter_by(
                organization_id=org_id, account_number=number
            ).first()
            if existing:
                continue

            account = Account(
                organization_id=org_id,
                account_number=number,
                name=name,
                account_type=acct_type,
                account_subtype=subtype,
                normal_balance=normal_bal,
                is_system=True,
            )
            session.add(account)

        session.commit()
        print(f"Seeded {len(SEED_ACCOUNTS)} accounts for org {org_id}")
    finally:
        session.close()


def create_org(name: str) -> uuid.UUID:
    """Create a new organization."""
    session = SyncSessionLocal()
    try:
        org = Organization(name=name)
        session.add(org)
        session.commit()
        print(f"Created organization: {org.name} ({org.id})")
        return org.id
    finally:
        session.close()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=sync_engine)
    print("Database tables created.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m openledger.cli <command>")
        print("Commands: init-db, create-org <name>, seed-accounts <org-id>")
        sys.exit(1)

    command = sys.argv[1]

    if command == "init-db":
        init_db()
    elif command == "create-org":
        name = sys.argv[2] if len(sys.argv) > 2 else "Default Organization"
        org_id = create_org(name)
        print(f"Now run: python -m openledger.cli seed-accounts {org_id}")
    elif command == "seed-accounts":
        if len(sys.argv) < 3:
            print("Usage: python -m openledger.cli seed-accounts <org-id>")
            sys.exit(1)
        seed_accounts(uuid.UUID(sys.argv[2]))
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
