"""
Graph nodes for LangGraph StateGraph.

Each node represents a step in the conversation flow:
1. setup_session - Ensure session_id exists (from thread_id if needed)
2. route_intent - Classify user intent using LLM
3. extract_slots - Extract required information from message
4. validate_slots - Check for missing or ambiguous information
5. ask_question - Generate clarifying question
6. call_tool - Execute tool with validated slots
7. generate_response - Format final response
"""

from datetime import date
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI

from src.core.config import settings
from src.core.tracing import traceable
from src.orchestrator.state import ConversationState
from src.orchestrator.validators import normalise_date, normalise_iata_or_city, normalise_pax
from src.orchestrator.ask_policy import (
    next_missing,
    TRAVEL_PRIORITY,
    WEATHER_PRIORITY,
    travel_question,
    weather_question,
)
from src.orchestrator.extractor import extract_structured
from src.orchestrator.prompts import EXTRACT_WEATHER, EXTRACT_TRAVEL
from src.schemas.graph_state import IntentClassification
from src.schemas.weather import WeatherSlots
from src.schemas.travel import TravelSlots, REQUIRED_ONE_WAY
from src.tools.toolkit import call_tool
from src.tools.base import ToolContext


@traceable(name="setup_session_node")
def setup_session_node(state: ConversationState, config: RunnableConfig) -> ConversationState:
    """
    Ensure session_id exists in state.

    If session_id is not provided in the initial state (e.g., when testing in Studio),
    copy it from the thread_id in config. This guarantees session_id is always available
    for downstream nodes.
    """
    if not state.get("session_id"):
        return {"session_id": config["configurable"]["thread_id"]}
    return {}


@traceable(name="route_intent_node")
def route_intent_node(state: ConversationState) -> ConversationState:
    """
    Classify user intent using LLM-powered classification.

    Replaces keyword-based routing with structured LLM output.
    Falls back to keyword matching if LLM is not available.
    """
    # Get the last user message
    last_message = state["messages"][-1].content if state["messages"] else ""

    # Try LLM-based classification if OpenAI key is configured
    if settings.openai_api_key:
        try:
            llm = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_model or "gpt-4o-mini",
                temperature=0,
            )
            structured_llm = llm.with_structured_output(IntentClassification)

            prompt = f"""Classify the following user message into one of these intents:
- TRAVEL: Flight booking, airline queries, travel planning
- WEATHER: Weather forecast, temperature, conditions
- SMALLTALK: Greetings, thanks, casual conversation
- OTHER: Everything else

User message: {last_message}

Provide the intent, confidence score, and reasoning."""

            result = structured_llm.invoke([HumanMessage(content=prompt)])
            intent = result.intent

        except Exception as e:
            # Log the error for debugging
            print(f"⚠️  LLM intent classification failed: {type(e).__name__}: {str(e)[:100]}")
            print(f"   Falling back to keyword-based routing")
            # Fall back to keyword-based routing
            intent = _keyword_route(last_message)
    else:
        # Use keyword-based routing if no LLM configured
        intent = _keyword_route(last_message)

    return {
        "intent": intent,
        "slots": {},
        "missing_slots": [],
    }


def _keyword_route(text: str) -> str:
    """Fallback keyword-based routing (from original router.py)."""
    TRAVEL_KW = {"flight", "flights", "fly", "fare", "airport", "book", "airline"}
    WEATHER_KW = {"weather", "rain", "temperature", "forecast", "sunny", "snow"}

    t = text.lower()
    if any(k in t for k in TRAVEL_KW):
        return "TRAVEL"
    if any(k in t for k in WEATHER_KW):
        return "WEATHER"
    if any(k in t for k in {"hi", "hello", "hey", "thanks"}):
        return "SMALLTALK"
    return "OTHER"


@traceable(name="extract_slots_node")
def extract_slots_node(state: ConversationState) -> ConversationState:
    """
    Extract slots from user message based on intent.

    Uses existing heuristic extraction (fast and deterministic for PoC).
    """
    intent = state["intent"]
    last_message = state["messages"][-1].content if state["messages"] else ""

    slots_dict = {}

    if intent == "WEATHER":
        # Use existing heuristic extraction
        slots = extract_structured(EXTRACT_WEATHER, WeatherSlots, last_message)
        slots_dict = {
            "location": slots.location,
            "date": slots.date,
        }

    elif intent == "TRAVEL":
        # Use existing heuristic extraction
        slots = extract_structured(EXTRACT_TRAVEL, TravelSlots, last_message)
        slots_dict = {
            "origin": slots.origin,
            "destination": slots.destination,
            "depart_date": slots.depart_date,
            "return_date": slots.return_date,
            "pax_adults": slots.pax_adults,
            "cabin": slots.cabin,
        }

    return {
        "slots": slots_dict,
    }


@traceable(name="validate_slots_node")
def validate_slots_node(state: ConversationState) -> ConversationState:
    """
    Validate extracted slots and identify missing/ambiguous ones.

    Uses existing validators for date normalization, location validation, etc.
    """
    intent = state["intent"]
    slots = state["slots"]
    missing = []
    ambiguities = []

    if intent == "WEATHER":
        # Validate location
        loc = slots.get("location")
        if not loc:
            missing.append("location")

        # Validate date
        d, err_d = normalise_date(slots.get("date"), today=date.today())
        if err_d == "ambiguous-relative":
            ambiguities.append("date")
        slots["date"] = d

        # Determine next action
        ask_slot = next_missing(missing or ambiguities, WEATHER_PRIORITY)
        next_action = "ask_question" if ask_slot else "call_tool"

    elif intent == "TRAVEL":
        # Validate origin/destination
        origin, _ = normalise_iata_or_city(slots.get("origin"))
        dest, _ = normalise_iata_or_city(slots.get("destination"))
        dep, err_dep = normalise_date(slots.get("depart_date"))
        pax, err_pax = normalise_pax(slots.get("pax_adults"))

        if not origin:
            missing.append("origin")
        if not dest:
            missing.append("destination")
        if dep is None:
            missing.append("depart_date")
        if pax is None:
            missing.append("pax_adults")
        if err_dep == "ambiguous-relative":
            ambiguities.append("depart_date")

        # Update normalized values
        slots["origin"] = origin
        slots["destination"] = dest
        slots["depart_date"] = dep
        slots["pax_adults"] = pax

        # Determine next action
        ask_slot = next_missing(missing or ambiguities, TRAVEL_PRIORITY)
        next_action = "ask_question" if ask_slot else "call_tool"

    else:
        # SMALLTALK or OTHER
        next_action = "respond"

    return {
        "slots": slots,
        "missing_slots": missing or ambiguities,
        "next_action": next_action,
    }


@traceable(name="ask_question_node")
def ask_question_node(state: ConversationState) -> ConversationState:
    """
    Generate a clarifying question for missing slots.

    Uses existing question generation from ask_policy.py.
    """
    intent = state["intent"]
    missing_slots = state["missing_slots"]

    if not missing_slots:
        question = "I need more information to help you."
    else:
        ask_slot = missing_slots[0]  # Already prioritized by validate_slots

        if intent == "WEATHER":
            question = weather_question(ask_slot)
        elif intent == "TRAVEL":
            question = travel_question(ask_slot)
        else:
            question = "Could you clarify that detail, please?"

    return {
        "final_response": question,
    }


@traceable(name="call_tool_node")
async def call_tool_node(state: ConversationState) -> ConversationState:
    """
    Execute tool with validated slots.

    Currently only weather tool is implemented. Travel is stubbed.
    """
    intent = state["intent"]
    slots = state["slots"]
    session_id = state["session_id"]

    if intent == "WEATHER":
        # Call weather tool
        try:
            report = await call_tool(
                "weather.get",
                {"location": slots["location"], "date": slots["date"]},
                ToolContext(session_id=session_id),
            )
            response = (
                f"{report.location_label} on {report.date}: "
                f"{report.summary}, {report.temp_c:.0f}°C."
            )
        except Exception as e:
            response = f"Sorry, I couldn't fetch the weather: {str(e)}"

    elif intent == "TRAVEL":
        # Stub response for travel
        origin = slots["origin"]
        dest = slots["destination"]
        dep = slots["depart_date"]
        pax = slots["pax_adults"]
        response = f"Got it. {origin} → {dest} on {dep} for {pax} adult(s)."

    else:
        response = "I'm not sure how to help with that."

    return {
        "final_response": response,
    }


@traceable(name="generate_response_node")
def generate_response_node(state: ConversationState) -> ConversationState:
    """
    Generate final response for SMALLTALK and OTHER intents.
    """
    intent = state["intent"]

    if intent == "SMALLTALK":
        response = "Hello! How can I help you today? I can assist with travel or weather."
    elif intent == "OTHER":
        response = "Would you like help with travel or weather?"
    else:
        response = "I'm here to help! What would you like to know?"

    return {
        "final_response": response,
    }


# Conditional routing functions for graph edges


def should_extract_slots(state: ConversationState) -> str:
    """
    Route to slot extraction if intent requires it.
    Otherwise skip to generate_response.
    """
    intent = state.get("intent")
    if intent in ["WEATHER", "TRAVEL"]:
        return "extract_slots"
    return "generate_response"


def should_validate_or_respond(state: ConversationState) -> str:
    """Route after extraction - always validate for WEATHER/TRAVEL."""
    return "validate_slots"


def route_after_validation(state: ConversationState) -> str:
    """
    Route based on next_action determined by validation.

    Options: ask_question, call_tool, respond
    """
    next_action = state.get("next_action", "respond")
    if next_action == "ask_question":
        return "ask_question"
    elif next_action == "call_tool":
        return "call_tool"
    return "generate_response"
