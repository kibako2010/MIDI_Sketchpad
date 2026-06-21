import os
import mido

from midi_renderer import export_part_files, export_merged_from_part_midis
from engine.session_utils import resolve_part_file_map


def test_export_merged_from_part_midis_rebuilds_full_merge(tmp_path):
    out = tmp_path / "src"
    out.mkdir(parents=True, exist_ok=True)

    events = {
        "Bass": [(0, 1, 40, 90, 240)],
        "Guitar": [(0, 2, 52, 80, 240)],
    }
    files = export_part_files(events, str(out), bpm=120, ticks_per_beat=480, time_sig=(4, 4))
    file_map = {os.path.splitext(os.path.basename(p))[0]: p for p in files}

    merged_path = tmp_path / "All_Parts.mid"
    export_merged_from_part_midis(file_map, str(merged_path), bpm=120, ticks_per_beat=480, time_sig=(4, 4))

    mid = mido.MidiFile(str(merged_path))
    assert len(mid.tracks) >= 3  # tempo + 2 parts


def test_resolve_part_file_map_handles_relative_paths(tmp_path):
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True, exist_ok=True)

    bass = session_dir / "Bass.mid"
    bass.write_bytes(b"dummy")

    session_path = session_dir / "session.json"
    session_path.write_text("{}", encoding="utf-8")

    resolved = resolve_part_file_map(["Bass.mid"], str(session_path))
    assert "Bass" in resolved
    assert resolved["Bass"].endswith("Bass.mid")
