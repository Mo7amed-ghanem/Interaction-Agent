"""LangGraph assembly for the User Interaction Agent."""

from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from .node import route_next_step, user_interaction_node


def _passthrough(state: Dict[str, Any]) -> Dict[str, Any]:
    return state


def build_user_interaction_graph():
    """Build and compile the user interaction graph.

    Routes:
    - `to_intent`: send payload downstream to Intent Agent.
    - `to_gui`: send formatted GUI message to frontend.
    - `await_user`: keep state and wait for next user turn.
    """
    graph = StateGraph(dict)

    graph.add_node("user_interaction", user_interaction_node)
    graph.add_node("emit_intent_payload", _passthrough)
    graph.add_node("emit_gui_message", _passthrough)
    graph.add_node("wait_for_user", _passthrough)

    graph.add_edge(START, "user_interaction")
    graph.add_conditional_edges(
        "user_interaction",
        route_next_step,
        {
            "to_intent": "emit_intent_payload",
            "to_gui": "emit_gui_message",
            "await_user": "wait_for_user",
        },
    )
    graph.add_edge("emit_intent_payload", END)
    graph.add_edge("emit_gui_message", END)
    graph.add_edge("wait_for_user", END)

    return graph.compile()
