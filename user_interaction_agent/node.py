"""Async node implementation for the User Interaction Agent."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import ValidationError

from .schemas import (
    AgentResponse,
    ClarificationRequired,
    GuiOutput,
    HistoryEntry,
    IntentAgentRequest,
    ParsedEvent,
    VoiceInput,
)
from .state import UserInteractionState

logger = logging.getLogger(__name__)
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    """Normalize user text while preserving semantics."""
    text = text.strip()
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.replace(" ,", ",").replace(" .", ".")
    return text


def _append_history(
    state: UserInteractionState,
    *,
    role: str,
    event_type: str,
    payload: Dict[str, Any],
    timestamp: datetime,
) -> None:
    state.history.append(
        HistoryEntry(
            role=role,
            event_type=event_type,
            payload=payload,
            timestamp=timestamp,
        )
    )


def _build_gui_error(state: UserInteractionState, message: str) -> GuiOutput:
    return GuiOutput(
        display_type="error",
        title="Invalid interaction payload",
        message=message,
        data={"conversation_id": state.conversation_id},
    )


def _build_intent_request(parsed: VoiceInput, cleaned_text: str) -> IntentAgentRequest:
    return IntentAgentRequest(
        user_id=parsed.user_id,
        content=cleaned_text,
        timestamp=parsed.timestamp,
    )


async def user_interaction_node(state_input: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user/agent events and produce next-step routing outputs.

    This node explicitly does not perform intent classification or planning.
    """
    try:
        state = UserInteractionState.model_validate(state_input)
    except ValidationError as exc:
        logger.exception("State validation failed", extra={"errors": exc.errors()})
        raise

    logger.info(
        "Processing incoming event",
        extra={"conversation_id": state.conversation_id, "user_id": state.user_id},
    )

    try:
        parsed = ParsedEvent.model_validate({"event": state.incoming_event}).event
    except ValidationError as exc:
        logger.warning(
            "Incoming event validation failed",
            extra={"conversation_id": state.conversation_id, "errors": exc.errors()},
        )
        state.gui_message = _build_gui_error(state, "I couldn't process that request. Please try again.")
        state.route = "to_gui"
        return state.model_dump(mode="json")

    if isinstance(parsed, VoiceInput):
        normalized = _normalize_text(parsed.text)
        state.cleaned_text = normalized

        if parsed.user_id != state.user_id:
            logger.warning(
                "Voice input user_id does not match conversation user_id",
                extra={
                    "conversation_id": state.conversation_id,
                    "state_user_id": state.user_id,
                    "event_user_id": parsed.user_id,
                },
            )

        _append_history(
            state,
            role="user",
            event_type="voice_input",
            payload=parsed.model_dump(mode="json"),
            timestamp=parsed.timestamp,
        )

        if state.pending_question:
            answered_question = state.pending_question
            state.context["clarification_answer"] = normalized
            state.context["clarification_answered_at"] = datetime.now(timezone.utc).isoformat()
            state.context["pending_question_resolved"] = answered_question
            state.pending_question = None
            state.gui_message = GuiOutput(
                display_type="notification",
                title="Thanks, updating request",
                message="Got it. I'll continue with your updated details.",
                data={
                    "conversation_id": state.conversation_id,
                    "answered_question": answered_question,
                },
            )
        else:
            state.gui_message = GuiOutput(
                display_type="text",
                title="Request received",
                message=f"Understood: {normalized}",
                data={"conversation_id": state.conversation_id},
            )

        state.intent_agent_payload = _build_intent_request(parsed, normalized)
        state.route = "to_intent"

    elif isinstance(parsed, ClarificationRequired):
        state.pending_question = parsed.question
        state.context["pending_question_agent"] = parsed.agent
        state.context["pending_question_asked_at"] = datetime.now(timezone.utc).isoformat()

        _append_history(
            state,
            role="system",
            event_type="clarification_required",
            payload=parsed.model_dump(mode="json"),
            timestamp=datetime.now(timezone.utc),
        )

        state.gui_message = GuiOutput(
            display_type="question",
            title=f"Need clarification from {parsed.agent}",
            message=parsed.question,
            data={"conversation_id": state.conversation_id, "agent": parsed.agent},
        )
        state.route = "await_user"

    elif isinstance(parsed, AgentResponse):
        _append_history(
            state,
            role="agent",
            event_type="agent_response",
            payload=parsed.model_dump(mode="json"),
            timestamp=datetime.now(timezone.utc),
        )

        display_type = "confirmation"
        if parsed.data.get("status") == "error":
            display_type = "error"
        elif parsed.data.get("status") == "partial":
            display_type = "notification"

        state.gui_message = GuiOutput(
            display_type=display_type,
            title=f"Update from {parsed.agent}",
            message=parsed.message,
            data=parsed.data,
        )
        state.route = "to_gui"

    else:  # pragma: no cover
        raise RuntimeError("Unhandled event variant")

    logger.info(
        "Processed incoming event",
        extra={"conversation_id": state.conversation_id, "route": state.route},
    )

    return state.model_dump(mode="json")


def route_next_step(state_input: Dict[str, Any]) -> str:
    """LangGraph edge router based on state route field."""
    state = UserInteractionState.model_validate(state_input)
    if state.route not in {"to_intent", "to_gui", "await_user", "idle"}:
        logger.warning(
            "Unknown route detected; defaulting to await_user",
            extra={"conversation_id": state.conversation_id, "route": state.route},
        )
        return "await_user"
    return state.route
