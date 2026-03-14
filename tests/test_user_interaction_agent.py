from datetime import datetime, timezone

import pytest

from user_interaction_agent.node import route_next_step, user_interaction_node


@pytest.mark.asyncio
async def test_voice_input_generates_intent_payload_and_gui_text():
    state = {
        "conversation_id": "c1",
        "user_id": "u1",
        "history": [],
        "pending_question": None,
        "context": {},
        "incoming_event": {
            "type": "voice_input",
            "text": "  turn on   lights in lobby  ",
            "user_id": "u1",
            "timestamp": "2026-01-01T00:00:00Z",
        },
    }

    result = await user_interaction_node(state)

    assert result["cleaned_text"] == "turn on lights in lobby"
    assert result["intent_agent_payload"]["type"] == "user_request"
    assert result["route"] == "to_intent"
    assert result["gui_message"]["display_type"] == "text"


@pytest.mark.asyncio
async def test_clarification_sets_pending_question_and_wait_route():
    state = {
        "conversation_id": "c2",
        "user_id": "u1",
        "history": [],
        "pending_question": None,
        "context": {},
        "incoming_event": {
            "type": "clarification_required",
            "agent": "planning_agent",
            "question": "Which floor should be prioritized?",
        },
    }

    result = await user_interaction_node(state)

    assert result["pending_question"] == "Which floor should be prioritized?"
    assert result["route"] == "await_user"
    assert result["gui_message"]["display_type"] == "question"


@pytest.mark.asyncio
async def test_clarification_answer_goes_to_intent_and_resets_pending_question():
    state = {
        "conversation_id": "c2",
        "user_id": "u1",
        "history": [],
        "pending_question": "Which floor should be prioritized?",
        "context": {},
        "incoming_event": {
            "type": "voice_input",
            "text": "Prioritize floor 3",
            "user_id": "u1",
            "timestamp": "2026-01-01T00:01:00Z",
        },
    }

    result = await user_interaction_node(state)

    assert result["pending_question"] is None
    assert result["route"] == "to_intent"
    assert result["gui_message"]["display_type"] == "notification"
    assert result["context"]["clarification_answer"] == "Prioritize floor 3"


@pytest.mark.asyncio
async def test_agent_response_maps_error_to_gui_error_display_type():
    now = datetime.now(timezone.utc).isoformat()
    state = {
        "conversation_id": "c3",
        "user_id": "u1",
        "history": [],
        "pending_question": None,
        "context": {},
        "incoming_event": {
            "type": "agent_response",
            "agent": "system_hvac",
            "message": "Unable to contact thermostat.",
            "data": {"status": "error", "timestamp": now},
        },
    }

    result = await user_interaction_node(state)

    assert result["route"] == "to_gui"
    assert result["gui_message"]["display_type"] == "error"


@pytest.mark.asyncio
async def test_invalid_event_is_mapped_to_gui_error():
    state = {
        "conversation_id": "c4",
        "user_id": "u1",
        "history": [],
        "pending_question": None,
        "context": {},
        "incoming_event": {
            "type": "unknown",
        },
    }

    result = await user_interaction_node(state)

    assert result["route"] == "to_gui"
    assert result["gui_message"]["display_type"] == "error"


def test_route_next_step_defaults_unknown_routes_to_await_user():
    state = {
        "conversation_id": "c5",
        "user_id": "u1",
        "history": [],
        "pending_question": None,
        "context": {},
        "incoming_event": {},
        "route": "something_else",
    }

    assert route_next_step(state) == "await_user"
