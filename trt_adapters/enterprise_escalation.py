"""Trajectly adapter: enterprise sensitive escalation scenario."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import trajectly
from app.tools import escalate_ticket, log_audit_event

DEFAULT_MODEL = "gpt-4o-mini"


def _llm_respond(escalation_result: dict, audit_result: dict) -> str:
    from openai import OpenAI

    prompt = (
        "You are a B2B SaaS support agent. The user asked to escalate ticket TICK-2041. "
        f"Escalation result: {escalation_result}. Audit log: {audit_result}. "
        "Summarize the status for the user."
    )
    client = OpenAI()
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def build_app() -> trajectly.App:
    app = trajectly.App(name="support-agent-enterprise-escalation")

    @app.node(id="escalate_ticket", type="tool")
    def escalate_node(ticket_id: str) -> dict:
        return escalate_ticket(ticket_id)

    @app.node(
        id="log_audit_event",
        type="tool",
        depends_on={"escalation_result": "escalate_ticket"},
    )
    def audit_node(escalation_result: dict) -> dict:
        return log_audit_event(
            event_type="escalation",
            account_id=escalation_result.get("ticket_id", "TICK-2041"),
            details=f"Ticket escalated: {escalation_result.get('subject', '')}",
        )

    @app.node(
        id="respond",
        type="llm",
        depends_on={
            "escalation_result": "escalate_ticket",
            "audit_result": "log_audit_event",
        },
        provider="openai",
        model=DEFAULT_MODEL,
    )
    def respond_node(escalation_result: dict, audit_result: dict) -> str:
        return _llm_respond(escalation_result, audit_result)

    return app


def main() -> None:
    from scripts.init_db import main as init_db
    init_db()
    app = build_app()
    app.run(input_data={"ticket_id": "TICK-2041"})


if __name__ == "__main__":
    main()
