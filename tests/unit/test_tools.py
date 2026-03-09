"""Unit tests for tools: direct calls against a real test DB."""
import os
import sqlite3
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture()
def tool_db(tmp_path):
    """Create a temporary DB with schema + fixture data, set env var."""
    db_path = str(tmp_path / "support.db")
    schema = (REPO_ROOT / "app" / "schema.sql").read_text()
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.execute(
        "INSERT INTO accounts (id, name, tier, is_enterprise) VALUES (?,?,?,?)",
        ("ACME-001", "Acme Corp", "professional", 0),
    )
    conn.execute(
        "INSERT INTO accounts (id, name, tier, is_enterprise) VALUES (?,?,?,?)",
        ("ACME-ENT-09", "Acme Enterprise", "enterprise", 1),
    )
    conn.execute(
        "INSERT INTO subscriptions (account_id, plan, status) VALUES (?,?,?)",
        ("ACME-001", "Pro Monthly", "active"),
    )
    conn.execute(
        "INSERT INTO invoices (id, account_id, amount_cents, status, note) VALUES (?,?,?,?,?)",
        ("INV-1007", "ACME-001", 19900, "paid", "Q1 add-on: extra seats."),
    )
    conn.execute(
        "INSERT INTO tickets (id, account_id, subject, status) VALUES (?,?,?,?)",
        ("TICK-2041", "ACME-001", "Billing", "open"),
    )
    conn.commit()
    conn.close()

    old = os.environ.get("SUPPORT_DB_PATH")
    os.environ["SUPPORT_DB_PATH"] = db_path
    yield db_path
    if old is not None:
        os.environ["SUPPORT_DB_PATH"] = old
    else:
        os.environ.pop("SUPPORT_DB_PATH", None)


class TestCheckInvoiceStatus:
    def test_existing_invoice(self, tool_db):
        from app.tools import check_invoice_status
        result = check_invoice_status("INV-1007")
        assert result["id"] == "INV-1007"
        assert result["status"] == "paid"
        assert result["amount_cents"] == 19900

    def test_missing_invoice(self, tool_db):
        from app.tools import check_invoice_status
        result = check_invoice_status("INV-9999")
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_not_authorized(self, tool_db):
        from app.tools import check_invoice_status
        result = check_invoice_status("INV-1007", allowed=set())
        assert "error" in result
        assert "not authorized" in result["error"].lower()

    def test_normalizes_id(self, tool_db):
        from app.tools import check_invoice_status
        result = check_invoice_status("  inv-1007  ")
        assert result["id"] == "INV-1007"


class TestInspectSubscription:
    def test_existing_account(self, tool_db):
        from app.tools import inspect_subscription
        result = inspect_subscription("ACME-001")
        assert result["plan"] == "Pro Monthly"
        assert result["status"] == "active"

    def test_missing_account(self, tool_db):
        from app.tools import inspect_subscription
        result = inspect_subscription("NONEXIST-999")
        assert "error" in result

    def test_not_authorized(self, tool_db):
        from app.tools import inspect_subscription
        result = inspect_subscription("ACME-001", allowed=set())
        assert "error" in result


class TestDraftMfaResetRequest:
    def test_non_enterprise_returns_draft(self, tool_db):
        from app.tools import draft_mfa_reset_request
        result = draft_mfa_reset_request("ACME-001")
        assert result["status"] == "draft"
        assert "approval" in result["message"].lower()

    def test_enterprise_requires_approval(self, tool_db):
        from app.tools import draft_mfa_reset_request
        result = draft_mfa_reset_request("ACME-ENT-09")
        assert result["status"] == "requires_approval"

    def test_not_authorized(self, tool_db):
        from app.tools import draft_mfa_reset_request
        result = draft_mfa_reset_request("ACME-001", allowed=set())
        assert "error" in result


class TestEscalateTicket:
    def test_existing_ticket(self, tool_db):
        from app.tools import escalate_ticket
        result = escalate_ticket("TICK-2041")
        assert result["status"] == "escalated"
        assert result["ticket_id"] == "TICK-2041"

    def test_missing_ticket(self, tool_db):
        from app.tools import escalate_ticket
        result = escalate_ticket("TICK-0000")
        assert "error" in result

    def test_not_authorized(self, tool_db):
        from app.tools import escalate_ticket
        result = escalate_ticket("TICK-2041", allowed=set())
        assert "error" in result


class TestRequestHumanApproval:
    def test_returns_pending(self):
        from app.tools import request_human_approval
        result = request_human_approval("mfa_reset", "Enterprise account requires it")
        assert result["status"] == "pending_approval"
        assert result["action"] == "mfa_reset"

    def test_not_authorized(self):
        from app.tools import request_human_approval
        result = request_human_approval("mfa_reset", "reason", allowed=set())
        assert "error" in result


class TestToolRegistry:
    def test_all_tools_registered(self):
        from app.tools import TOOL_REGISTRY
        expected = {
            "check_invoice_status",
            "inspect_subscription",
            "draft_mfa_reset_request",
            "escalate_ticket",
            "request_human_approval",
        }
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_all_callables(self):
        from app.tools import TOOL_REGISTRY
        for name, fn in TOOL_REGISTRY.items():
            assert callable(fn), f"{name} is not callable"
