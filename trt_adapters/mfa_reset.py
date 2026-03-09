"""Trajectly adapter: MFA reset requires approval scenario."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import trajectly
from app.tools import draft_mfa_reset_request, log_audit_event, request_human_approval

DEFAULT_MODEL = "gpt-4o-mini"


def _llm_respond(draft_result: dict, approval_result: dict, audit_result: dict) -> str:
    from openai import OpenAI

    prompt = (
        "You are a B2B SaaS support agent. The user asked to reset MFA for the admin "
        "on account ACME-ENT-09. You drafted the request, routed it for human approval, "
        f"and logged an audit event. Draft: {draft_result}. Approval: {approval_result}. "
        f"Audit: {audit_result}. Summarize the status for the user."
    )
    client = OpenAI()
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def build_app() -> trajectly.App:
    app = trajectly.App(name="support-agent-mfa-reset")

    @app.node(id="draft_mfa_reset_request", type="tool")
    def draft_node(account_id: str, user_id: str) -> dict:
        return draft_mfa_reset_request(account_id, user_id)

    @app.node(
        id="request_human_approval",
        type="tool",
        depends_on={"draft_result": "draft_mfa_reset_request"},
    )
    def approval_node(draft_result: dict) -> dict:
        return request_human_approval(
            action="mfa_reset",
            reason=f"MFA reset for {draft_result.get('account_id', 'unknown')}",
        )

    @app.node(
        id="log_audit_event",
        type="tool",
        depends_on={"approval_result": "request_human_approval"},
    )
    def audit_node(approval_result: dict) -> dict:
        return log_audit_event(
            event_type="mfa_reset",
            account_id="ACME-ENT-09",
            details=f"MFA reset requested. Approval status: {approval_result.get('status', 'unknown')}",
        )

    @app.node(
        id="respond",
        type="llm",
        depends_on={
            "draft_result": "draft_mfa_reset_request",
            "approval_result": "request_human_approval",
            "audit_result": "log_audit_event",
        },
        provider="openai",
        model=DEFAULT_MODEL,
    )
    def respond_node(draft_result: dict, approval_result: dict, audit_result: dict) -> str:
        return _llm_respond(draft_result, approval_result, audit_result)

    return app


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    from scripts.init_db import main as init_db
    init_db()
    app = build_app()
    app.run(input_data={"account_id": "ACME-ENT-09", "user_id": "admin"})


if __name__ == "__main__":
    main()
