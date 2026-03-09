#!/usr/bin/env python3
"""
Create SQLite DB from schema and load generated JSON. Idempotent: recreates tables.
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO_ROOT / "app" / "schema.sql"
DATA_DIR = Path(os.environ.get("SUPPORT_DATA_DIR", str(REPO_ROOT / "data")))
GENERATED_DIR = DATA_DIR / "generated"
DB_PATH = os.environ.get("SUPPORT_DB_PATH", str(REPO_ROOT / "data" / "support.db"))


def get_schema():
    return SCHEMA_PATH.read_text()


def load_json(name):
    path = GENERATED_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Run scripts/generate_data.py first: missing {path}")
    return json.loads(path.read_text())


def main():
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(get_schema())

    accounts = load_json("accounts.json")
    for row in accounts:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (id, name, tier, is_enterprise) VALUES (?, ?, ?, ?)",
            (row["id"], row["name"], row["tier"], 1 if row.get("is_enterprise") else 0),
        )

    subs = load_json("subscriptions.json")
    for row in subs:
        conn.execute(
            "INSERT OR REPLACE INTO subscriptions (account_id, plan, status) VALUES (?, ?, ?)",
            (row["account_id"], row["plan"], row["status"]),
        )

    invoices = load_json("invoices.json")
    for row in invoices:
        conn.execute(
            "INSERT OR REPLACE INTO invoices (id, account_id, amount_cents, status, note) VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["account_id"], row["amount_cents"], row["status"], row.get("note")),
        )

    tickets = load_json("tickets.json")
    for row in tickets:
        conn.execute(
            "INSERT OR REPLACE INTO tickets (id, account_id, subject, status) VALUES (?, ?, ?, ?)",
            (row["id"], row["account_id"], row["subject"], row["status"]),
        )

    conn.commit()
    conn.close()
    print("DB initialized at", DB_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
