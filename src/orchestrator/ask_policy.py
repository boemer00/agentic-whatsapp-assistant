from typing import List

TRAVEL_PRIORITY = ["depart_date", "destination", "origin", "return_date", "pax_adults", "cabin"]
WEATHER_PRIORITY = ["location", "date"]


def next_missing(slots: List[str], priority: List[str]) -> str | None:
    for p in priority:
        if p in slots:
            return p
    return None


def travel_question(slot: str) -> str:
    Q = {
        "depart_date": "What departure date works for you? (YYYY-MM-DD)",
        "destination": "Where are you flying to?",
        "origin": "Where are you flying from?",
        "return_date": "And the return date? (YYYY-MM-DD) If one-way, just say one-way.",
        "pax_adults": "How many adults are travelling?",
        "cabin": "Which cabin do you prefer? Economy, Premium Economy, Business or First?",
    }
    return Q.get(slot, "Could you clarify that detail, please?")


def weather_question(slot: str) -> str:
    Q = {
        "location": "Which city should I check the weather for?",
        "date": "For which date should I check the forecast? (YYYY-MM-DD)",
    }
    return Q.get(slot, "Could you clarify that detail, please?")
