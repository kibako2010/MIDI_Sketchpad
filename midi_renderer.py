# midi_renderer.py
"""
MidiEventリストをMIDIファイルとして書き出すモジュール。
パート別（1ファイル/パート）と全パートマージ（マルチチャンネル）の両方に対応。
"""

import os
from typing import List, Dict
import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

from generators.base import MidiEvent
from model.events import event_to_tuple

# MIDIチャンネル → パート名マッピング
CHANNEL_NAMES = {
    0:  "Piano",
    1:  "Bass",
    2:  "Guitar",
    3:  "Pad",
    4:  "Lead",
    5:  "Fiddle",
    6:  "Whistle",
    7:  "Brass",
    8:  "Percussion",
    9:  "Drums",
    15: "ChordTrack", 
}


def _events_to_track(
    events: List[MidiEvent],
    tempo:  int  = 500000,
    program: int = 0,
    channel: int = 0,
    track_name: str = "Track",
) -> MidiTrack:
    track = MidiTrack()
    track.append(MetaMessage("track_name", name=track_name, time=0))
    # ↓ この行を削除
    # track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    # プログラムチェンジ（ドラムは不要）
    if channel != 9:
        track.append(Message("program_change", channel=channel,
                              program=program, time=0))

    # Note ON/OFF イベントに展開
    raw: List[tuple] = []
    for event in events:
        abs_tick, ch, note, vel, dur = event_to_tuple(event)
        raw.append((abs_tick,       "note_on",  ch, note, vel))
        raw.append((abs_tick + dur, "note_off", ch, note, 0))

    raw.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

    prev_tick = 0
    for item in raw:
        abs_tick, msg_type, ch, note, vel = item
        delta = max(0, abs_tick - prev_tick)
        prev_tick = abs_tick
        track.append(Message(msg_type, channel=ch, note=note,
                              velocity=vel, time=delta))

    track.append(MetaMessage("end_of_track", time=1))
    return track


# ---- パート別プログラム番号 (GM) ----
PART_PROGRAMS = {
    "Piano":      0,    # Acoustic Grand Piano
    "Bass":       32,   # Acoustic Bass
    "Guitar":     25,   # Acoustic Guitar (steel)
    "Pad":        49,   # String Ensemble 1
    "Lead":       80,   # Lead Synth (Square)
    "Fiddle":     40,   # Violin
    "Whistle":    72,   # Flute (Tin Whistleに近い)
    "Brass":      56,   # Trumpet
    "Percussion": 115,  # Woodblock (Bodhrán代替)
    "Drums":      0,    # Drums (ch9固定)
    "ChordTrack": 0,    # ← 追加（Piano音色だが音源割り当て不要）
}


def export_part_files(
    all_events:     Dict[str, List[MidiEvent]],
    output_dir:     str,
    bpm:            float  = 120.0,
    ticks_per_beat: int    = 480,
    time_sig:       tuple  = (6, 8),
) -> List[str]:
    """
    パートごとにMIDIファイルを書き出す。
    Returns: 書き出したファイルパスのリスト
    """
    os.makedirs(output_dir, exist_ok=True)
    tempo   = int(60_000_000 / bpm)
    written = []

    for part_name, events in all_events.items():
        if not events:
            continue
        channel  = _name_to_channel(part_name)
        program  = PART_PROGRAMS.get(part_name, 0)
        track    = _events_to_track(events, tempo, program, channel, part_name)

        mid = MidiFile(type=1, ticks_per_beat=ticks_per_beat)
        # テンポ・拍子トラック
        tempo_track = MidiTrack()
        tempo_track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
        tempo_track.append(MetaMessage(
            "time_signature",
            numerator=time_sig[0], denominator=time_sig[1],
            clocks_per_click=24, notated_32nd_notes_per_beat=8,
            time=0,
        ))
        tempo_track.append(MetaMessage("end_of_track", time=1))
        mid.tracks.append(tempo_track)
        mid.tracks.append(track)

        filename = os.path.join(output_dir, f"{part_name}.mid")
        mid.save(filename)
        written.append(filename)
        print(f"  [OK]{filename}")

    return written


def export_merged_file(
    all_events:     Dict[str, List[MidiEvent]],
    output_path:    str,
    bpm:            float  = 120.0,
    ticks_per_beat: int    = 480,
    time_sig:       tuple  = (6, 8),
) -> str:
    """全パートを1つのマルチトラックMIDIファイルに書き出す"""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    tempo = int(60_000_000 / bpm)

    mid = MidiFile(type=1, ticks_per_beat=ticks_per_beat)

    # テンポトラック
    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("track_name", name="Tempo", time=0))
    tempo_track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    tempo_track.append(MetaMessage(
        "time_signature",
        numerator=time_sig[0], denominator=time_sig[1],
        clocks_per_click=24, notated_32nd_notes_per_beat=8,
        time=0,
    ))
    tempo_track.append(MetaMessage("end_of_track", time=1))
    mid.tracks.append(tempo_track)

    for part_name, events in all_events.items():
        if not events:
            continue
        channel = _name_to_channel(part_name)
        program = PART_PROGRAMS.get(part_name, 0)
        track   = _events_to_track(events, tempo, program, channel, part_name)
        mid.tracks.append(track)

    mid.save(output_path)
    print(f"  [OK] Merged:{output_path}")
    return output_path


def _name_to_channel(name: str) -> int:
    for ch, n in CHANNEL_NAMES.items():
        if n.lower() == name.lower():
            return ch
    return 0


def _extract_performance_track(src_mid: MidiFile) -> MidiTrack | None:
    """Source MIDIから演奏トラックを1本抽出。"""
    if not src_mid.tracks:
        return None

    best_track = None
    best_count = -1
    for tr in src_mid.tracks:
        count = sum(1 for msg in tr if getattr(msg, "type", "") in ("note_on", "note_off"))
        if count > best_count:
            best_count = count
            best_track = tr

    if best_track is None or best_count <= 0:
        return None
    return best_track


def export_merged_from_part_midis(
    part_midi_paths: Dict[str, str],
    output_path: str,
    bpm: float = 120.0,
    ticks_per_beat: int = 480,
    time_sig: tuple = (6, 8),
) -> str:
    """
    既存パートMIDIを直接読み込み、全パート統合MIDIを構築する。
    Regenerate時の「既存 + 再生成」完全merge用。
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    tempo = int(60_000_000 / bpm)

    mid = MidiFile(type=1, ticks_per_beat=ticks_per_beat)

    tempo_track = MidiTrack()
    tempo_track.append(MetaMessage("track_name", name="Tempo", time=0))
    tempo_track.append(MetaMessage("set_tempo", tempo=tempo, time=0))
    tempo_track.append(MetaMessage(
        "time_signature",
        numerator=time_sig[0], denominator=time_sig[1],
        clocks_per_click=24, notated_32nd_notes_per_beat=8,
        time=0,
    ))
    tempo_track.append(MetaMessage("end_of_track", time=1))
    mid.tracks.append(tempo_track)

    for part_name in sorted(part_midi_paths.keys()):
        src_path = part_midi_paths[part_name]
        if not os.path.exists(src_path):
            continue

        src_mid = mido.MidiFile(src_path)
        src_track = _extract_performance_track(src_mid)
        if src_track is None:
            continue

        new_track = MidiTrack()
        new_track.append(MetaMessage("track_name", name=part_name, time=0))
        for msg in src_track:
            if msg.type in ("set_tempo", "time_signature", "track_name"):
                continue
            new_track.append(msg.copy())
        if not new_track or new_track[-1].type != "end_of_track":
            new_track.append(MetaMessage("end_of_track", time=1))

        mid.tracks.append(new_track)

    mid.save(output_path)
    print(f"  [OK] Merged(rebuilt):{output_path}")
    return output_path