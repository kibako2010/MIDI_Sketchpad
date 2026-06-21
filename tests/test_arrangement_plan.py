import argparse
import json

import main
from engine.arrangement_plan import (
    ARRANGEMENT_PLAN_VERSION,
    build_arrangement_plan_document,
    build_arrangement_plan_summary,
    load_deterministic_inputs_from_plan_file,
    summarize_arrangement_plan,
    validate_arrangement_plan_summary,
)


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
    assert a["version"] == ARRANGEMENT_PLAN_VERSION
    assert a["storage"] == "summary"
    assert a["signature"] != c["signature"]
    assert a["deterministic_regeneration"]["source"] == ["params", "chords", "bars", "seed"]


def test_arrangement_plan_model_to_dict_contains_structured_preview():
    params = {"parts": {"drums": True, "fiddle": True, "piano": False}}
    chords = ["Dm", "Bb", "F", "C"]

    summary = build_arrangement_plan_summary(params, chords, bars=4, seed=1).to_dict()

    assert summary["version"] == ARRANGEMENT_PLAN_VERSION
    assert summary["enabled_parts"] == ["drums", "fiddle"]
    assert len(summary["bar_preview"]) == 4
    assert summary["bar_preview"][0]["bar"] == 1
    assert summary["bar_preview"][0]["chord"] == "Dm"


def test_arrangement_plan_validation_detects_mismatch():
    params = {"parts": {"drums": True}}
    chords = ["Dm", "Bb"]
    stored = summarize_arrangement_plan(params, chords, bars=4, seed=42)

    ok_result = validate_arrangement_plan_summary(stored, params, chords, bars=4, seed=42)
    bad_result = validate_arrangement_plan_summary(stored, params, chords, bars=4, seed=123)

    assert ok_result["ok"] is True
    assert ok_result["reason"] == "ok"
    assert bad_result["ok"] is False
    assert bad_result["reason"] == "signature_mismatch"
    assert bad_result["expected_signature"] != bad_result["actual_signature"]


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
        save_arrangement_plan=False,
    )

    main.run(args)

    session_path = out_dir / "session.json"
    assert session_path.exists()

    payload = json.loads(session_path.read_text(encoding="utf-8"))
    assert "arrangement_plan" in payload
    assert payload["arrangement_plan"]["version"] == ARRANGEMENT_PLAN_VERSION
    assert payload["arrangement_plan"]["storage"] == "summary"
    assert payload["arrangement_plan_file"] is None


def test_load_deterministic_inputs_from_plan_file(tmp_path):
    params = {"parts": {"drums": True}, "energy": 65}
    chords = ["Dm", "Bb", "F", "C"]
    document = build_arrangement_plan_document(params=params, chords=chords, bars=4, seed=999)

    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_path = session_dir / "session.json"
    session_path.write_text("{}", encoding="utf-8")
    plan_path = session_dir / "arrangement_plan.json"
    plan_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    recovered = load_deterministic_inputs_from_plan_file("arrangement_plan.json", str(session_path))

    assert recovered is not None
    assert recovered["seed"] == 999
    assert recovered["bars"] == 4
    assert recovered["chords"] == chords
    assert recovered["params"]["energy"] == 65


def test_main_optionally_saves_full_arrangement_plan_file(tmp_path):
    out_dir = tmp_path / "out_full"
    args = argparse.Namespace(
        chords="Dm | Bb | F | C",
        midi=None,
        prompt="folk adventure",
        bars=4,
        seed=321,
        output=str(out_dir),
        merge=False,
        no_llm=True,
        generate_chords=False,
        test_llm=False,
        regenerate=None,
        session=None,
        variations=None,
        save_arrangement_plan=True,
    )

    main.run(args)

    session_path = out_dir / "session.json"
    payload = json.loads(session_path.read_text(encoding="utf-8"))

    plan_file = out_dir / "arrangement_plan.json"
    assert plan_file.exists()
    assert payload["arrangement_plan_file"] == str(plan_file)

    plan_payload = json.loads(plan_file.read_text(encoding="utf-8"))
    assert plan_payload["schema"] == "arrangement_plan_document/v0.1"
    assert plan_payload["summary"]["version"] == ARRANGEMENT_PLAN_VERSION
    assert plan_payload["deterministic_inputs"]["seed"] == 321


def test_regenerate_can_recover_inputs_from_arrangement_plan_file(tmp_path):
    source_out = tmp_path / "src"
    generate_args = argparse.Namespace(
        chords="Dm | Bb | F | C",
        midi=None,
        prompt="folk adventure",
        bars=4,
        seed=2024,
        output=str(source_out),
        merge=False,
        no_llm=True,
        generate_chords=False,
        test_llm=False,
        regenerate=None,
        session=None,
        variations=None,
        save_arrangement_plan=True,
    )
    main.run(generate_args)

    session_path = source_out / "session.json"
    payload = json.loads(session_path.read_text(encoding="utf-8"))
    payload.pop("chords", None)
    payload.pop("params", None)
    payload.pop("bars", None)
    session_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    regen_out = tmp_path / "regen"
    regen_args = argparse.Namespace(
        test_llm=False,
        regenerate="Drums",
        session=str(session_path),
        output=str(regen_out),
        seed=3030,
        save_arrangement_plan=False,
    )
    main.run(regen_args)

    regen_session = regen_out / "session_regenerate.json"
    assert regen_session.exists()
    regen_payload = json.loads(regen_session.read_text(encoding="utf-8"))
    assert regen_payload["chords"] == ["Dm", "Bb", "F", "C"]
    assert regen_payload["bars"] == 4
    assert isinstance(regen_payload["params"], dict)
