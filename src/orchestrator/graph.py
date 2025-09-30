from datetime import date
from typing import AsyncIterator

from src.orchestrator.ask_policy import (
    TRAVEL_PRIORITY,
    WEATHER_PRIORITY,
    next_missing,
    travel_question,
    weather_question,
)
from src.orchestrator.extractor import extract_structured
from src.orchestrator.prompts import EXTRACT_TRAVEL, EXTRACT_WEATHER
from src.orchestrator.router import route
from src.orchestrator.validators import normalise_date, normalise_iata_or_city, normalise_pax
from src.schemas.travel import TravelSlots
from src.schemas.weather import WeatherSlots
from src.tools.base import ToolContext
from src.tools.toolkit import call_tool
from src.tools.weather import WeatherReport


async def handle_turn(session_id: str, message: str) -> AsyncIterator[str]:
    r = route(message)
    yield f"[intent:{r.intent}]"

    if r.intent == "WEATHER":
        wslots = extract_structured(EXTRACT_WEATHER, WeatherSlots, message)
        missing = list(wslots.missing)
        ambiguities = list(wslots.ambiguities)

        loc = wslots.location
        d, err_d = normalise_date(wslots.date, today=date.today())
        if err_d == "ambiguous-relative":
            ambiguities.append("date")
        wslots.date = d

        if not loc:
            missing.append("location")

        ask_slot = next_missing(missing or ambiguities, WEATHER_PRIORITY)
        if ask_slot:
            yield weather_question(ask_slot)
            return

        report = await call_tool(
            "weather.get",
            {"location": loc, "date": wslots.date},
            ToolContext(session_id=session_id),
            expected_model=WeatherReport,  # <-- precise return model
        )
        yield f"{report.location_label} on {report.date}: {report.summary}, {report.temp_c:.0f}°C."
        return

    if r.intent == "TRAVEL":
        tslots = extract_structured(EXTRACT_TRAVEL, TravelSlots, message)
        missing = list(tslots.missing)
        ambiguities = list(tslots.ambiguities)

        origin, _ = normalise_iata_or_city(tslots.origin)
        dest, _ = normalise_iata_or_city(tslots.destination)
        dep, err_dep = normalise_date(tslots.depart_date)
        pax, err_pax = normalise_pax(tslots.pax_adults)

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

        ask_slot = next_missing(missing or ambiguities, TRAVEL_PRIORITY)
        if ask_slot:
            yield travel_question(ask_slot)
            return

        yield f"Got it. {origin} → {dest} on {dep} for {pax} adult(s)."
        return

    yield "How can I help you with travel or weather?"
