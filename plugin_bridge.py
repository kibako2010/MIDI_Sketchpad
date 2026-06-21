#!/usr/bin/env python3
"""
plugin_bridge.py

JUCE plugin / Standalone から呼ばれるJSON bridge入口。

Usage:
  python plugin_bridge.py --request request.json --response response.json
"""

import argparse
import json
import math
import os
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List

from chord_generator import generate_chords
from chord_parser import chords_from_text, estimate_key_and_scale, parse_midi_to_chords
from engine.arrangement_plan import summarize_arrangement_plan
from engine.event_safety import clip_events_to_song_bounds
from engine.generation_engine import GenerationEngine
from humanizer import apply_humanize
from midi_renderer import export_merged_file, export_part_files
from prompt_interpreter import interpret_prompt, test_lm_studio_connection

BACKEND_VERSION = "0.1"
ENGINE = GenerationEngine()

DEFAULT_TRACKS: Dict[str, Dict[str, Any]] = {
    "drums_bodhran": {"enabled": True, "volume_db": 0.0},
    "bass": {"enabled": True, "volume_db": 0.0},
    "guitar": {"enabled": True, "volume_db": 0.0},
    "fiddle": {"enabled": True, "volume_db": 0.0},
    "whistle": {"enabled": True, "volume_db": 0.0},
    "pad": {"enabled": True, "volume_db": 0.0},
    "chord_track": {"enabled": True, "volume_db": 0.0},
}

TRACK_TO_PART_FLAGS = {
    "drums_bodhran": ["drums", "percussion"],
    "bass": ["bass"],
    "guitar": ["acoustic_guitar"],
    "fiddle": ["fiddle"],
    "whistle": ["tin_whistle"],
    "pad": ["pad_strings"],
}

TRACK_TO_RENDERED_PARTS = {
    "drums_bodhran": ["Drums", "Percussion"],
    "bass": ["Bass"],
    "guitar": ["Guitar"],
    "fiddle": ["Fiddle"],
    "whistle": ["Whistle"],
    "pad": ["Pad"],
    "chord_track": ["ChordTrack"],
}


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _default_output_dir() -> str:
    return os.path.join(os.path.expanduser("~"), "Documents", "MIDI Sketchpad Output")


def _normalize_tracks(tracks: Dict[str, Any] | None) -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in DEFAULT_TRACKS.items()}
    if not isinstance(tracks, dict):
        return merged

    for track_id, value in tracks.items():
        if track_id not in merged or not isinstance(value, dict):
            continue
        merged[track_id]["enabled"] = bool(value.get("enabled", merged[track_id]["enabled"]))
        try:
            merged[track_id]["volume_db"] = float(value.get("volume_db", merged[track_id]["volume_db"]))
        except (TypeError, ValueError):
            pass
    return merged


def _to_params_parts(tracks: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
    parts = {
        "drums": False,
        "percussion": False,
        "bass": False,
        "acoustic_guitar": False,
        "fiddle": False,
        "tin_whistle": False,
        "pad_strings": False,
        "piano": False,
        "lead_synth": False,
    }

    for track_id, flags in TRACK_TO_PART_FLAGS.items():
        enabled = bool(tracks.get(track_id, {}).get("enabled", False))
        for part_flag in flags:
            parts[part_flag] = enabled

    return parts


def _enabled_rendered_parts(tracks: Dict[str, Dict[str, Any]]) -> set[str]:
    enabled = set()
    for track_id, rendered_parts in TRACK_TO_RENDERED_PARTS.items():
        if bool(tracks.get(track_id, {}).get("enabled", False)):
            enabled.update(rendered_parts)
    return enabled


def _velocity_scale(velocity: int, gain: float) -> int:
    scaled = int(round(velocity * gain))
    return max(1, min(127, scaled))


def _apply_track_volumes(
    events_by_part: Dict[str, List[tuple]],
    tracks: Dict[str, Dict[str, Any]],
) -> Dict[str, List[tuple]]:
    part_to_db: Dict[str, float] = {}
    for track_id, rendered_parts in TRACK_TO_RENDERED_PARTS.items():
        db = float(tracks.get(track_id, {}).get("volume_db", 0.0))
        db = max(-24.0, min(12.0, db))
        for part in rendered_parts:
            part_to_db[part] = db

    out: Dict[str, List[tuple]] = {}
    for part_name, events in events_by_part.items():
        db = part_to_db.get(part_name, 0.0)
        gain = 10 ** (db / 20.0)
        adjusted = []
        for ev in events:
            tick, ch, note, vel, dur = ev
            adjusted.append((tick, ch, note, _velocity_scale(int(vel), gain), dur))
        out[part_name] = adjusted
    return out


def _make_output_dir(base_output_dir: str, create_timestamp_folder: bool, seed: int) -> str:
    if not create_timestamp_folder:
        os.makedirs(base_output_dir, exist_ok=True)
        return base_output_dir

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    final_dir = os.path.join(base_output_dir, f"{stamp}_seed{seed}")
    os.makedirs(final_dir, exist_ok=True)
    return final_dir


def _list_to_part_map(file_paths: List[str]) -> Dict[str, str]:
    result = {}
    for p in file_paths:
        name = os.path.splitext(os.path.basename(p))[0]
        result[name] = p
    return result


def _resolve_key_scale(req: Dict[str, Any], chords: List[str]) -> tuple[str, str]:
    estimated_key, estimated_scale = estimate_key_and_scale(chords)

    key_override = req.get("key")
    scale_override = req.get("scale")

    key = str(key_override).strip() if key_override is not None and str(key_override).strip() else estimated_key
    scale = str(scale_override).strip() if scale_override is not None and str(scale_override).strip() else estimated_scale
    return key, scale


def _handle_generate(req: Dict[str, Any]) -> Dict[str, Any]:
    chords_text = str(req.get("chords", ""))
    chords = chords_from_text(chords_text)
    if not chords:
        raise ValueError("No valid chords found in request.chords")

    prompt = str(req.get("prompt", ""))
    bars = int(req.get("bars", len(chords)))
    seed = int(req.get("seed", 42))
    bpm = float(req.get("bpm", 120))
    time_sig = req.get("time_sig", [6, 8])
    if not isinstance(time_sig, list) or len(time_sig) != 2:
        time_sig = [6, 8]
    time_sig_tuple = (int(time_sig[0]), int(time_sig[1]))

    humanize = int(req.get("humanize", 70))
    merge = bool(req.get("merge", True))
    use_llm = bool(req.get("use_llm", True))
    tracks = _normalize_tracks(req.get("tracks"))

    base_output_dir = str(req.get("output_dir") or _default_output_dir())
    create_timestamp_folder = bool(req.get("create_timestamp_folder", True))
    out_dir = _make_output_dir(base_output_dir, create_timestamp_folder, seed)

    params = interpret_prompt(prompt, use_llm=use_llm)
    params["humanize"] = max(0, min(100, humanize))
    params["parts"] = _to_params_parts(tracks)
    params["parts"]["piano"] = False
    params["parts"]["lead_synth"] = False

    key, scale = _resolve_key_scale(req, chords)

    generators = ENGINE.build_generators(
        chords=chords,
        key=key,
        scale=scale,
        params=params,
        bars=bars,
        ticks_per_beat=480,
        time_sig=time_sig_tuple,
        seed=seed,
    )

    all_events: Dict[str, List[tuple]] = {}
    for part_name, gen in generators.items():
        events = gen.generate()
        if params.get("post_humanize", False):
            events = apply_humanize(events, params, seed=seed)
        all_events[part_name] = events

    all_events = clip_events_to_song_bounds(
        all_events,
        bars=bars,
        ticks_per_beat=480,
        time_sig=time_sig_tuple,
    )

    enabled_parts = _enabled_rendered_parts(tracks)
    filtered_events = {name: evs for name, evs in all_events.items() if name in enabled_parts}
    scaled_events = _apply_track_volumes(filtered_events, tracks)

    written = export_part_files(
        scaled_events,
        out_dir,
        bpm=bpm,
        ticks_per_beat=480,
        time_sig=time_sig_tuple,
    )

    merged_path = None
    if merge:
        merged_path = os.path.join(out_dir, "All_Parts.mid")
        export_merged_file(
            scaled_events,
            merged_path,
            bpm=bpm,
            ticks_per_beat=480,
            time_sig=time_sig_tuple,
        )

    session_payload = {
        "mode": "plugin_generate",
        "plugin_version": BACKEND_VERSION,
        "prompt": prompt,
        "chords": chords,
        "key": key,
        "scale": scale,
        "bpm": bpm,
        "time_sig": list(time_sig_tuple),
        "bars": bars,
        "seed": seed,
        "humanize": humanize,
        "params": params,
        "tracks": tracks,
        "arrangement_plan": {"summary": summarize_arrangement_plan(params, chords, bars, seed)},
        "part_files": written,
        "merged_file": merged_path,
    }
    session_path = os.path.join(out_dir, "session.json")
    _write_json(session_path, session_payload)

    files = _list_to_part_map(written)
    if merged_path:
        files["All_Parts"] = merged_path

    return {
        "ok": True,
        "command": "generate",
        "message": "Generated successfully",
        "output_dir": out_dir,
        "files": files,
        "session": session_path,
        "seed": seed,
        "bars": bars,
        "bpm": bpm,
        "time_sig": list(time_sig_tuple),
        "key": key,
        "scale": scale,
    }


def _handle_generate_chords(req: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(req.get("prompt", ""))
    bars = int(req.get("bars", 8))
    seed = int(req.get("seed", 42))
    use_llm = bool(req.get("use_llm", True))

    params = interpret_prompt(prompt, use_llm=use_llm)
    result = generate_chords(params=params, bars=bars, seed=seed, use_llm=use_llm)
    chords = result.get("chords", [])

    return {
        "ok": True,
        "command": "generate_chords",
        "chords": chords,
        "chords_text": " | ".join(chords),
        "key": result.get("key", "C"),
        "scale": result.get("scale", "major"),
    }


def _handle_import_midi_chords(req: Dict[str, Any]) -> Dict[str, Any]:
    midi_path = str(req.get("midi_path", ""))
    if not midi_path:
        raise ValueError("midi_path is required")
    if not os.path.exists(midi_path):
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    bars = int(req.get("bars", 8))
    chords = parse_midi_to_chords(midi_path, bars=bars)
    key, scale = estimate_key_and_scale(chords)

    return {
        "ok": True,
        "command": "import_midi_chords",
        "chords": chords,
        "chords_text": " | ".join(chords),
        "key": key,
        "scale": scale,
    }


def _handle_test_lm_studio(_: Dict[str, Any]) -> Dict[str, Any]:
    result = test_lm_studio_connection()
    if result.get("ok"):
        return {
            "ok": True,
            "command": "test_lm_studio",
            "connected": True,
            "message": "LM Studio connected",
        }

    return {
        "ok": False,
        "command": "test_lm_studio",
        "connected": False,
        "error": "LM Studio connection failed",
        "detail": str(result.get("error", "Unknown error")),
    }


def _handle_test_backend(_: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "command": "test_backend",
        "message": "Python backend is available",
        "python_version": sys.version.split()[0],
        "backend_version": BACKEND_VERSION,
    }


def dispatch(request: Dict[str, Any]) -> Dict[str, Any]:
    command = request.get("command")
    if not command:
        raise ValueError("request.command is required")

    if command == "generate":
        return _handle_generate(request)
    if command == "generate_chords":
        return _handle_generate_chords(request)
    if command == "import_midi_chords":
        return _handle_import_midi_chords(request)
    if command == "test_lm_studio":
        return _handle_test_lm_studio(request)
    if command == "test_backend":
        return _handle_test_backend(request)

    raise ValueError(f"Unsupported command: {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="MIDI Sketchpad plugin bridge")
    parser.add_argument("--request", required=True, help="Request JSON path")
    parser.add_argument("--response", required=True, help="Response JSON path")
    args = parser.parse_args()

    command = "unknown"
    try:
        request = _read_json(args.request)
        command = str(request.get("command", "unknown"))
        response = dispatch(request)
    except Exception as exc:
        response = {
            "ok": False,
            "command": command,
            "error": "Generation failed",
            "detail": f"{exc}\n{traceback.format_exc()}",
        }

    _write_json(args.response, response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
