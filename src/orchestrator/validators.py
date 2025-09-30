import re
from datetime import date, datetime
from typing import Optional, Tuple

from dateutil import parser as dparser

IATA_RE = re.compile(r"^[A-Z]{3}$")
RELATIVE_HINTS = re.compile(r"\b(next|this|coming)\b", re.IGNORECASE)


def normalise_date(
    raw: Optional[str], today: Optional[date] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Try to normalise to YYYY-MM-DD.
    If `raw` is None -> (None, None)
    If relative wording like 'next Friday' is present -> (None, "ambiguous-relative")
    If parse fails -> (None, "invalid-date")
    """
    if raw is None:
        return None, None
    if RELATIVE_HINTS.search(raw):
        return None, "ambiguous-relative"
    try:
        dt = dparser.parse(
            raw,
            dayfirst=False,
            yearfirst=True,
            default=datetime.combine(today or date.today(), datetime.min.time()),
        )
        return dt.date().isoformat(), None
    except Exception:
        return None, "invalid-date"


def normalise_iata_or_city(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Accepts 'LHR' or 'London'. For MVP we only check IATA pattern;
    city resolution can be added later (map to IATA).
    """
    if raw is None:
        return None, None
    raw = raw.strip()
    if IATA_RE.match(raw.upper()):
        return raw.upper(), None
    # Defer city resolution -> mark not-iata (still acceptable as city)
    return raw, None


def normalise_pax(n: Optional[int]) -> Tuple[Optional[int], Optional[str]]:
    if n is None:
        return None, None
    if n <= 0:
        return None, "invalid-pax"
    if n > 9:
        return None, "too-many-pax"
    return n, None
