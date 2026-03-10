"""Internal tools: invoice status, subscription, MFA draft, escalation, human approval, audit log."""
from app.db import (
    get_account,
    get_connection,
    get_invoice,
    get_subscription,
    get_ticket,
    insert_audit_event,
)
from app.guardrails import require_escalation
from app.helpers import normalize_account_id, normalize_invoice_id, normalize_ticket_id, scrub_pii


def check_invoice_status(invoice_id: str, allowed: set[str] | None = None) -> dict:
    """Look up invoice by ID. Returns status and details."""
    if allowed is not None and "check_invoice_status" not in allowed:
        return {"error": "Not authorized to check invoice status"}
    inv_id = normalize_invoice_id(invoice_id)
    conn = get_connection()
    try:
        row = get_invoice(conn, inv_id)
        if not row:
            return {"error": "Invoice not found", "invoice_id": inv_id}
        return {
            "id": row["id"],
            "account_id": row["account_id"],
            "amount_cents": row["amount_cents"],
            "status": row["status"],
            "note": row.get("note"),
        }
    finally:
        conn.close()


def inspect_subscription(account_id: str, allowed: set[str] | None = None) -> dict:
    """Look up subscription/plan for an account."""
    if allowed is not None and "inspect_subscription" not in allowed:
        return {"error": "Not authorized to inspect subscription"}
    aid = normalize_account_id(account_id)
    conn = get_connection()
    try:
        acc = get_account(conn, aid)
        if not acc:
            return {"error": "Account not found", "account_id": aid}
        sub = get_subscription(conn, aid)
        if not sub:
            return {"error": "No subscription found", "account_id": aid}
        return {"account_id": aid, "plan": sub["plan"], "status": sub["status"], "tier": acc["tier"]}
    finally:
        conn.close()


def draft_mfa_reset_request(account_id: str, user_id: str | None = None, allowed: set[str] | None = None) -> dict:
    """Draft an MFA reset request (requires human approval). Does not execute reset.
    PII (contact_email) is scrubbed before returning data to the LLM.
    """
    if allowed is not None and "draft_mfa_reset_request" not in allowed:
        return {"error": "Not authorized to draft MFA reset"}
    aid = normalize_account_id(account_id)
    conn = get_connection()
    try:
        acc = get_account(conn, aid)
        if not acc:
            return {"error": "Account not found", "account_id": aid}
        contact = scrub_pii(acc.get("contact_email") or "")
        if require_escalation(aid, "draft_mfa_reset_request"):
            return {
                "status": "requires_approval",
                "message": "Enterprise account: MFA reset must be approved. Use request_human_approval.",
                "account_id": aid,
                "contact": contact,
            }
        return {
            "status": "draft",
            "message": "MFA reset request drafted for approval.",
            "account_id": aid,
            "user_id": user_id or "admin",
            "contact": contact,
        }
    finally:
        conn.close()


def escalate_ticket(ticket_id: str, allowed: set[str] | None = None) -> dict:
    """Escalate a ticket to tier-2."""
    if allowed is not None and "escalate_ticket" not in allowed:
        return {"error": "Not authorized to escalate"}
    tid = normalize_ticket_id(ticket_id)
    conn = get_connection()
    try:
        ticket = get_ticket(conn, tid)
        if not ticket:
            return {"error": "Ticket not found", "ticket_id": tid}
        return {"status": "escalated", "ticket_id": tid, "account_id": ticket["account_id"], "subject": ticket["subject"]}
    finally:
        conn.close()


def request_human_approval(action: str, reason: str, allowed: set[str] | None = None) -> dict:
    """Request human approval for a sensitive action."""
    if allowed is not None and "request_human_approval" not in allowed:
        return {"error": "Not authorized to request approval"}
    return {"status": "pending_approval", "action": action, "reason": reason}


def log_audit_event(event_type: str, account_id: str, details: str, allowed: set[str] | None = None) -> dict:
    """Write an entry to the audit_log table. Used for sensitive actions like MFA resets and escalations."""
    if allowed is not None and "log_audit_event" not in allowed:
        return {"error": "Not authorized to log audit events"}
    aid = normalize_account_id(account_id)
    safe_details = scrub_pii(details)
    conn = get_connection()
    try:
        row_id = insert_audit_event(conn, event_type, aid, safe_details)
        return {"status": "logged", "audit_id": row_id, "event_type": event_type, "account_id": aid}
    finally:
        conn.close()


TOOL_REGISTRY = {
    "check_invoice_status": check_invoice_status,
    "inspect_subscription": inspect_subscription,
    "draft_mfa_reset_request": draft_mfa_reset_request,
    "escalate_ticket": escalate_ticket,
    "request_human_approval": request_human_approval,
    "log_audit_event": log_audit_event,
}
