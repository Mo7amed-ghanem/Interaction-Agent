# User Interaction Agent (BMS)

This repository contains a LangGraph-based **User Interaction Agent** for a multi-agent Building Management System (BMS).

The agent is responsible for:
- ingesting transcribed voice input,
- normalizing and validating user text,
- forwarding structured requests to the Intent Agent,
- receiving agent responses,
- turning internal responses into GUI-safe user messages,
- handling clarification loops,
- preserving multi-turn conversation state.

## Package layout

- `user_interaction_agent/schemas.py` – Pydantic input/output schemas.
- `user_interaction_agent/state.py` – conversation state model used by LangGraph.
- `user_interaction_agent/node.py` – async node logic for all supported event types.
- `user_interaction_agent/graph.py` – LangGraph graph construction with conditional edges and looping.

## Quick usage

```python
import asyncio
from user_interaction_agent import UserInteractionState, build_user_interaction_graph

app = build_user_interaction_graph()

initial = UserInteractionState(
    conversation_id="conv-001",
    user_id="u-01",
    history=[],
    pending_question=None,
    context={},
    incoming_event={
        "type": "voice_input",
        "text": "Can you set the meeting room to 22 degrees?",
        "user_id": "u-01",
        "timestamp": "2026-03-14T10:45:00Z",
    },
)

result = asyncio.run(app.ainvoke(initial.model_dump()))
print(result["intent_agent_payload"])
print(result["gui_message"])
```

## Notes

- The node is intentionally scoped to interaction/orchestration only.
- It does **not** classify intent or perform downstream planning.


## Implementation highlights

- Strong schema validation for state and incoming events (Pydantic).
- Async LangGraph node with conditional routing.
- Clarification loop support via `await_user` routing and re-entry when a new event is attached in-run.
- Structured logging hooks and graceful GUI-facing error fallback for malformed events.
