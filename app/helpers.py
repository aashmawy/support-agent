"""Normalization and formatting helpers."""
import re


def normalize_account_id(raw: str) -> str:
    """Normalize account ID: uppercase, strip. Pattern like ACME-001 or ACME-ENT-09."""
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().upper()
    return s if re.match(r"^[A-Z0-9]+-[A-Z0-9]+$", s) else s


def normalize_ticket_id(raw: str) -> str:
    """Normalize ticket ID: uppercase, strip. Pattern like TICK-2041."""
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().upper()
    return s if re.match(r"^TICK-\d+$", s) else s


def normalize_invoice_id(raw: str) -> str:
    """Normalize invoice ID: uppercase, strip. Pattern like INV-1007."""
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip().upper()
    return s if re.match(r"^INV-\d+$", s) else s


def format_tool_result(d: dict) -> str:
    """Format a tool result dict for display."""
    if not d:
        return ""
    parts = [f"{k}: {v}" for k, v in d.items()]
    return "\n".join(parts)
