from prompt_interpreter import _keyword_fallback
from style_planner import plan_style


def test_keyword_fallback_has_extended_fields():
    params = _keyword_fallback("アニメ風アイリッシュ。フィドルとホイッスル")
    assert "post_humanize" in params
    assert "parts" in params
    assert "piano" in params["parts"]
    assert "lead_synth" in params["parts"]


def test_style_planner_reflects_rock_anime_in_bpm():
    base = {
        "style": "anime_irish",
        "tempo_feel": "fast_6_8",
        "energy": 70,
        "rock": 10,
        "anime": 10,
        "folk": 10,
        "weirdness": 0,
    }
    hot = dict(base)
    hot.update({"rock": 90, "anime": 90, "weirdness": 80})

    p1 = plan_style(base, ["Dm", "Bb", "F", "C"], "D", "dorian")
    p2 = plan_style(hot, ["Dm", "Bb", "F", "C"], "D", "dorian")

    assert p2["bpm"] > p1["bpm"]
