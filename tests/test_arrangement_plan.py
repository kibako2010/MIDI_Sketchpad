import argparse
import json

import main
from engine.arrangement_plan import summarize_arrangement_plan


def test_arrangement_plan_summary_is_deterministic():
    params = {
        "parts": {"drums": True, "bass": True, "piano": False},
        "energy": 70,
        "density": 60,
    }
    chords = ["Dm", "Bb", "F", "C"]

    a = summarize_arrangement_plan(params, chords, bars=8, seed=42)
    b = summarize_arrangement_plan(params, chords, bars=8, seed=42)
    c = summarize_arrangement_plan(params, chords, bars=8, seed=99)

    assert a == b
    assert a["version"] == "0.1"
    assert a["storage"] == "summary"
    assert a["signature"] != c["signature"]
    assert a["deterministic_regeneration"]["source"] == ["params", "chords", "bars", "seed"]


def test_main_saves_arrangement_plan_into_session_json(tmp_path):
    out_dir = tmp_path / "out"
    args = argparse.Namespace(
        chords="Dm | Bb | F | C",
        midi=None,
        prompt="folk adventure",
        bars=4,
        seed=123,
        output=str(out_dir),
        merge=False,
        no_llm=True,
        generate_chords=False,
        test_llm=False,
        regenerate=None,
        session=None,
        variations=None,
    )

    main.run(args)

    session_path = out_dir / "session.json"
    assert session_path.exists()

    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert "arrangement_plan" in payload
    assert payload["arrangement_plan"]["version"] == "0.1"
    assert payload["arrangement_plan"]["storage"] == "summary"
