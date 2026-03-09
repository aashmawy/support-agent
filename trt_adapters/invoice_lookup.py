"""Trajectly adapter: invoice lookup scenario."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import trajectly
from app.tools import check_invoice_status

DEFAULT_MODEL = "gpt-4o-mini"


def _llm_respond(invoice_data: dict) -> str:
    from openai import OpenAI

    prompt = (
        "You are a B2B SaaS support agent. The user asked: "
        "'Why was invoice INV-1007 higher this month?' "
        f"Here is the invoice data: {invoice_data}. "
        "Give a concise, helpful answer."
    )
    client = OpenAI()
    resp = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    return resp.choices[0].message.content or ""


def build_app() -> trajectly.App:
    app = trajectly.App(name="support-agent-invoice-lookup")

    @app.node(id="check_invoice_status", type="tool")
    def check_invoice_node(invoice_id: str) -> dict:
        return check_invoice_status(invoice_id)

    @app.node(
        id="respond",
        type="llm",
        depends_on={"invoice_data": "check_invoice_status"},
        provider="openai",
        model=DEFAULT_MODEL,
    )
    def respond_node(invoice_data: dict) -> str:
        return _llm_respond(invoice_data)

    return app


def main() -> None:
    from scripts.init_db import main as init_db
    init_db()
    app = build_app()
    app.run(input_data={"invoice_id": "INV-1007"})


if __name__ == "__main__":
    main()
