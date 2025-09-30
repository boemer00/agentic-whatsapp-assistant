from src.orchestrator.validators import normalise_date

def test_next_friday_is_ambiguous():
    d, err = normalise_date("next Friday")
    assert d is None and err == "ambiguous-relative"

def test_iso_date_is_ok():
    d, err = normalise_date("2025-10-01")
    assert d == "2025-10-01" and err is None
