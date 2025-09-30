import anyio
from src.orchestrator.graph import handle_turn

async def collect(stream):
    out = []
    async for tok in stream:
        out.append(tok)
    return out

def test_weather_missing_location_asks_once():
    async def run():
        toks = await collect(handle_turn("s1", "What's the weather?"))
        assert toks[0].startswith("[intent:WEATHER]")
        assert any("Which city" in t for t in toks)
    anyio.run(run)

def test_weather_ok_calls_tool():
    async def run():
        toks = await collect(handle_turn("s1", "weather in Toronto tomorrow"))
        # With current policy 'tomorrow' will be parsed to a date unless you decide to mark it ambiguous.
        # If you prefer to force explicit dates, tighten normalise_date and adjust this assertion.
        assert toks[0].startswith("[intent:WEATHER]")
        assert any("Toronto" in t for t in toks)
    anyio.run(run)
