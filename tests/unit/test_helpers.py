"""Unit tests for helpers: normalize_account_id, normalize_ticket_id, format_tool_result."""
from app.helpers import (
    format_tool_result,
    normalize_account_id,
    normalize_invoice_id,
    normalize_ticket_id,
)


def test_normalize_account_id_uppercase():
    assert normalize_account_id("acme-001") == "ACME-001"
    assert normalize_account_id("ACME-001") == "ACME-001"


def test_normalize_account_id_strip():
    assert normalize_account_id("  ACME-001  ") == "ACME-001"


def test_normalize_account_id_enterprise():
    assert normalize_account_id("acme-ent-09") == "ACME-ENT-09"


def test_normalize_ticket_id():
    assert normalize_ticket_id("tick-2041") == "TICK-2041"
    assert normalize_ticket_id("  TICK-2041  ") == "TICK-2041"


def test_normalize_invoice_id():
    assert normalize_invoice_id("inv-1007") == "INV-1007"


def test_normalize_account_idempotent():
    x = "acme-001"
    assert normalize_account_id(normalize_account_id(x)) == normalize_account_id(x)


def test_normalize_ticket_idempotent():
    x = "tick-2041"
    assert normalize_ticket_id(normalize_ticket_id(x)) == normalize_ticket_id(x)


def test_format_tool_result():
    d = {"status": "paid", "id": "INV-1007"}
    out = format_tool_result(d)
    assert "paid" in out
    assert "INV-1007" in out


def test_format_tool_result_empty():
    assert format_tool_result({}) == ""
