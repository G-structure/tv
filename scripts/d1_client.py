"""Cloudflare D1 HTTP client — drop-in replacement for sqlite3.Connection.

Provides a sqlite3-compatible interface that talks to D1 via the REST API.
Used by the football scrapers and translator to write directly to D1
without local SQLite.

Requires env vars:
    CLOUDFLARE_ACCOUNT_ID
    CLOUDFLARE_API_TOKEN

Usage:
    from d1_client import get_d1
    conn = get_d1()
    conn.execute("INSERT INTO articles (...) VALUES (?)", (val,))
    rows = conn.execute("SELECT * FROM articles WHERE id = ?", (id,)).fetchall()
"""

import os
import sys
from dataclasses import dataclass, field

import httpx

D1_DATABASE_ID = "7087ac6b-6417-48a4-9c7f-1d108057cd51"


@dataclass
class D1Row:
    """Dict-like row that supports both index and key access."""
    _data: dict = field(repr=False)
    _keys: list = field(repr=False)

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._data.values())[key]
        return self._data[key]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(name)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        return self._data.get(key, default)


class D1Result:
    """Result from a D1 query, mimics sqlite3.Cursor."""

    def __init__(self, results: list[dict] | None = None):
        self._results = results or []
        self._rows = [D1Row(_data=r, _keys=list(r.keys())) for r in self._results]

    def fetchall(self) -> list[D1Row]:
        return self._rows

    def fetchone(self) -> D1Row | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)

    def __len__(self):
        return len(self._rows)


class D1Connection:
    """sqlite3.Connection-compatible wrapper around D1 REST API."""

    def __init__(self, account_id: str, api_token: str, database_id: str = D1_DATABASE_ID):
        self.account_id = account_id
        self.api_token = api_token
        self.database_id = database_id
        self.base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
            f"/d1/database/{database_id}/query"
        )
        self.row_factory = None  # compatibility with sqlite3
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def execute(self, sql: str, params: tuple | list | None = None) -> D1Result:
        """Execute a single SQL statement against D1."""
        body: dict = {"sql": sql}
        if params:
            body["params"] = list(params)

        resp = self._client.post(self.base_url, json=body)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            errors = data.get("errors", [])
            msg = errors[0].get("message", "Unknown D1 error") if errors else "Unknown D1 error"
            raise RuntimeError(f"D1 query failed: {msg}\nSQL: {sql[:200]}")

        results = data.get("result", [])
        if results and "results" in results[0]:
            return D1Result(results[0]["results"])
        return D1Result()

    def executescript(self, sql: str) -> None:
        """Execute multiple SQL statements (semicolon-separated)."""
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        for stmt in statements:
            self.execute(stmt)

    def commit(self) -> None:
        """No-op — D1 auto-commits."""
        pass

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def get_d1() -> D1Connection:
    """Create a D1Connection from environment variables."""
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")

    if not account_id or not api_token:
        print(
            "Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN env vars.\n"
            "Set them or use local SQLite mode.",
            file=sys.stderr,
        )
        sys.exit(1)

    return D1Connection(account_id, api_token)
