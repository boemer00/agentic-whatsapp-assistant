from typing import List, Optional

from pydantic import BaseModel


class WeatherSlots(BaseModel):
    location: Optional[str] = None
    date: Optional[str] = None
    missing: List[str] = []
    ambiguities: List[str] = []
