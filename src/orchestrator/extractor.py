import re
from typing import Type, TypeVar

from pydantic import BaseModel
from src.core.tracing import traceable

T = TypeVar("T", bound=BaseModel)


# Very small, deterministic heuristics suitable for a PoC
_DATE_ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_LOC_AFTER_PREP_RE = re.compile(r"\b(?:in|for|at)\s+([A-Za-z][A-Za-z .'\-]{1,40})", re.IGNORECASE)
_STOPWORDS_OR_PUNCT_RE = re.compile(r"[,;.!?\n]|\b(today|tomorrow|next|this|coming|on|at|for)\b", re.IGNORECASE)


def _extract_location(text: str) -> str | None:
    """Grab text after 'in/for/at' and stop at common keywords/punctuation."""
    m = _LOC_AFTER_PREP_RE.search(text)
    if not m:
        return None
    raw = m.group(1).strip()
    # Truncate at stopwords or punctuation
    parts = _STOPWORDS_OR_PUNCT_RE.split(raw, maxsplit=1)
    cleaned = (parts[0] if parts else raw).strip(" ,.!?\"'")
    return cleaned or None


def _extract_date(text: str) -> str | None:
    """Return ISO date if present, else simple keywords 'today'/'tomorrow'."""
    m = _DATE_ISO_RE.search(text)
    if m:
        return m.group(0)
    lower = text.lower()
    if "tomorrow" in lower:
        return "tomorrow"
    if "today" in lower:
        return "today"
    return None

@traceable(name="extract_structured")
def extract_structured(prompt: str, schema: Type[T], context: str) -> T:
    """
    Deterministic extractor for PoC:
    - If the target schema has fields {'location','date'}, extract those heuristically.
    - Otherwise, return empty defaults.
    """
    field_names = set(getattr(schema, "model_fields", {}).keys())
    text = context.strip()

    if {"location", "date"}.issubset(field_names):
        return schema.model_validate(
            {
                "location": _extract_location(text),
                "date": _extract_date(text),
            }
        )

    return schema.model_validate({})  # empty defaults
