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

# コード名 → (ルート, タイプ) のパターンマッチ
CHORD_RE = re.compile(
    r"^([A-G][#b]?)"
    r"(maj7|maj9|min7b5|m7b5|min7|m7|maj|min|m|dim|aug"
    r"|sus2|sus4|add9|7|9|11|13|6|b5)?"
    r"(?:/([A-G][#b]?))?$"
)

# 音符名 → MIDI番号 (オクターブ4基準)
def name_to_midi(name: str, octave: int = 4) -> int:
    base = NOTE_NAMES.index(name.upper().replace("BB", "A#").replace("EB", "D#")
                             .replace("AB", "G#").replace("DB", "C#").replace("GB", "F#"))
    return base + (octave + 1) * 12

def midi_to_name(note: int) -> Tuple[str, int]:
    return NOTE_NAMES[note % 12], (note // 12) - 1

def parse_chord_name(name: str) -> Optional[Tuple[str, str]]:
    """コード文字列 → (root_name, chord_type)"""
    m = CHORD_RE.match(name.strip())
    if not m:
        return None
    root = m.group(1)
    ctype = m.group(2) or "maj"
    ctype = ctype.replace("m7b5", "min7b5").replace("min", "min").replace("m", "min")
    return root, ctype

def chord_name_to_notes(name: str, octave: int = 4) -> List[int]:
    """コード名 → MIDIノート番号リスト"""
    from config import CHORD_INTERVALS
    parsed = parse_chord_name(name)
    if not parsed:
        return []
    root_name, ctype = parsed
    root = name_to_midi(root_name, octave)
    intervals = CHORD_INTERVALS.get(ctype, CHORD_INTERVALS["maj"])
    return [root + i for i in intervals]

def detect_chord_from_notes(notes: List[int]) -> str:
    """同時発音ノートのリストからコード名を推定"""
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
    """
    MIDIファイルを読み込み、小節単位のコード進行リストを返す。
    例: ["Dm", "Bb", "F", "C", "Dm", "Bb", "C", "Dm"]
    """
    mid = mido.MidiFile(midi_path)
    tpb = mid.ticks_per_beat

    # tempo取得（最初のset_tempoメッセージ）
    tempo = 500000  # デフォルト 120 BPM
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                break

    # 拍子取得
    numerator   = 4
    denominator = 4
    for track in mid.tracks:
        for msg in track:
            if msg.type == "time_signature":
                numerator   = msg.numerator
                denominator = msg.denominator
                break

    ticks_per_bar = tpb * numerator * (4 // denominator)

    # 全ノートを絶対tick時刻で収集
    all_notes: List[Tuple[int, int, int]] = []  # (tick_on, tick_off, pitch)
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

    # 小節単位でノートを集計
    chord_list = []
    for bar_idx in range(bars):
        bar_start = bar_idx * ticks_per_bar
        bar_end   = bar_start + ticks_per_bar
        mid_tick  = bar_start + ticks_per_bar // 2
        # 小節中央付近に存在するノートを収集
        bar_notes = [
            pitch for (on, off, pitch) in all_notes
            if on <= mid_tick < off
        ]
        if bar_notes:
            chord_list.append(detect_chord_from_notes(bar_notes))
        else:
            # 小節内に少しでも鳴っているノートを代替使用
            bar_notes_any = [
                pitch for (on, off, pitch) in all_notes
                if on < bar_end and off > bar_start
            ]
            chord_list.append(
                detect_chord_from_notes(bar_notes_any) if bar_notes_any else "?"
            )
    return chord_list

def chords_from_text(text: str) -> List[str]:
    """
    "Dm | Bb | F | C" 形式のテキストからコードリストを生成。
    パイプ・スペース・カンマ・改行で区切る。
    """
    tokens = re.split(r"[\|\s,\n]+", text.strip())
    result = []
    for t in tokens:
        t = t.strip()
        if t and t != "|":
            result.append(t)
    return result

def estimate_key_and_scale(chords: List[str]) -> Tuple[str, str]:
    """
    コード進行からキーとスケールを推定する。
    簡易版：マイナーコードが多ければ natural_minor / dorian を推定。
    """
    minor_count = sum(
        1 for c in chords
        if "m" in c.lower() and "maj" not in c.lower()
    )
    ratio = minor_count / max(len(chords), 1)

    # コードルートの頻度からキーを推定
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
        # マイナー系 → Dorian or Natural Minor
        # Dmの場合はDorianが多い（アイリッシュ）
        scale = "dorian" if ratio < 0.8 else "natural_minor"
    else:
        scale = "major"

    return (most_common_root, scale)