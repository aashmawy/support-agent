"""Normalization, formatting, and PII scrubbing helpers."""
import re

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


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


def scrub_pii(text: str) -> str:
    """Replace email addresses with [EMAIL REDACTED]."""
    if not text or not isinstance(text, str):
        return text or ""
    return _EMAIL_RE.sub("[EMAIL REDACTED]", text)


def format_tool_result(d: dict) -> str:
    """Format a tool result dict for display."""
    if not d:
        return ""
    parts = [f"{k}: {v}" for k, v in d.items()]
    return "\n".join(parts)
