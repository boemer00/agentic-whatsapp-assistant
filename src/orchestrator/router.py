from typing import Literal
from pydantic import BaseModel
from src.core.tracing import traceable

Intent = Literal["TRAVEL", "WEATHER", "SMALLTALK", "OTHER"]

TRAVEL_KW = {"flight", "flights", "fly", "fare", "airport", "book", "airline"}
WEATHER_KW = {"weather", "rain", "temperature", "forecast", "sunny", "snow"}

class Route(BaseModel):
    intent: Intent
    reason: str | None = None

@traceable(name="route")
def route(text: str) -> Route:
    t = text.lower()
    if any(k in t for k in TRAVEL_KW):
        return Route(intent="TRAVEL", reason="matched travel keywords")
    if any(k in t for k in WEATHER_KW):
        return Route(intent="WEATHER", reason="matched weather keywords")
    if any(k in t for k in {"hi", "hello", "hey", "thanks"}):
        return Route(intent="SMALLTALK", reason="greeting/ack")
    return Route(intent="OTHER", reason="default")
