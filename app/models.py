"""Data models for the support agent."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    tool_name: str
    result: dict[str, Any] | str


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class AgentResponse:
    final_text: str
    escalated: bool = False
    refused: bool = False
    tools_used: list[str] = field(default_factory=list)
