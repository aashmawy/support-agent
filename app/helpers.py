"""Normalization and formatting helpers."""


def normalize_account_id(raw: str) -> str:
    """Normalize account ID: uppercase and strip whitespace."""
    if not raw or not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def normalize_ticket_id(raw: str) -> str:
    """Normalize ticket ID: uppercase and strip whitespace."""
    if not raw or not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def normalize_invoice_id(raw: str) -> str:
    """Normalize invoice ID: uppercase and strip whitespace."""
    if not raw or not isinstance(raw, str):
        return ""
    return raw.strip().upper()


def format_tool_result(d: dict) -> str:
    """Format a tool result dict for display."""
    if not d:
        return ""
    parts = [f"{k}: {v}" for k, v in d.items()]
    return "\n".join(parts)
