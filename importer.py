"""
Bank Transaction Import Service

Handles CSV and XLSX bank statement imports:
- Parses various bank export formats
- Deduplicates via SHA-256 hashing
- Stages transactions for AI classification
- Creates journal entries from classified transactions
"""

import hashlib
import io
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.models import BankTransaction, TransactionSource
from openledger.schemas import BankImportResponse


# ── Column Mapping Profiles ─────────────────────────────────
# Different banks export different column names. We normalize them.

COLUMN_MAPS = {
    "default": {
        "date": ["date", "transaction date", "trans date", "posting date", "post date"],
        "description": ["description", "memo", "narrative", "details", "transaction description", "payee"],
        "amount": ["amount", "transaction amount"],
        "debit": ["debit", "withdrawal", "withdrawals"],
        "credit": ["credit", "deposit", "deposits"],
        "balance": ["balance", "running balance", "available balance"],
        "reference": ["reference", "ref", "check number", "reference number"],
        "category": ["category", "type", "transaction type"],
    }
}


class ImportError(Exception):
    pass


class TransactionImporter:
    """Import bank transactions from CSV/XLSX files."""

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id

    async def import_file(
        self,
        file_content: bytes,
        filename: str,
        bank_account_id: Optional[uuid.UUID] = None,
    ) -> BankImportResponse:
        """
        Import a CSV or XLSX bank statement file.
        
        Returns a summary of imported, skipped (duplicate), and errored rows.
        """
        batch_id = uuid.uuid4()

        # Parse based on file type
        if filename.lower().endswith(".csv"):
            df = self._parse_csv(file_content)
            source = TransactionSource.BANK_IMPORT_CSV
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = self._parse_xlsx(file_content)
            source = TransactionSource.BANK_IMPORT_XLSX
        else:
            raise ImportError(f"Unsupported file type: {filename}")

        # Normalize columns
        df = self._normalize_columns(df)

        imported = 0
        duplicates = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                txn = self._row_to_transaction(row, batch_id, source)

                # Check for duplicates via hash
                is_dup = await self._check_duplicate(txn.transaction_hash)
                if is_dup:
                    duplicates += 1
                    continue

                self.db.add(txn)
                imported += 1

            except Exception as e:
                errors.append(f"Row {idx + 1}: {str(e)}")

        return BankImportResponse(
            batch_id=batch_id,
            total_rows=len(df),
            imported=imported,
            duplicates_skipped=duplicates,
            errors=errors,
        )

    # ── Parsing ─────────────────────────────────────────────

    def _parse_csv(self, content: bytes) -> pd.DataFrame:
        """Parse CSV with encoding detection."""
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(io.BytesIO(content), encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ImportError("Could not decode CSV file with any supported encoding")

    def _parse_xlsx(self, content: bytes) -> pd.DataFrame:
        """Parse XLSX file."""
        try:
            return pd.read_excel(io.BytesIO(content), engine="openpyxl")
        except Exception as e:
            raise ImportError(f"Could not parse XLSX file: {e}")

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Map bank-specific column names to our standard schema.
        Uses fuzzy matching against known column name patterns.
        """
        col_map = COLUMN_MAPS["default"]
        normalized = {}

        # Lowercase all column names for matching
        df.columns = [str(c).strip().lower() for c in df.columns]

        for standard_name, variants in col_map.items():
            for variant in variants:
                if variant in df.columns:
                    normalized[variant] = standard_name
                    break

        df = df.rename(columns=normalized)

        # Handle split debit/credit columns → single amount
        if "amount" not in df.columns and "debit" in df.columns and "credit" in df.columns:
            df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
            df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)
            df["amount"] = df["credit"] - df["debit"]

        # Validate required columns exist
        required = ["date", "description", "amount"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ImportError(
                f"Missing required columns: {missing}. "
                f"Found columns: {list(df.columns)}"
            )

        return df

    def _row_to_transaction(
        self, row: pd.Series, batch_id: uuid.UUID, source: TransactionSource
    ) -> BankTransaction:
        """Convert a normalized DataFrame row to a BankTransaction model."""
        # Parse date
        txn_date = pd.to_datetime(row["date"]).date()

        # Parse amount
        amount_raw = str(row["amount"]).replace(",", "").replace("$", "").strip()
        try:
            amount = Decimal(amount_raw)
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid amount: {row['amount']}")

        description = str(row.get("description", "")).strip()
        if not description:
            raise ValueError("Empty description")

        # Generate dedup hash
        hash_input = f"{txn_date}|{amount}|{description}"
        txn_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return BankTransaction(
            organization_id=self.org_id,
            import_batch_id=batch_id,
            source=source,
            transaction_date=txn_date,
            post_date=pd.to_datetime(row.get("post_date")).date() if pd.notna(row.get("post_date")) else None,
            description_raw=description,
            amount=amount,
            balance=Decimal(str(row["balance"])) if pd.notna(row.get("balance")) else None,
            reference_number=str(row.get("reference", "")).strip() or None,
            category_raw=str(row.get("category", "")).strip() or None,
            transaction_hash=txn_hash,
        )

    async def _check_duplicate(self, txn_hash: str) -> bool:
        """Check if a transaction with this hash already exists."""
        result = await self.db.execute(
            select(BankTransaction.id).where(
                BankTransaction.organization_id == self.org_id,
                BankTransaction.transaction_hash == txn_hash,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
