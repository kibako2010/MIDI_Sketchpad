# chord_parser.py
"""
MIDIファイルからコード進行を読み取るモジュール。
同時発音ノートをコードとして認識し、小節単位で整理する。
"""

import re
from typing import List, Tuple, Optional
import mido

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

CHORD_RE = re.compile(
    r"^([A-G][#b]?)"
    r"(maj9|maj7|min7b5|m7b5|min7|min6|maj|min|m7|m|dim|aug"
    r"|sus2|sus4|add9|7|9|11|13|6|b5)?"
    r"(?:/([A-G][#b]?))?$"
)


def _normalize_chord_type(raw: str) -> str:
    if not raw:
        return "maj"
    mapping = {
        "m": "min",
        "m7": "min7",
        "m7b5": "min7b5",
        "min": "min",
        "min7": "min7",
        "min6": "min6",
        "maj": "maj",
        "maj7": "maj7",
        "maj9": "maj9",
    }
    return mapping.get(raw, raw)


def name_to_midi(name: str, octave: int = 4) -> int:
    base = NOTE_NAMES.index(name.upper().replace("BB", "A#").replace("EB", "D#")
                             .replace("AB", "G#").replace("DB", "C#").replace("GB", "F#"))
    return base + (octave + 1) * 12


def midi_to_name(note: int) -> Tuple[str, int]:
    return NOTE_NAMES[note % 12], (note // 12) - 1


def parse_chord_name(name: str) -> Optional[Tuple[str, str]]:
    m = CHORD_RE.match(name.strip())
    if not m:
        return None
    root = m.group(1)
    ctype = _normalize_chord_type(m.group(2) or "maj")
    return root, ctype


def chord_name_to_notes(name: str, octave: int = 4) -> List[int]:
    from config import CHORD_INTERVALS
    parsed = parse_chord_name(name)
    if not parsed:
        return []
    root_name, ctype = parsed
    root = name_to_midi(root_name, octave)
    intervals = CHORD_INTERVALS.get(ctype, CHORD_INTERVALS["maj"])
    return [root + i for i in intervals]


def detect_chord_from_notes(notes: List[int]) -> str:
    from config import CHORD_INTERVALS
    if not notes:
        return "?"
    pcs = sorted(set(n % 12 for n in notes))
    best_name = "?"
    best_score = -1
    for root_pc in pcs:
        root_name = NOTE_NAMES[root_pc]
        for ctype, intervals in CHORD_INTERVALS.items():
            chord_pcs = sorted(set((root_pc + i) % 12 for i in intervals))
            match = sum(1 for pc in chord_pcs if pc in pcs)
            score = match / max(len(chord_pcs), len(pcs))
            if score > best_score:
                best_score = score
                best_name = f"{root_name}{'' if ctype == 'maj' else ctype}"
    return best_name


def parse_midi_to_chords(midi_path: str, bars: int = 8) -> List[str]:
    mid = mido.MidiFile(midi_path)
    tpb = mid.ticks_per_beat

    numerator = 4
    denominator = 4
    for track in mid.tracks:
        for msg in track:
            if msg.type == "time_signature":
                numerator = msg.numerator
                denominator = msg.denominator
                break

    # 6/8でも正しく計算（整数除算バグ修正）
    ticks_per_bar = int(tpb * numerator * 4 / denominator)

    all_notes: List[Tuple[int, int, int]] = []
    for track in mid.tracks:
        abs_tick = 0
        active: dict = {}
        for msg in track:
            abs_tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = abs_tick
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    all_notes.append((active.pop(key), abs_tick, msg.note))

    if not all_notes:
        return []

    chord_list = []
    for bar_idx in range(bars):
        bar_start = bar_idx * ticks_per_bar
        bar_end = bar_start + ticks_per_bar
        mid_tick = bar_start + ticks_per_bar // 2
        bar_notes = [pitch for (on, off, pitch) in all_notes if on <= mid_tick < off]
        if bar_notes:
            chord_list.append(detect_chord_from_notes(bar_notes))
        else:
            bar_notes_any = [pitch for (on, off, pitch) in all_notes if on < bar_end and off > bar_start]
            chord_list.append(detect_chord_from_notes(bar_notes_any) if bar_notes_any else "?")
    return chord_list


def chords_from_text(text: str) -> List[str]:
    tokens = re.split(r"[\|\s,\n]+", text.strip())
    return [t.strip() for t in tokens if t.strip() and t.strip() != "|"]


def estimate_key_and_scale(chords: List[str]) -> Tuple[str, str]:
    minor_count = sum(1 for c in chords if "m" in c.lower() and "maj" not in c.lower())
    ratio = minor_count / max(len(chords), 1)

    from collections import Counter
    roots = []
    for c in chords:
        parsed = parse_chord_name(c)
        if parsed:
            roots.append(parsed[0])
    if not roots:
        return ("C", "major")

    most_common_root = Counter(roots).most_common(1)[0][0]
    if ratio >= 0.5:
        scale = "dorian" if ratio < 0.8 else "natural_minor"
    else:
        scale = "major"

    return (most_common_root, scale)
