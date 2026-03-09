"""Trajectly adapter: MFA reset requires approval scenario."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import trajectly
from app.tools import draft_mfa_reset_request, request_human_approval

DEFAULT_MODEL = "gpt-4o-mini"


def _should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _llm_respond(draft_result: dict, approval_result: dict, *, use_openai: bool) -> str:
    prompt = (
        "You are a B2B SaaS support agent. The user asked to reset MFA for the admin "
        "on account ACME-ENT-09. You drafted the request and routed it for human approval. "
        f"Draft result: {draft_result}. Approval result: {approval_result}. "
        "Summarize the status for the user."
    )
    if use_openai:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return resp.choices[0].message.content or ""
    return f"MFA reset drafted: {draft_result.get('status')}. Approval: {approval_result.get('status')}."


def build_app(*, use_openai: bool | None = None) -> trajectly.App:
    if use_openai is None:
        use_openai = _should_use_openai()

    provider = "openai" if use_openai else "mock-openai"
    model = DEFAULT_MODEL if use_openai else "mock-support-v1"

    app = trajectly.App(name="support-agent-mfa-reset")

    @app.node(id="draft_mfa_reset_request", type="tool")
    def draft_node(account_id: str = "ACME-ENT-09", user_id: str = "admin") -> dict:
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
        id="respond",
        type="llm",
        depends_on={
            "draft_result": "draft_mfa_reset_request",
            "approval_result": "request_human_approval",
        },
        provider=provider,
        model=model,
    )
    def respond_node(draft_result: dict, approval_result: dict) -> str:
        return _llm_respond(draft_result, approval_result, use_openai=use_openai)

    return app


def main() -> None:
    from scripts.init_db import main as init_db
    init_db()
    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
