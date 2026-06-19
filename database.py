"""SQLite persistence for the Smart AR Voice Agent.

The database is intentionally small and local so the project can run on a
laptop, Docker container, or Hugging Face Space without an external service.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("AR_DB_PATH", Path(__file__).with_name("accounts_receivable.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    amount_due REAL NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OVERDUE',
    promise_date TEXT,
    last_updated TEXT NOT NULL
)
"""

MOCK_INVOICES = [
    {
        "invoice_id": "INV-2026-001",
        "customer_name": "Acme Corporation",
        "amount_due": 4500.50,
        "due_date": "June 1, 2026",
        "status": "OVERDUE",
    },
    {
        "invoice_id": "INV-2026-002",
        "customer_name": "Stark Industries",
        "amount_due": 12500.00,
        "due_date": "June 12, 2026",
        "status": "OVERDUE",
    },
    {
        "invoice_id": "INV-2026-003",
        "customer_name": "Wayne Enterprises",
        "amount_due": 980.00,
        "due_date": "July 5, 2026",
        "status": "PENDING",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with dictionary-like row access."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add missing columns for users who already created an older DB."""
    columns = _table_columns(conn, "invoices")
    migrations = {
        "promise_date": "ALTER TABLE invoices ADD COLUMN promise_date TEXT",
        "last_updated": "ALTER TABLE invoices ADD COLUMN last_updated TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            conn.execute(statement)

    conn.execute(
        "UPDATE invoices SET last_updated = ? WHERE last_updated IS NULL",
        (utc_now(),),
    )


def init_db(seed: bool = True) -> None:
    """Create/migrate the invoices table and optionally insert sample data."""
    with closing(get_connection()) as conn:
        conn.execute(SCHEMA)
        _migrate_schema(conn)
        if seed:
            for invoice in MOCK_INVOICES:
                upsert_invoice(invoice, connection=conn, overwrite=False)
        conn.commit()


def upsert_invoice(
    invoice: dict[str, Any],
    *,
    connection: sqlite3.Connection | None = None,
    overwrite: bool = True,
) -> None:
    """Insert or update an invoice extracted from OCR or test data.

    Args:
        invoice: Dict containing invoice_id, customer_name, amount_due, due_date,
            and optionally status/promise_date.
        connection: Optional existing connection used during migrations/seeding.
        overwrite: If False, existing invoices are preserved.
    """
    required = {"invoice_id", "customer_name", "amount_due", "due_date"}
    missing = required - set(invoice)
    if missing:
        raise ValueError(f"Missing invoice fields: {', '.join(sorted(missing))}")

    owns_connection = connection is None
    conn = connection or get_connection()
    try:
        sql = (
            """
            INSERT INTO invoices (
                invoice_id, customer_name, amount_due, due_date, status,
                promise_date, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(invoice_id) DO UPDATE SET
                customer_name = excluded.customer_name,
                amount_due = excluded.amount_due,
                due_date = excluded.due_date,
                status = excluded.status,
                promise_date = excluded.promise_date,
                last_updated = excluded.last_updated
            """
            if overwrite
            else """
            INSERT OR IGNORE INTO invoices (
                invoice_id, customer_name, amount_due, due_date, status,
                promise_date, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
        )
        conn.execute(
            sql,
            (
                str(invoice["invoice_id"]),
                str(invoice["customer_name"]),
                float(invoice["amount_due"]),
                str(invoice["due_date"]),
                str(invoice.get("status", "OVERDUE")),
                invoice.get("promise_date"),
                utc_now(),
            ),
        )
        if owns_connection:
            conn.commit()
    finally:
        if owns_connection:
            conn.close()


def get_invoice_details(invoice_id: str) -> dict[str, Any] | None:
    """Return invoice data as a plain dict, or None when not found."""
    init_db(seed=True)
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT invoice_id, customer_name, amount_due, due_date, status,
                   promise_date, last_updated
            FROM invoices
            WHERE invoice_id = ?
            """,
            (invoice_id,),
        ).fetchone()
    return dict(row) if row else None


def update_invoice_status(
    invoice_id: str,
    new_status: str,
    *,
    promise_date: str | None = None,
) -> bool:
    """Update invoice status and optionally record a promised payment date."""
    init_db(seed=True)
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            """
            UPDATE invoices
            SET status = ?, promise_date = COALESCE(?, promise_date), last_updated = ?
            WHERE invoice_id = ?
            """,
            (new_status, promise_date, utc_now(), invoice_id),
        )
        conn.commit()
        return cursor.rowcount > 0


if __name__ == "__main__":
    init_db(seed=True)
    print(f"Database ready at: {DB_PATH}")
    print(get_invoice_details("INV-2026-001"))
