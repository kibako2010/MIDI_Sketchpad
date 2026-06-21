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
    chords: List[str] = []

    for raw in tokens:
        token = raw.strip()
        if not token or token == "|":
            continue

        if token == "^":
            if chords:
                chords.append(chords[-1])
            continue

        if parse_chord_name(token) is None:
            continue

        chords.append(token)

    return chords


def _note_name_to_pc(name: str) -> int:
    clean = name.replace("b", "").replace("#", "")
    try:
        pc = NOTE_NAMES.index(clean)
    except ValueError:
        return 0
    if "b" in name:
        pc = (pc - 1) % 12
    elif "#" in name:
        pc = (pc + 1) % 12
    return pc


def estimate_key_and_scale(chords: List[str]) -> Tuple[str, str]:
    from config import CHORD_INTERVALS, SCALES

    parsed_chords = []
    for chord in chords:
        parsed = parse_chord_name(chord)
        if not parsed:
            continue
        root_name, ctype = parsed
        root_pc = _note_name_to_pc(root_name)
        parsed_chords.append((root_pc, ctype))

    if not parsed_chords:
        return ("C", "major")

    first_root = parsed_chords[0][0]
    last_root = parsed_chords[-1][0]

    candidate_scales = ["major", "natural_minor", "dorian"]
    best_score = float("-inf")
    best = (0, "major")

    for key_pc in range(12):
        for scale_name in candidate_scales:
            intervals = SCALES[scale_name]
            scale_pcs = {(key_pc + iv) % 12 for iv in intervals}
            score = 0.0

            has_iv_major = False
            has_bvii_major = False
            has_bvi_major = False

            for root_pc, ctype in parsed_chords:
                chord_intervals = CHORD_INTERVALS.get(ctype, CHORD_INTERVALS["maj"])
                chord_pcs = {(root_pc + iv) % 12 for iv in chord_intervals}
                in_scale = sum(1 for pc in chord_pcs if pc in scale_pcs)
                out_scale = len(chord_pcs) - in_scale

                score += in_scale * 1.4
                score -= out_scale * 1.8

                if root_pc in scale_pcs:
                    score += 0.2
                else:
                    score -= 0.8

                is_minor_quality = ("min" in ctype and "maj" not in ctype)
                is_major_quality = not is_minor_quality

                if root_pc == key_pc:
                    score += 1.5
                    if scale_name == "major":
                        score += 1.2 if is_major_quality else -1.2
                    else:
                        score += 1.2 if is_minor_quality else -1.2

                if root_pc == (key_pc + 5) % 12 and is_major_quality:
                    has_iv_major = True
                if root_pc == (key_pc + 10) % 12 and is_major_quality:
                    has_bvii_major = True
                if root_pc == (key_pc + 8) % 12 and is_major_quality:
                    has_bvi_major = True

            if first_root == key_pc:
                score += 0.8
            if last_root == key_pc:
                score += 1.4
            if first_root == key_pc and last_root == key_pc:
                score += 0.8

            if scale_name == "dorian":
                if has_iv_major:
                    score += 0.9
                if has_bvii_major:
                    score += 0.4
            if scale_name == "natural_minor" and has_bvi_major:
                score += 0.9

            if score > best_score:
                best_score = score
                best = (key_pc, scale_name)

    key_name = NOTE_NAMES[best[0]]
    return key_name, best[1]
