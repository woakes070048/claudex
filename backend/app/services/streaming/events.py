from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from app.models.types import JSONDict, JSONValue


StreamEventType = Literal[
    "assistant_text",
    "assistant_thinking",
    "tool_started",
    "tool_completed",
    "tool_failed",
    "user_text",
    "system",
    "permission_request",
    "prompt_suggestions",
]


class ToolPayload(TypedDict, total=False):
    id: str
    name: str
    title: str
    status: Literal["started", "completed", "failed"]
    parent_id: str | None
    input: JSONDict | None
    result: JSONValue
    error: str


class StreamEvent(TypedDict, total=False):
    type: StreamEventType
    text: str
    thinking: str
    tool: ToolPayload
    data: JSONDict
    request_id: str
    tool_name: str
    tool_input: JSONDict
    suggestions: list[str]


@dataclass
class ActiveToolState:
    id: str
    name: str
    title: str
    parent_id: str | None
    input: JSONDict | None

    def to_payload(self) -> ToolPayload:
        payload: ToolPayload = {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "parent_id": self.parent_id,
            "input": self.input or None,
        }
        return payload
