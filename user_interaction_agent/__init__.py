"""User Interaction Agent package."""

from .node import route_next_step, user_interaction_node
from .schemas import (
    AgentResponse,
    ClarificationRequired,
    GuiOutput,
    IntentAgentRequest,
    VoiceInput,
)
from .state import UserInteractionState


def build_user_interaction_graph():
    """Lazy import graph builder so core modules work without LangGraph installed."""
    from .graph import build_user_interaction_graph as _builder

    return _builder()


__all__ = [
    "AgentResponse",
    "ClarificationRequired",
    "GuiOutput",
    "IntentAgentRequest",
    "VoiceInput",
    "UserInteractionState",
    "build_user_interaction_graph",
    "route_next_step",
    "user_interaction_node",
]
