"""Deterministic safety and policy checks. No I/O."""
import re

REFUSAL_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)",
    r"email\s+(me\s+)?(my\s+)?credentials",
    r"send\s+(me\s+)?(my\s+)?(password|credentials|secret)",
    r"reset\s+password\s+directly",
    r"bypass\s+(security|approval|mfa)",
]

WRITE_TOOLS = frozenset({
    "draft_mfa_reset_request",
    "escalate_ticket",
    "request_human_approval",
    "log_audit_event",
})

READ_TOOLS = frozenset({
    "check_invoice_status",
    "inspect_subscription",
})


def check_refusal(message: str) -> bool:
    """Return True if the message should be refused (injection/override/credential ask)."""
    if not message or not isinstance(message, str):
        return False
    lower = message.lower().strip()
    for pat in REFUSAL_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return True
    return False


def require_approval_for_mfa() -> bool:
    """MFA reset always requires human approval."""
    return True


def require_escalation(account_id: str, action: str) -> bool:
    """Return True if this account/action must go through escalation (e.g. enterprise)."""
    if not account_id:
        return False
    aid = account_id.upper().strip()
    if "ENT" in aid or aid.startswith("ACME-ENT"):
        if action in ("mfa_reset", "draft_mfa_reset_request", "bulk_change"):
            return True
    return False


def allowed_tools(role_or_context: str | None = None) -> set[str]:
    """Return tool names allowed for role. support_agent allows all registered tools."""
    all_tools = {
        "check_invoice_status",
        "inspect_subscription",
        "draft_mfa_reset_request",
        "escalate_ticket",
        "request_human_approval",
        "log_audit_event",
    }
    if role_or_context == "blocked":
        return set()
    return all_tools


def is_dangerous_tool(name: str) -> bool:
    """Tools that must never be executed without explicit approval path."""
    return name in ("draft_mfa_reset_request",)


def is_write_tool(name: str) -> bool:
    """Return True if the tool has side effects (writes data)."""
    return name in WRITE_TOOLS
