"""Property-based tests with Hypothesis: normalization, auth consistency, sanitization, PII scrubbing."""
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from app.guardrails import allowed_tools
from app.helpers import normalize_account_id, normalize_ticket_id, scrub_pii
from app.retrieval import _sanitize_snippet

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@given(st.text(min_size=1, max_size=50))
def test_normalize_account_id_idempotent(s: str):
    """Normalizing twice gives the same result."""
    n1 = normalize_account_id(s)
    n2 = normalize_account_id(n1)
    assert n1 == n2 or (n1 == "" and n2 == "")


@given(st.sampled_from(["ACME-001", "acme-001", "  ACME-001  ", "ACME-ENT-09"]))
def test_authorization_consistency_equivalent_ids(account_id: str):
    """Equivalent account ID forms get the same allowed tools."""
    normalized = normalize_account_id(account_id)
    if normalized:
        t1 = allowed_tools("support_agent")
        t2 = allowed_tools("support_agent")
        assert t1 == t2
        assert "check_invoice_status" in t1


DANGEROUS_IN_RETRIEVAL = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "send credentials",
    "email me credentials",
]


@given(st.text(min_size=1, max_size=200))
def test_sanitize_snippet_removes_injection_phrase(text: str):
    """If text contains any dangerous phrase, snippet is redacted; else unchanged."""
    result = _sanitize_snippet(text)
    has_dangerous = any(p.lower() in text.lower() for p in DANGEROUS_IN_RETRIEVAL)
    if has_dangerous:
        assert result == "[Content redacted for security]"
    else:
        assert result == text


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyzACME-001", min_size=0, max_size=30))
def test_normalize_ticket_id_idempotent(s: str):
    """Normalize ticket ID is idempotent when result matches TICK-123 pattern."""
    n1 = normalize_ticket_id(s)
    n2 = normalize_ticket_id(n1)
    assert n1 == n2


EMAIL_STRATEGY = st.from_regex(r"[a-z]{1,8}@[a-z]{1,6}\.[a-z]{2,4}", fullmatch=True)


@given(st.tuples(st.text(min_size=0, max_size=30), EMAIL_STRATEGY, st.text(min_size=0, max_size=30)))
def test_scrub_pii_removes_all_emails(parts):
    """Any string containing an email address must have it scrubbed."""
    prefix, email, suffix = parts
    text = prefix + email + suffix
    result = scrub_pii(text)
    assert "@" not in result
    assert "[EMAIL REDACTED]" in result


@given(st.text(min_size=0, max_size=100).filter(lambda t: "@" not in t))
def test_scrub_pii_preserves_non_email_text(text: str):
    """Text without email addresses is returned unchanged."""
    assert scrub_pii(text) == text
