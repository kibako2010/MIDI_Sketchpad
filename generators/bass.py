# generators/bass.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import parse_chord_name
from config import CH_BASS, RANGE, NOTE_NAMES, SCALES


def _root_note(chord_name: str, octave: int = 2) -> int:
    parsed = parse_chord_name(chord_name)
    if not parsed:
        return 38
    root_name, _ = parsed
    name = root_name.replace("b","").replace("#","")
    try:
        idx = NOTE_NAMES.index(name)
        if "b" in root_name: idx = (idx - 1) % 12
        elif "#" in root_name: idx = (idx + 1) % 12
    except ValueError:
        idx = 0
    note = idx + (octave + 1) * 12
    lo, hi = RANGE["bass"]
    while note > hi: note -= 12
    while note < lo: note += 12
    return note

def _fifth_note(root: int) -> int:
    n = root + 7
    lo, hi = RANGE["bass"]
    if n > hi: n -= 12
    return n

def _third_note(chord_name: str, root: int) -> int:
    parsed = parse_chord_name(chord_name)
    if not parsed:
        return root + 3
    _, ctype = parsed
    interval = 3 if "min" in ctype or ctype == "dim" else 4
    n = root + interval
    lo, hi = RANGE["bass"]
    if n > hi: n -= 12
    return n


class BassGenerator(BaseGenerator):

    def generate(self) -> List[MidiEvent]:
        num, den = self.time_sig
        if den == 8 and num in (6, 12):
            return self._bass_6_8()
        return self._bass_4_4()

    def _bass_6_8(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        for bar in range(self.bars):
            bs         = self._bar_start(bar)
            chord      = self._chord_for_bar(bar)
            next_chord = self._chord_for_bar(bar + 1)
            progress   = bar / max(self.bars - 1, 1)

            root  = _root_note(chord,      octave=2)
            fifth = _fifth_note(root)
            third = _third_note(chord, root)
            next_root = _root_note(next_chord, octave=2)

            # ---- セクションで動きを変える ----
            if progress < 0.25:
                # イントロ: シンプルにルート+5度
                pattern = self._pattern_simple(bs, et, root, fifth)

            elif progress < 0.5:
                # Aメロ後半: ルート+5度+アプローチ
                pattern = self._pattern_approach(
                    bs, et, root, fifth, next_root
                )

            elif progress < 0.75:
                # Bメロ: ルート+3度+5度でウォーキング感
                pattern = self._pattern_walking(
                    bs, et, root, third, fifth, next_root
                )

            else:
                # クライマックス: 8分でルートを刻む
                pattern = self._pattern_driving(bs, et, root, fifth)

            events.extend(pattern)

        return events

    def _pattern_simple(self, bs, et, root, fifth) -> List[MidiEvent]:
        """ルート(1拍) + 5度(4拍) のシンプルパターン"""
        events = []
        vel1 = self._humanize_velocity(92)
        vel2 = self._humanize_velocity(78)
        events.append((self._humanize_timing(bs),          CH_BASS, root,  vel1, et*2-10))
        events.append((self._humanize_timing(bs + et*3),   CH_BASS, fifth, vel2, et*2-10))
        return events

    def _pattern_approach(self, bs, et, root, fifth, next_root) -> List[MidiEvent]:
        """ルート+5度+次コードへのアプローチ音"""
        events = []
        approach = next_root - 1 if self.rng.random() < 0.5 else next_root - 2
        lo, hi   = RANGE["bass"]
        approach = max(lo, min(hi, approach))
        events.append((self._humanize_timing(bs),          CH_BASS, root,     self._humanize_velocity(92), et*2-10))
        events.append((self._humanize_timing(bs + et*3),   CH_BASS, fifth,    self._humanize_velocity(78), et*1-10))
        events.append((self._humanize_timing(bs + et*5),   CH_BASS, approach, self._humanize_velocity(68), et  -10))
        return events

    def _pattern_walking(self, bs, et, root, third, fifth, next_root) -> List[MidiEvent]:
        """ウォーキングベース: ルート→3度→5度→アプローチ"""
        events  = []
        approach = next_root - 1
        lo, hi   = RANGE["bass"]
        approach = max(lo, min(hi, approach))
        notes = [root, third, fifth, approach]
        vels  = [92, 75, 78, 65]
        beats = [0, 2, 3, 5]
        for note, vel_b, beat in zip(notes, vels, beats):
            tick = bs + beat * et
            events.append((self._humanize_timing(tick), CH_BASS,
                           note, self._humanize_velocity(vel_b), et*2-10))
        return events

    def _pattern_driving(self, bs, et, root, fifth) -> List[MidiEvent]:
        """クライマックス: 8分音符で力強く刻む"""
        events = []
        pattern_notes = [root, root, fifth, root, root, root]
        pattern_vels  = [95,   80,   75,    88,   80,   85  ]
        for i, (note, vel_b) in enumerate(zip(pattern_notes, pattern_vels)):
            tick = bs + i * et
            events.append((self._humanize_timing(tick), CH_BASS,
                           note, self._humanize_velocity(vel_b), et-15))
        return events

    def _bass_4_4(self) -> List[MidiEvent]:
        events = []
        et = self._eighth_ticks()
        for bar in range(self.bars):
            bs    = self._bar_start(bar)
            chord = self._chord_for_bar(bar)
            root  = _root_note(chord, octave=2)
            fifth = _fifth_note(root)
            for beat, note, vel_b in [(0, root, 92), (4, root, 85),
                                       (2, fifth, 75), (6, fifth, 70)]:
                tick = bs + beat * et
                events.append((self._humanize_timing(tick), CH_BASS,
                               note, self._humanize_velocity(vel_b), et*2-10))
        return events
