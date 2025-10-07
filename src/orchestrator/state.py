"""
State schema for the LangGraph StateGraph.

This module defines the conversation state structure used throughout
the graph execution. The state tracks messages, intent, extracted slots,
and session information.
"""

from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class ConversationState(TypedDict):
    """
    Main state object for the conversation graph.

    Attributes:
        messages: Conversation history, automatically merged using add_messages reducer
        session_id: Unique identifier for the user session
        intent: Classified intent (TRAVEL, WEATHER, SMALLTALK, OTHER)
        slots: Dictionary of extracted slot values for the current intent
        missing_slots: List of slot names that are missing or ambiguous
        next_action: Next action to take (ask_question, call_tool, respond)
        tool_result: Result from tool execution (if any)
        final_response: Final formatted response to send to user
    """

    # Conversation history - using LangChain's add_messages reducer for automatic merging
    messages: Annotated[list[BaseMessage], add_messages]

    # Session management
    session_id: str

    # Intent routing
    intent: str | None

    # Slot filling
    slots: dict
    missing_slots: list[str]

    # Flow control
    next_action: str | None  # "ask_question", "call_tool", "respond"

    # Results
    tool_result: dict | None
    final_response: str | None
