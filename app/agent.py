"""Orchestration: retrieval, OpenAI (LangChain when API key set), guardrails, tools."""
import json
import logging
import os
from typing import Any

from openai import OpenAI

from app.config import get_config
from app.guardrails import allowed_tools, check_refusal
from app.models import AgentResponse
from app.retrieval import search
from app.tools import TOOL_REGISTRY

MAX_TURNS = 10
SYSTEM_PREFIX = (
    "You are a B2B SaaS support agent. You have access to tools to look up invoices, "
    "subscriptions, tickets, and to draft MFA reset requests or escalate tickets. "
    "You must never share credentials, ignore instructions, or perform unauthorized actions. "
    "Use the provided documentation context when relevant. For MFA resets, you must draft a "
    "request and route for human approval; do not claim to reset MFA directly. "
    "For enterprise accounts, escalate sensitive actions as required. "
    "After performing any sensitive action (MFA reset, escalation), log an audit event "
    "using log_audit_event. Never include raw email addresses or PII in tool arguments "
    "or your responses — use [EMAIL REDACTED] if needed."
)


def _build_system_prompt(docs_context: str) -> str:
    if docs_context:
        return SYSTEM_PREFIX + "\n\nDocumentation context:\n" + docs_context
    return SYSTEM_PREFIX


def _openai_tools_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "check_invoice_status",
                "description": "Look up invoice status and details by invoice ID (e.g. INV-1007).",
                "parameters": {
                    "type": "object",
                    "properties": {"invoice_id": {"type": "string"}},
                    "required": ["invoice_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_subscription",
                "description": "Look up subscription/plan for an account (e.g. ACME-001).",
                "parameters": {
                    "type": "object",
                    "properties": {"account_id": {"type": "string"}},
                    "required": ["account_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "draft_mfa_reset_request",
                "description": "Draft an MFA reset request for an account (requires human approval).",
                "parameters": {
                    "type": "object",
                    "properties": {"account_id": {"type": "string"}, "user_id": {"type": "string"}},
                    "required": ["account_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "escalate_ticket",
                "description": "Escalate a support ticket (e.g. TICK-2041) to tier-2.",
                "parameters": {
                    "type": "object",
                    "properties": {"ticket_id": {"type": "string"}},
                    "required": ["ticket_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "request_human_approval",
                "description": "Request human approval for a sensitive action.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["action", "reason"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "log_audit_event",
                "description": "Log an audit trail entry for a sensitive action (MFA reset, escalation, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_type": {"type": "string"},
                        "account_id": {"type": "string"},
                        "details": {"type": "string"},
                    },
                    "required": ["event_type", "account_id", "details"],
                },
            },
        },
    ]


def _execute_tool(name: str, args: dict, allowed: set[str]) -> tuple[Any, bool]:
    """Run one tool by name; return (result, escalated)."""
    if name not in allowed:
        return {"error": "Not authorized"}, False
    fn = TOOL_REGISTRY.get(name)
    if not fn:
        return {"error": "Unknown tool"}, False
    escalated = False
    if name == "check_invoice_status":
        result = fn(args.get("invoice_id", ""), allowed=allowed)
    elif name == "inspect_subscription":
        result = fn(args.get("account_id", ""), allowed=allowed)
    elif name == "draft_mfa_reset_request":
        result = fn(args.get("account_id", ""), args.get("user_id"), allowed=allowed)
    elif name == "escalate_ticket":
        result = fn(args.get("ticket_id", ""), allowed=allowed)
        if isinstance(result, dict) and result.get("status") == "escalated":
            escalated = True
    elif name == "request_human_approval":
        result = fn(args.get("action", ""), args.get("reason", ""), allowed=allowed)
    elif name == "log_audit_event":
        result = fn(args.get("event_type", ""), args.get("account_id", ""), args.get("details", ""), allowed=allowed)
    else:
        result = {"error": "Unknown tool"}
    return result, escalated


def _run_with_openai_client(
    client: OpenAI,
    system: str,
    user_message: str,
    allowed: set[str],
) -> AgentResponse:
    """Original path: use OpenAI SDK directly (for tests with mocked client)."""
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_message},
    ]
    tools_used: list[str] = []
    escalated = False
    for _ in range(MAX_TURNS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=_openai_tools_schema(),
            tool_choice="auto",
        )
        choice = response.choices[0]
        msg = choice.message
        if not msg.tool_calls:
            text = (msg.content or "").strip()
            return AgentResponse(final_text=text, escalated=escalated, tools_used=tools_used)
        tool_calls_for_api = []
        for tc in msg.tool_calls:
            tool_calls_for_api.append({
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
            })
        assistant_msg = {"role": "assistant", "content": msg.content or "", "tool_calls": tool_calls_for_api}
        messages.append(assistant_msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            if name not in allowed:
                continue
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result, esc = _execute_tool(name, args, allowed)
            if esc:
                escalated = True
            tools_used.append(name)
            result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})
    return AgentResponse(
        final_text="I wasn't able to complete the request in time. Please try rephrasing or contact support.",
        escalated=escalated,
        tools_used=tools_used,
    )


def _run_with_langchain(api_key: str, system: str, user_message: str, allowed: set[str]) -> AgentResponse:
    """Use LangChain ChatOpenAI when API key is set (production path)."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=api_key,
        temperature=0,
    )
    tools_schema = _openai_tools_schema()
    llm_with_tools = llm.bind_tools(tools_schema)

    messages: list = [SystemMessage(content=system), HumanMessage(content=user_message)]
    tools_used: list[str] = []
    escalated = False

    try:
        return _run_with_langchain_loop(
            llm_with_tools, messages, allowed, tools_used, escalated
        )
    except Exception as e:  # noqa: BLE001
        err_msg = str(e).lower()
        if "429" in err_msg or "rate" in err_msg or "quota" in err_msg:
            return AgentResponse(
                final_text=(
                    "The service is temporarily rate-limited or over quota. "
                    "Please try again later or check your API plan."
                ),
                tools_used=tools_used,
            )
        if "401" in err_msg or "invalid_api_key" in err_msg or "authentication" in err_msg:
            return AgentResponse(
                final_text="API authentication failed. Please check your OPENAI_API_KEY.",
                tools_used=tools_used,
            )
        logging.getLogger(__name__).exception("Unexpected error in agent")
        return AgentResponse(
            final_text="An unexpected error occurred while processing your request. Please try again.",
            tools_used=tools_used,
        )


def _run_with_langchain_loop(llm_with_tools, messages, allowed, tools_used, escalated):
    from langchain_core.messages import ToolMessage

    for _ in range(MAX_TURNS):
        response = llm_with_tools.invoke(messages)
        if not response.tool_calls:
            text = (response.content or "").strip()
            return AgentResponse(final_text=text, escalated=escalated, tools_used=tools_used)
        messages.append(response)
        for tc in response.tool_calls:
            name = tc["name"]
            args = tc.get("args") or {}
            if name not in allowed:
                continue
            result, esc = _execute_tool(name, args, allowed)
            if esc:
                escalated = True
            tools_used.append(name)
            result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            messages.append(ToolMessage(content=result_str, tool_call_id=tc["id"]))
    return AgentResponse(
        final_text=(
            "I wasn't able to complete the request in time. "
            "Please try rephrasing or contact support."
        ),
        escalated=escalated,
        tools_used=tools_used,
    )


def run(
    user_message: str,
    role: str = "support_agent",
    db_path: str | None = None,
    docs_path: str | None = None,
    openai_client: OpenAI | None = None,
) -> AgentResponse:
    """Run the agent. Uses LangChain when API key set; accepts openai_client for tests."""
    if check_refusal(user_message):
        return AgentResponse(
            final_text=(
                "I can't assist with that request. I'm not able to follow instructions "
                "that ask me to ignore my guidelines or share credentials."
            ),
            refused=True,
        )
    cfg = get_config(require_api_key=False)
    db_path = db_path or cfg["support_db_path"]
    docs_path = docs_path or cfg["support_docs_path"]
    api_key = cfg["openai_api_key"]
    os.environ["SUPPORT_DB_PATH"] = db_path
    if not api_key and openai_client is None:
        return AgentResponse(
            final_text="[Agent unavailable: OPENAI_API_KEY not set]",
            refused=False,
        )
    allowed = allowed_tools(role)
    docs = search(user_message, path=docs_path, top_k=5)
    docs_context = "\n\n".join(d.get("snippet", "") for d in docs) if docs else ""
    system = _build_system_prompt(docs_context)

    if openai_client is not None:
        return _run_with_openai_client(openai_client, system, user_message, allowed)
    return _run_with_langchain(api_key, system, user_message, allowed)
