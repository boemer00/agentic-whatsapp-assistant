from typing import List, Literal, Optional

from pydantic import BaseModel

Cabin = Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]


class TravelSlots(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    depart_date: Optional[str] = None
    return_date: Optional[str] = None
    pax_adults: Optional[int] = None
    pax_children: Optional[int] = None
    cabin: Optional[Cabin] = None
    missing: List[str] = []
    ambiguities: List[str] = []


REQUIRED_ONE_WAY = ["origin", "destination", "depart_date", "pax_adults"]
REQUIRED_ROUND = REQUIRED_ONE_WAY + ["return_date"]
