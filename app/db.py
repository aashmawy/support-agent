"""SQLite access for accounts, subscriptions, invoices, tickets, audit log."""
import os
import sqlite3
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def get_connection(db_path: str | None = None):
    path = db_path or os.environ.get("SUPPORT_DB_PATH", str(_REPO_ROOT / "data" / "support.db"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)


def get_account(conn: sqlite3.Connection, account_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, name, tier, is_enterprise, contact_email FROM accounts WHERE id = ?",
        (account_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "tier": row[2],
        "is_enterprise": bool(row[3]),
        "contact_email": row[4],
    }


def get_subscription(conn: sqlite3.Connection, account_id: str) -> dict | None:
    row = conn.execute(
        "SELECT account_id, plan, status FROM subscriptions WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    if not row:
        return None
    return {"account_id": row[0], "plan": row[1], "status": row[2]}


def get_invoice(conn: sqlite3.Connection, invoice_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, account_id, amount_cents, status, note FROM invoices WHERE id = ?",
        (invoice_id,),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "account_id": row[1], "amount_cents": row[2], "status": row[3], "note": row[4]}


def get_ticket(conn: sqlite3.Connection, ticket_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, account_id, subject, status FROM tickets WHERE id = ?",
        (ticket_id,),
    ).fetchone()
    if not row:
        return None
    return {"id": row[0], "account_id": row[1], "subject": row[2], "status": row[3]}


def insert_audit_event(conn: sqlite3.Connection, event_type: str, account_id: str, details: str) -> int:
    cursor = conn.execute(
        "INSERT INTO audit_log (event_type, account_id, details) VALUES (?, ?, ?)",
        (event_type, account_id, details),
    )
    conn.commit()
    return cursor.lastrowid or 0


def list_invoices_for_account(conn: sqlite3.Connection, account_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT id, account_id, amount_cents, status, note FROM invoices WHERE account_id = ? ORDER BY id",
        (account_id,),
    ).fetchall()
    return [
        {"id": r[0], "account_id": r[1], "amount_cents": r[2], "status": r[3], "note": r[4]}
        for r in rows
    ]
