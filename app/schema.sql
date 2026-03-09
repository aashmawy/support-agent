-- Support agent SQLite schema

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL,
    is_enterprise INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subscriptions (
    account_id TEXT NOT NULL REFERENCES accounts(id),
    plan TEXT NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (account_id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    subject TEXT NOT NULL,
    status TEXT NOT NULL
);
