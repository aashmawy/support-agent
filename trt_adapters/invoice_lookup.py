"""Trajectly adapter: invoice lookup scenario."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import trajectly
from app.tools import check_invoice_status

DEFAULT_MODEL = "gpt-4o-mini"


def _should_use_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _llm_respond(invoice_data: dict, *, use_openai: bool) -> str:
    prompt = (
        "You are a B2B SaaS support agent. The user asked: "
        "'Why was invoice INV-1007 higher this month?' "
        f"Here is the invoice data: {invoice_data}. "
        "Give a concise, helpful answer."
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
    return f"Invoice INV-1007: amount={invoice_data.get('amount_cents')} status={invoice_data.get('status')}"


def build_app(*, use_openai: bool | None = None) -> trajectly.App:
    if use_openai is None:
        use_openai = _should_use_openai()

    provider = "openai" if use_openai else "mock-openai"
    model = DEFAULT_MODEL if use_openai else "mock-support-v1"

    app = trajectly.App(name="support-agent-invoice-lookup")

    @app.node(id="check_invoice_status", type="tool")
    def check_invoice_node(invoice_id: str = "INV-1007") -> dict:
        return check_invoice_status(invoice_id)

    @app.node(
        id="respond",
        type="llm",
        depends_on={"invoice_data": "check_invoice_status"},
        provider=provider,
        model=model,
    )
    def respond_node(invoice_data: dict) -> str:
        return _llm_respond(invoice_data, use_openai=use_openai)

    return app


def main() -> None:
    from scripts.init_db import main as init_db
    init_db()
    app = build_app()
    app.run()


if __name__ == "__main__":
    main()
