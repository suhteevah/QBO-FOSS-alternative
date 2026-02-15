"""
AI Service — Claude Sonnet Integration

Three core capabilities:
1. Transaction Classification — auto-categorize bank transactions to chart of accounts
2. Natural Language Queries — convert "What did I spend on supplies?" to ledger queries
3. Query Tokenization — hash and cache queries for cost management and dedup

All API calls are logged to ai_query_log for cost tracking and audit.
"""

import hashlib
import json
import re
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

import anthropic
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from openledger.config import settings
from openledger.models import (
    Account, AccountType, BankTransaction, AIQueryLog,
)


class AIService:
    """Claude Sonnet-powered accounting intelligence."""

    def __init__(self, db: AsyncSession, organization_id: uuid.UUID):
        self.db = db
        self.org_id = organization_id
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.sonnet_model

    # ── Transaction Classification ──────────────────────────

    async def classify_transaction(
        self,
        description: str,
        amount: Decimal,
        existing_categories: Optional[list[dict]] = None,
    ) -> dict:
        """
        Use Sonnet to classify a bank transaction into the chart of accounts.
        
        Returns:
            {
                "account_id": UUID,
                "account_name": str,
                "confidence": float,
                "reasoning": str,
                "cleaned_description": str,
            }
        """
        # Fetch chart of accounts for context
        if not existing_categories:
            existing_categories = await self._get_account_list()

        accounts_context = "\n".join(
            f"- {a['number']} | {a['name']} ({a['type']})"
            for a in existing_categories
        )

        prompt = f"""You are an expert bookkeeper classifying bank transactions into a GAAP-compliant chart of accounts.

CHART OF ACCOUNTS:
{accounts_context}

TRANSACTION:
- Description: {description}
- Amount: ${amount}
- Type: {"Expense/Debit" if amount < 0 else "Income/Credit"}

Respond with ONLY valid JSON (no markdown, no explanation):
{{
    "account_number": "the best matching account number",
    "account_name": "the account name",
    "confidence": 0.0 to 1.0,
    "reasoning": "brief explanation of why this classification",
    "cleaned_description": "cleaned/normalized merchant/description"
}}

If unsure, set confidence below 0.5. Prefer specificity over generic categories."""

        start_time = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            latency_ms = (time.time() - start_time) * 1000
            response_text = response.content[0].text

            # Parse response
            result = json.loads(response_text)

            # Log the query
            token_hash = self._hash_query(f"classify:{description}:{amount}")
            await self._log_query(
                query_type="classify",
                query_text=f"{description} | ${amount}",
                token_hash=token_hash,
                response_text=response_text,
                response_structured=result,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
            )

            # Resolve account_number to account_id
            account = await self._find_account_by_number(result["account_number"])
            if account:
                result["account_id"] = str(account.id)

            return result

        except (json.JSONDecodeError, KeyError) as e:
            return {
                "account_number": None,
                "confidence": 0.0,
                "reasoning": f"AI classification failed: {e}",
                "cleaned_description": description,
            }

    async def classify_batch(
        self, transactions: list[BankTransaction]
    ) -> list[dict]:
        """
        Classify multiple transactions efficiently.
        Fetches chart of accounts once and reuses context.
        """
        accounts = await self._get_account_list()
        results = []
        for txn in transactions:
            result = await self.classify_transaction(
                description=txn.description_raw,
                amount=txn.amount,
                existing_categories=accounts,
            )
            results.append({"transaction_id": str(txn.id), **result})
        return results

    # ── Natural Language Query ──────────────────────────────

    async def natural_language_query(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Convert a natural language question into a ledger query.
        
        Examples:
            "What did I spend on supplies in Q3?" 
            → SELECT from journal entries where account=supplies, date in Q3
            
            "Show me all unreconciled transactions over $500"
            → SELECT from bank_transactions where is_reconciled=false, amount > 500
        """
        # Check cache first
        token_hash = self._hash_query(f"nl:{query}")
        cached = await self._check_cache(token_hash)
        if cached:
            return {
                "query": query,
                "interpreted_as": cached.get("interpreted_as", ""),
                "sql_generated": cached.get("sql_generated"),
                "results": cached.get("results", []),
                "token_hash": token_hash,
                "cached": True,
            }

        # Get schema context
        accounts = await self._get_account_list()
        accounts_context = "\n".join(
            f"- {a['number']} | {a['name']} ({a['type']})"
            for a in accounts
        )

        prompt = f"""You are a bookkeeping assistant converting natural language questions into SQL queries against an accounting database.

AVAILABLE TABLES:
- journal_entries (id, entry_date, description, status, source)
- journal_line_items (journal_entry_id, account_id, debit_amount, credit_amount)  
- accounts (id, account_number, name, account_type)
- bank_transactions (id, transaction_date, description_raw, amount, is_reconciled, ai_category)

CHART OF ACCOUNTS:
{accounts_context}

USER QUESTION: {query}

Current date context: {datetime.now().strftime("%Y-%m-%d")}

Respond with ONLY valid JSON:
{{
    "interpreted_as": "plain English restatement of what you understood",
    "sql_query": "SELECT query to answer the question (use PostgreSQL syntax)",
    "parameters": {{}},
    "explanation": "brief explanation of the query logic"
}}

RULES:
- Only generate SELECT queries (never INSERT/UPDATE/DELETE)
- Always filter by organization_id = :org_id
- Use proper JOIN syntax
- Handle date ranges intelligently (Q1 = Jan-Mar, etc.)
- If the question is ambiguous, interpret it most generously"""

        start_time = time.time()

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            latency_ms = (time.time() - start_time) * 1000
            response_text = response.content[0].text
            parsed = json.loads(response_text)

            # Safety check — only allow SELECT
            sql = parsed.get("sql_query", "")
            if not self._is_safe_sql(sql):
                return {
                    "query": query,
                    "interpreted_as": "Query rejected for safety",
                    "sql_generated": None,
                    "results": [],
                    "token_hash": token_hash,
                    "cached": False,
                }

            # Execute the query (read-only)
            try:
                result = await self.db.execute(
                    text(sql),
                    {"org_id": str(self.org_id), **parsed.get("parameters", {})},
                )
                rows = [dict(row._mapping) for row in result.fetchall()]
                # Convert non-serializable types
                for row in rows:
                    for k, v in row.items():
                        if isinstance(v, Decimal):
                            row[k] = float(v)
                        elif isinstance(v, (datetime,)):
                            row[k] = v.isoformat()
                        elif isinstance(v, uuid.UUID):
                            row[k] = str(v)
            except Exception as e:
                rows = [{"error": f"Query execution failed: {str(e)}"}]

            # Log
            await self._log_query(
                query_type="nl_query",
                query_text=query,
                token_hash=token_hash,
                response_text=response_text,
                response_structured={
                    "interpreted_as": parsed.get("interpreted_as"),
                    "sql_generated": sql,
                    "results": rows[:50],  # Cap stored results
                },
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=latency_ms,
                user_id=user_id,
            )

            return {
                "query": query,
                "interpreted_as": parsed.get("interpreted_as", ""),
                "sql_generated": sql,
                "results": rows,
                "token_hash": token_hash,
                "cached": False,
            }

        except Exception as e:
            return {
                "query": query,
                "interpreted_as": f"Error: {str(e)}",
                "sql_generated": None,
                "results": [],
                "token_hash": token_hash,
                "cached": False,
            }

    # ── Query Tokenization & Caching ────────────────────────

    def _hash_query(self, query: str) -> str:
        """
        Tokenize and hash a query for caching and dedup.
        
        Normalizes the query by:
        1. Lowercasing
        2. Stripping extra whitespace
        3. Removing filler words
        4. Sorting remaining tokens
        
        This means "What did I spend on supplies?" and 
        "how much was spent on supplies" produce the same hash.
        """
        # Normalize
        normalized = query.lower().strip()
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation

        # Remove filler/stop words
        stop_words = {
            "what", "how", "much", "did", "i", "we", "the", "a", "an",
            "is", "was", "were", "are", "do", "does", "show", "me",
            "my", "our", "please", "can", "you", "tell", "get", "find",
            "list", "all", "total", "give",
        }
        tokens = [t for t in normalized.split() if t not in stop_words]
        tokens.sort()

        canonical = " ".join(tokens)
        return hashlib.sha256(canonical.encode()).hexdigest()

    async def _check_cache(self, token_hash: str) -> Optional[dict]:
        """Check if we have a recent cached result for this query hash."""
        result = await self.db.execute(
            select(AIQueryLog.response_structured)
            .where(
                AIQueryLog.organization_id == self.org_id,
                AIQueryLog.query_token_hash == token_hash,
                AIQueryLog.query_type == "nl_query",
            )
            .order_by(AIQueryLog.created_at.desc())
            .limit(1)
        )
        cached = result.scalar_one_or_none()
        return cached

    # ── Helpers ──────────────────────────────────────────────

    async def _get_account_list(self) -> list[dict]:
        """Fetch active chart of accounts for AI context."""
        result = await self.db.execute(
            select(Account)
            .where(
                Account.organization_id == self.org_id,
                Account.is_active == True,
            )
            .order_by(Account.account_number)
        )
        accounts = result.scalars().all()
        return [
            {
                "id": str(a.id),
                "number": a.account_number,
                "name": a.name,
                "type": a.account_type.value if a.account_type else "",
            }
            for a in accounts
        ]

    async def _find_account_by_number(self, account_number: str) -> Optional[Account]:
        """Look up an account by its number."""
        result = await self.db.execute(
            select(Account).where(
                Account.organization_id == self.org_id,
                Account.account_number == account_number,
            )
        )
        return result.scalar_one_or_none()

    def _is_safe_sql(self, sql: str) -> bool:
        """Validate that AI-generated SQL is read-only."""
        dangerous = ["insert", "update", "delete", "drop", "alter", "create", "truncate", "grant", "revoke"]
        sql_lower = sql.lower().strip()
        if not sql_lower.startswith("select"):
            return False
        for keyword in dangerous:
            if re.search(rf'\b{keyword}\b', sql_lower):
                return False
        return True

    async def _log_query(
        self,
        query_type: str,
        query_text: str,
        token_hash: str,
        response_text: str,
        response_structured: dict,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        user_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Log AI API call for cost tracking and audit."""
        # Estimate cost (Sonnet pricing as of 2025)
        cost = (input_tokens * 0.003 / 1000) + (output_tokens * 0.015 / 1000)

        log = AIQueryLog(
            organization_id=self.org_id,
            user_id=user_id,
            query_type=query_type,
            query_text=query_text,
            query_token_hash=token_hash,
            response_text=response_text,
            response_structured=response_structured,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=Decimal(str(round(cost, 6))),
            model_used=self.model,
            latency_ms=Decimal(str(round(latency_ms, 2))),
            cached_hit=False,
        )
        self.db.add(log)
