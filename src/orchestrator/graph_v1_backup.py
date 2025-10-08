import asyncio
from typing import AsyncIterator
from datetime import date
from src.core.tracing import traceable

from src.orchestrator.router import route
from src.orchestrator.prompts import EXTRACT_WEATHER, EXTRACT_TRAVEL
from src.orchestrator.extractor import extract_structured
from src.orchestrator.validators import normalise_date, normalise_iata_or_city, normalise_pax
from src.orchestrator.ask_policy import (
    next_missing, TRAVEL_PRIORITY, WEATHER_PRIORITY, travel_question, weather_question
)
from src.schemas.weather import WeatherSlots
from src.schemas.travel import TravelSlots, REQUIRED_ONE_WAY
from src.tools.toolkit import call_tool
from src.tools.base import ToolContext

@traceable(name="handle_turn")
async def handle_turn(session_id: str, message: str) -> AsyncIterator[str]:
    """
    Minimal policy:
    - Route intent
    - Extract slots for that intent
    - Validate & compute missing
    - If missing -> ask ONE question (end turn)
    - Else -> call tool (weather) or echo (for travel stub)
    """
    r = route(message)   # child run (router is also traceable below)
    yield f"[intent:{r.intent}]"

    if r.intent == "WEATHER":
        slots = extract_structured(EXTRACT_WEATHER, WeatherSlots, message)  # traced
        # Validate
        missing = list(slots.missing)
        ambiguities = list(slots.ambiguities)

        loc = slots.location or None
        d, err_d = normalise_date(slots.date, today=date.today())
        if err_d == "ambiguous-relative":
            ambiguities.append("date")
        slots.date = d

        if not loc:
            missing.append("location")

        ask_slot = next_missing(missing or ambiguities, WEATHER_PRIORITY)
        if ask_slot:
            yield weather_question(ask_slot); return

        report = await call_tool("weather.get", {"location": loc, "date": slots.date}, ToolContext(session_id=session_id))  # traced
        yield f"{report.location_label} on {report.date}: {report.summary}, {report.temp_c:.0f}°C."
        return

    elif r.intent == "TRAVEL":
        slots = extract_structured(EXTRACT_TRAVEL, TravelSlots, message)  # traced
        missing = list(slots.missing)
        ambiguities = list(slots.ambiguities)

        origin, _ = normalise_iata_or_city(slots.origin)
        dest, _ = normalise_iata_or_city(slots.destination)
        dep, err_dep = normalise_date(slots.depart_date)
        pax, err_pax = normalise_pax(slots.pax_adults)

        if not origin: missing.append("origin")
        if not dest: missing.append("destination")
        if dep is None: missing.append("depart_date")
        if pax is None: missing.append("pax_adults")
        if err_dep == "ambiguous-relative": ambiguities.append("depart_date")

        ask_slot = next_missing(missing or ambiguities, TRAVEL_PRIORITY)
        if ask_slot:
            yield travel_question(ask_slot); return

        yield f"Got it. {origin} → {dest} on {dep} for {pax} adult(s)."
        return

    else:
        yield "Would you like help with travel or weather?"
        return
