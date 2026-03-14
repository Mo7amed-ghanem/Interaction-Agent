"""Pydantic schemas for the User Interaction Agent."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DisplayType(str, Enum):
    """GUI display types used by the frontend."""

    TEXT = "text"
    NOTIFICATION = "notification"
    QUESTION = "question"
    CONFIRMATION = "confirmation"
    ERROR = "error"


class VoiceInput(BaseModel):
    """Incoming transcribed voice request."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["voice_input"]
    text: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    timestamp: datetime


class AgentResponse(BaseModel):
    """Response produced by an internal agent."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["agent_response"]
    agent: str = Field(min_length=1)
    message: str = Field(min_length=1)
    data: Dict[str, Any] = Field(default_factory=dict)


class ClarificationRequired(BaseModel):
    """Event emitted when downstream agents need additional user input."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["clarification_required"]
    agent: str = Field(min_length=1)
    question: str = Field(min_length=1)


IncomingEvent = Union[VoiceInput, AgentResponse, ClarificationRequired]


class IntentAgentRequest(BaseModel):
    """Structured request sent to the Intent Agent."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["user_request"] = "user_request"
    user_id: str
    content: str
    source: Literal["voice"] = "voice"
    timestamp: datetime


class GuiOutput(BaseModel):
    """Standardized GUI payload for UI rendering."""

    model_config = ConfigDict(extra="forbid")

    display_type: DisplayType
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class HistoryEntry(BaseModel):
    """Single conversation timeline event."""

    role: Literal["user", "agent", "system"]
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime


class ParsedEvent(BaseModel):
    """Internal parsed event wrapper."""

    event: IncomingEvent

    @field_validator("event", mode="before")
    @classmethod
    def parse_event(cls, value: Any) -> IncomingEvent:
        if not isinstance(value, dict):
            raise TypeError("incoming event must be a dict")

        event_type = value.get("type")
        if event_type == "voice_input":
            return VoiceInput.model_validate(value)
        if event_type == "agent_response":
            return AgentResponse.model_validate(value)
        if event_type == "clarification_required":
            return ClarificationRequired.model_validate(value)

        raise ValueError(f"Unsupported event type: {event_type!r}")
