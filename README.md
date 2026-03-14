# User Interaction Agent (BMS)

A production-oriented **User Interaction Agent** built with **Python + Pydantic + LangGraph** for a multi-agent Building Management System (BMS).

This agent is the boundary layer between user-facing channels and internal orchestration agents.

## Table of contents

- [System context](#system-context)
- [Scope and responsibilities](#scope-and-responsibilities)
- [Architecture overview](#architecture-overview)
- [Data contracts](#data-contracts)
- [Conversation state](#conversation-state)
- [Routing behavior](#routing-behavior)
- [Project structure](#project-structure)
- [Installation](#installation)
- [How to run](#how-to-run)
- [How to test the agent](#how-to-test-the-agent)
- [Troubleshooting](#troubleshooting)
- [Production notes](#production-notes)

---

## System context

```text
Voice → Speech-to-Text → User Interaction Agent → Intent Agent → Planning Agent → System Agents → User Interaction Agent → GUI
```

## Scope and responsibilities

The User Interaction Agent is responsible for:

- receiving transcribed voice input,
- cleaning/normalizing user text,
- structuring and forwarding requests to the Intent Agent,
- receiving agent/system responses,
- converting internal responses to GUI-safe payloads,
- handling clarification prompts and follow-up user turns,
- maintaining multi-turn conversation context.

### Explicitly out of scope

This component **does not**:

- classify intent,
- perform planning,
- directly execute building-system operations.

---

## Architecture overview

### Core design choices

- **Strict validation** using Pydantic (`extra="forbid"`) to prevent unrecognized input fields.
- **Async node interface** to fit LangGraph async execution and future external I/O.
- **Conditional edge routing** for intent forwarding, GUI output, or clarification waiting.
- **Defensive error path** for malformed events that returns a user-facing GUI error.
- **Conversation history appends** for user/system/agent timeline reconstruction.

### Interaction flow (high level)

1. Incoming event is validated and parsed (`voice_input`, `agent_response`, or `clarification_required`).
2. Node updates state/history/context.
3. Node emits:
   - `intent_agent_payload` for request-forwarding turns,
   - `gui_message` for frontend display,
   - route for downstream edge selection.
4. Graph follows conditional edges (`to_intent`, `to_gui`, `await_user`, `idle`).

---

## Data contracts

### Incoming events

#### `voice_input`

```json
{
  "type": "voice_input",
  "text": "Set room 301 to 22C",
  "user_id": "u-01",
  "timestamp": "2026-03-14T10:45:00Z"
}
```

#### `agent_response`

```json
{
  "type": "agent_response",
  "agent": "system_hvac",
  "message": "Temperature updated successfully.",
  "data": {
    "status": "ok"
  }
}
```

#### `clarification_required`

```json
{
  "type": "clarification_required",
  "agent": "planning_agent",
  "question": "Which floor should be prioritized?"
}
```

### Output to Intent Agent

```json
{
  "type": "user_request",
  "user_id": "u-01",
  "content": "Set room 301 to 22C",
  "source": "voice",
  "timestamp": "2026-03-14T10:45:00Z"
}
```

### Output to GUI

```json
{
  "display_type": "text | notification | question | confirmation | error",
  "title": "string",
  "message": "string",
  "data": {}
}
```

---

## Conversation state

State is carried via `UserInteractionState` and includes durable and runtime fields.

### Durable conversational fields

```python
{
  "conversation_id": "string",
  "user_id": "string",
  "history": [],
  "pending_question": None,
  "context": {}
}
```

### Runtime/graph fields

- `incoming_event`
- `cleaned_text`
- `intent_agent_payload`
- `gui_message`
- `route`

---

## Routing behavior

Valid route outputs:

- `to_intent` → send normalized request payload downstream.
- `to_gui` → send user-facing response to GUI.
- `await_user` → pause flow and wait for more user input.
- `idle` → explicit no-op end state.

If an unexpected route appears, router defaults to `await_user` defensively.

---

## Project structure

- `user_interaction_agent/schemas.py` — Pydantic schemas for events/outputs/history.
- `user_interaction_agent/state.py` — conversation state model used by LangGraph.
- `user_interaction_agent/node.py` — async node logic + validation + route decision.
- `user_interaction_agent/graph.py` — graph wiring and conditional edges.
- `tests/test_user_interaction_agent.py` — behavior and error-path tests.

---

## Installation

### Requirements

- Python `>=3.10`

### Install package

```bash
pip install -e .
```

---

## How to run

### Minimal graph invocation example

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
print(result["route"])
print(result.get("intent_agent_payload"))
print(result.get("gui_message"))
```

---

## How to test the agent

### 1) Run the full test suite

```bash
pytest -q
```

### 2) (Optional) Syntax/import sanity check

```bash
python -m compileall -q user_interaction_agent tests
```

### 3) What test coverage currently includes

- voice normalization and intent payload creation,
- clarification prompt handling (`await_user` route),
- clarification answer loop and `pending_question` reset,
- agent error status mapping to GUI `error`,
- malformed/unsupported event fallback to GUI-safe error,
- unknown route fallback handling.

### 4) Suggested additional tests for integrators

- contract tests against your Intent Agent HTTP/RPC payload shape,
- persistence/re-hydration tests for `UserInteractionState`,
- concurrency tests for simultaneous sessions/user IDs,
- observability tests ensuring log fields contain conversation/user identifiers.

---

## Troubleshooting

### `pytest` fails on async tests

This repository uses plain pytest tests that call async functions with `asyncio.run(...)`, so no async plugin is required.

### Malformed events

Malformed events are intentionally converted to GUI `error` output rather than crashing the run.

### User ID mismatch

If event `user_id` differs from state `user_id`, the node logs a warning and continues processing.

---

## Production notes

- The node is intentionally scoped to interaction/orchestration only.
- It does **not** classify intent or perform downstream planning.


## Implementation highlights

- Strong schema validation for state and incoming events (Pydantic).
- Async LangGraph node with conditional routing.
- Clarification loop support via `await_user` routing and re-entry when a new event is attached in-run.
- Structured logging hooks and graceful GUI-facing error fallback for malformed events.
