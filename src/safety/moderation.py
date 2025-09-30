import re

from pydantic import BaseModel


class ModerationResult(BaseModel):
    allowed: bool
    category: str | None = None
    reason: str | None = None

_PATTERNS = {
    "self-harm": re.compile(r"\b(kill myself|suicide|end my life)\b", re.I),
    "violent-threat": re.compile(r"\b(kill|murder|bomb|shoot)\b", re.I),
    "sexual-minor": re.compile(r"\b(child porn|cp|underage sex)\b", re.I),
    "hate": re.compile(r"\b(kill (?:all )?(?:jews|gays|blacks|asians))\b", re.I),
    "illegal": re.compile(r"\b(how to (?:make|build) (?:a bomb|meth)|credit card skimmer)\b", re.I),
}

def check_message(text: str) -> ModerationResult:
    t = text.strip()
    if not t:
        return ModerationResult(allowed=True)
    for cat, rx in _PATTERNS.items():
        if rx.search(t):
            return ModerationResult(allowed=False, category=cat, reason=f"⚠️ matched '{cat}' policy")
    return ModerationResult(allowed=True)
