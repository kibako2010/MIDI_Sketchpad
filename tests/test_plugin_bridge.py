import json
import subprocess
import sys
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "plugin_bridge.py"


def _run_bridge(tmp_path: Path, request_payload: dict) -> dict:
    req_path = tmp_path / "request.json"
    res_path = tmp_path / "response.json"
    req_path.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    proc = subprocess.run(
        [sys.executable, str(BRIDGE), "--request", str(req_path), "--response", str(res_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"bridge exited {proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert res_path.exists(), "response.json was not created"
    return json.loads(res_path.read_text(encoding="utf-8"))


def _all_tracks(enabled: bool = True) -> dict:
    return {
        "drums_bodhran": {"enabled": enabled, "volume_db": 0.0},
        "bass": {"enabled": enabled, "volume_db": 0.0},
        "guitar": {"enabled": enabled, "volume_db": 0.0},
        "fiddle": {"enabled": enabled, "volume_db": 0.0},
        "whistle": {"enabled": enabled, "volume_db": 0.0},
        "pad": {"enabled": enabled, "volume_db": 0.0},
        "chord_track": {"enabled": enabled, "volume_db": 0.0},
    }


def test_plugin_bridge_test_backend(tmp_path):
    response = _run_bridge(tmp_path, {"version": 1, "command": "test_backend"})
    assert response["ok"] is True
    assert response["command"] == "test_backend"
    assert "python_version" in response


def test_plugin_bridge_generate_all_tracks(tmp_path):
    out_dir = tmp_path / "out"
    request = {
        "version": 1,
        "command": "generate",
        "chords": "Am | F | C | G",
        "prompt": "6/8 Anime Irish, energetic, bright",
        "bars": 4,
        "bpm": 120,
        "time_sig": [6, 8],
        "seed": 12345,
        "humanize": 60,
        "output_dir": str(out_dir),
        "create_timestamp_folder": False,
        "merge": True,
        "use_llm": False,
        "tracks": _all_tracks(True),
        "target": "all",
    }

    response = _run_bridge(tmp_path, request)

    assert response["ok"] is True
    produced = response["files"]
    for key in ["Drums", "Percussion", "Bass", "Guitar", "Fiddle", "Whistle", "Pad", "ChordTrack", "All_Parts"]:
        assert key in produced, f"missing output key: {key}"
        assert Path(produced[key]).exists(), f"missing file: {produced[key]}"

    session_path = Path(response["session"])
    assert session_path.exists()

    session = json.loads(session_path.read_text(encoding="utf-8"))
    assert session["key"] == "A"
    assert session["scale"] == "natural_minor"

    drums_mid = mido.MidiFile(produced["Drums"])
    total_ticks = int(480 * 6 * 4 / 8) * 4
    for tr in drums_mid.tracks:
        abs_tick = 0
        for msg in tr:
            abs_tick += msg.time
            if msg.type in ("note_on", "note_off"):
                assert abs_tick <= total_ticks


def test_plugin_bridge_generate_bass_only(tmp_path):
    out_dir = tmp_path / "out_bass"
    tracks = _all_tracks(False)
    tracks["bass"] = {"enabled": True, "volume_db": 0.0}

    request = {
        "version": 1,
        "command": "generate",
        "chords": "Am | F | C | G",
        "prompt": "anime irish",
        "bars": 4,
        "bpm": 120,
        "time_sig": [4, 4],
        "seed": 99,
        "humanize": 60,
        "output_dir": str(out_dir),
        "create_timestamp_folder": False,
        "merge": False,
        "use_llm": False,
        "tracks": tracks,
    }

    response = _run_bridge(tmp_path, request)

    assert response["ok"] is True
    bass_path = out_dir / "Bass.mid"
    drums_path = out_dir / "Drums.mid"
    assert bass_path.exists()
    assert not drums_path.exists()


def test_plugin_bridge_generate_chords(tmp_path):
    request = {
        "version": 1,
        "command": "generate_chords",
        "prompt": "アニメ風アイリッシュ。明るく疾走感。",
        "bars": 4,
        "seed": 777,
        "use_llm": False,
    }
    response = _run_bridge(tmp_path, request)

    assert response["ok"] is True
    assert response["command"] == "generate_chords"
    assert isinstance(response["chords"], list)
    assert len(response["chords"]) == 4
    assert isinstance(response["chords_text"], str)
    assert "|" in response["chords_text"]


def test_plugin_bridge_generate_respects_key_scale_override(tmp_path):
    out_dir = tmp_path / "out_override"
    request = {
        "version": 1,
        "command": "generate",
        "chords": "Am | F | C | G",
        "prompt": "anime irish",
        "bars": 4,
        "bpm": 120,
        "time_sig": [6, 8],
        "seed": 123,
        "humanize": 60,
        "output_dir": str(out_dir),
        "create_timestamp_folder": False,
        "merge": False,
        "use_llm": False,
        "key": "A",
        "scale": "natural_minor",
        "tracks": _all_tracks(False) | {"fiddle": {"enabled": True, "volume_db": 0.0}},
    }

    response = _run_bridge(tmp_path, request)
    assert response["ok"] is True
    assert response["key"] == "A"
    assert response["scale"] == "natural_minor"

    session = json.loads(Path(response["session"]).read_text(encoding="utf-8"))
    assert session["chords"] == ["Am", "F", "C", "G"]
    assert session["key"] == "A"
    assert session["scale"] == "natural_minor"


def test_plugin_bridge_generate_ignores_caret_tokens_in_session_chords(tmp_path):
    out_dir = tmp_path / "out_caret"
    request = {
        "version": 1,
        "command": "generate",
        "chords": "Am ^| F ^| C ^| G",
        "prompt": "anime irish",
        "bars": 4,
        "bpm": 120,
        "time_sig": [6, 8],
        "seed": 222,
        "humanize": 60,
        "output_dir": str(out_dir),
        "create_timestamp_folder": False,
        "merge": False,
        "use_llm": False,
        "tracks": _all_tracks(False) | {"fiddle": {"enabled": True, "volume_db": 0.0}},
    }

    response = _run_bridge(tmp_path, request)
    assert response["ok"] is True

    session = json.loads(Path(response["session"]).read_text(encoding="utf-8"))
    assert "^" not in session["chords"]
    assert session["chords"] == ["Am", "Am", "F", "F", "C", "C", "G"]


def test_plugin_bridge_import_midi_chords(tmp_path):
    midi_path = tmp_path / "source.mid"
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    # 4 bars x whole note chord tones
    for note in (60, 64, 67):
        track.append(mido.Message("note_on", note=note, velocity=90, time=0))
    # Keep notes through 4 bars in 4/4 (4*1920 ticks)
    track.append(mido.Message("note_off", note=60, velocity=0, time=7680))
    track.append(mido.Message("note_off", note=64, velocity=0, time=0))
    track.append(mido.Message("note_off", note=67, velocity=0, time=0))
    mid.save(str(midi_path))

    request = {
        "version": 1,
        "command": "import_midi_chords",
        "midi_path": str(midi_path),
        "bars": 4,
    }

    response = _run_bridge(tmp_path, request)
    assert response["ok"] is True
    assert response["command"] == "import_midi_chords"
    assert isinstance(response["chords"], list)
    assert len(response["chords"]) == 4
    assert isinstance(response["chords_text"], str)
