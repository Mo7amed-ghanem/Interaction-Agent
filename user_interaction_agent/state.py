"""State model for the User Interaction Agent LangGraph node."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .schemas import GuiOutput, HistoryEntry, IntentAgentRequest


class UserInteractionState(BaseModel):
    """Conversation state persisted and passed through graph nodes."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: str
    user_id: str
    history: List[HistoryEntry] = Field(default_factory=list)
    pending_question: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)

    # Runtime fields used by the graph
    incoming_event: Dict[str, Any] = Field(default_factory=dict)
    cleaned_text: Optional[str] = None
    intent_agent_payload: Optional[IntentAgentRequest] = None
    gui_message: Optional[GuiOutput] = None
    route: str = "idle"
