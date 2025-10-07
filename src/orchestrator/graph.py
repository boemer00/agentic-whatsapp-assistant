"""
LangGraph-based conversation orchestration.

This module defines the StateGraph for handling multi-turn conversations
with intent routing, slot filling, validation, and tool execution.

Graph Flow:
    START → setup_session → route_intent → [extract_slots or generate_response] →
    validate_slots → [ask_question or call_tool or generate_response] → END
"""

from typing import AsyncIterator
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from src.core.tracing import traceable
from src.orchestrator.state import ConversationState
from src.orchestrator.nodes import (
    setup_session_node,
    route_intent_node,
    extract_slots_node,
    validate_slots_node,
    ask_question_node,
    call_tool_node,
    generate_response_node,
    should_extract_slots,
    route_after_validation,
)


def build_graph() -> StateGraph:
    """
    Build and compile the conversation StateGraph.

    Returns:
        Compiled StateGraph ready for execution
    """
    # Create the graph with ConversationState schema
    graph = StateGraph(ConversationState)

    # Add all nodes
    graph.add_node("setup_session", setup_session_node)
    graph.add_node("route_intent", route_intent_node)
    graph.add_node("extract_slots", extract_slots_node)
    graph.add_node("validate_slots", validate_slots_node)
    graph.add_node("ask_question", ask_question_node)
    graph.add_node("call_tool", call_tool_node)
    graph.add_node("generate_response", generate_response_node)

    # Define edges
    # START -> setup_session -> route_intent
    graph.add_edge(START, "setup_session")
    graph.add_edge("setup_session", "route_intent")

    # route_intent -> extract_slots OR generate_response
    # (WEATHER/TRAVEL extract slots, SMALLTALK/OTHER skip to response)
    graph.add_conditional_edges(
        "route_intent",
        should_extract_slots,
        {
            "extract_slots": "extract_slots",
            "generate_response": "generate_response",
        },
    )

    # extract_slots -> validate_slots (always)
    graph.add_edge("extract_slots", "validate_slots")

    # validate_slots -> ask_question OR call_tool OR generate_response
    graph.add_conditional_edges(
        "validate_slots",
        route_after_validation,
        {
            "ask_question": "ask_question",
            "call_tool": "call_tool",
            "generate_response": "generate_response",
        },
    )

    # Terminal nodes -> END
    graph.add_edge("ask_question", END)
    graph.add_edge("call_tool", END)
    graph.add_edge("generate_response", END)

    # Compile the graph
    return graph.compile()


# Global compiled graph instance
_compiled_graph = None


def get_graph():
    """
    Get or create the compiled graph instance.

    Lazy initialization to avoid building graph on import.
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


@traceable(name="handle_turn")
async def handle_turn(session_id: str, message: str) -> AsyncIterator[str]:
    """
    Handle a conversation turn using LangGraph.

    This replaces the previous sequential orchestration with graph-based execution.
    Streams output tokens as the graph executes.

    Args:
        session_id: Unique session identifier for the user
        message: User's input message

    Yields:
        String tokens as the graph produces output
    """
    graph = get_graph()

    # Initialize state with user message
    initial_state: ConversationState = {
        "messages": [HumanMessage(content=message)],
        "session_id": session_id,
        "intent": None,
        "slots": {},
        "missing_slots": [],
        "next_action": None,
        "tool_result": None,
        "final_response": None,
    }

    # Configure execution with session-based thread_id for state persistence
    config = {
        "configurable": {
            "thread_id": session_id,
        }
    }

    # Stream graph execution
    async for event in graph.astream(initial_state, config):
        # event is a dict: {node_name: node_output}
        for node_name, node_output in event.items():
            # Skip if node produced no output
            if not node_output:
                continue

            # Yield intent when classified
            if node_name == "route_intent" and "intent" in node_output:
                intent = node_output["intent"]
                yield f"[intent:{intent}]"

            # Yield final response when available
            if "final_response" in node_output and node_output["final_response"]:
                yield node_output["final_response"]
