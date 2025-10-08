"""
Pydantic models for LangGraph state and structured outputs.

These models are used for:
- LLM structured output (intent classification)
- Slot extraction results
- Tool execution results
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# Intent types (reused from router.py but as literal for structured output)
IntentType = Literal["TRAVEL", "WEATHER", "SMALLTALK", "OTHER"]


class IntentClassification(BaseModel):
    """
    Structured output from LLM intent classification.

    Used to replace keyword-based routing with LLM-powered classification.
    """

    intent: IntentType = Field(
        description="The classified intent of the user message"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for the classification (0.0-1.0)",
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen"
    )


class SlotExtractionResult(BaseModel):
    """
    Result from slot extraction (either LLM-based or heuristic).

    Contains extracted slot values and metadata about what's missing.
    """

    slots: dict = Field(
        default_factory=dict,
        description="Dictionary of extracted slot values",
    )
    missing: list[str] = Field(
        default_factory=list,
        description="List of required slots that are missing",
    )
    ambiguities: list[str] = Field(
        default_factory=list,
        description="List of slots that are ambiguous or need clarification",
    )
    extraction_method: Literal["heuristic", "llm"] = Field(
        default="heuristic",
        description="Method used for extraction",
    )


class WeatherSlotExtraction(BaseModel):
    """
    Structured extraction for weather intent.

    Used when LLM-based extraction is enabled.
    """

    location: Optional[str] = Field(
        None,
        description="City or location name for weather query",
    )
    date: Optional[str] = Field(
        None,
        description="Date for weather forecast (ISO format or 'today'/'tomorrow')",
    )


class TravelSlotExtraction(BaseModel):
    """
    Structured extraction for travel intent.

    Used when LLM-based extraction is enabled.
    """

    origin: Optional[str] = Field(
        None,
        description="Origin city or IATA airport code",
    )
    destination: Optional[str] = Field(
        None,
        description="Destination city or IATA airport code",
    )
    depart_date: Optional[str] = Field(
        None,
        description="Departure date (ISO format)",
    )
    return_date: Optional[str] = Field(
        None,
        description="Return date (ISO format), None for one-way",
    )
    pax_adults: Optional[int] = Field(
        None,
        description="Number of adult passengers",
    )
    cabin: Optional[Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]] = Field(
        None,
        description="Cabin class preference",
    )
