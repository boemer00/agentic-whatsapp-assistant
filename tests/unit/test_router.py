from src.orchestrator.router import route

def test_route_travel():
    r = route("Find flights from London to Toronto")
    assert r.intent == "TRAVEL"

def test_route_weather():
    r = route("weather in Toronto tomorrow")
    assert r.intent == "WEATHER"

def test_route_smalltalk():
    r = route("hello there")
    assert r.intent == "SMALLTALK"

def test_route_other():
    r = route("explain embeddings vs bm25")
    assert r.intent == "OTHER"
