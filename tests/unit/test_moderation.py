from src.safety.moderation import check_message

def test_allows_normal_text():
    assert check_message("check weather in Toronto").allowed

def test_blocks_self_harm():
    r = check_message("I want to kill myself")
    assert not r.allowed and r.category == "self-harm"
