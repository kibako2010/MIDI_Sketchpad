# generators/guitar.py
"""
アコースティックギタージェネレータ。
Anime Irish 6/8: ジャカジャカ系ストロークパターン。
"""

from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import chord_name_to_notes
from config import CH_GUITAR, RANGE


class GuitarGenerator(BaseGenerator):

    def generate(self) -> List[MidiEvent]:
        num, den = self.time_sig
        if den == 8 and num == 6:
            return self._guitar_6_8()
        return self._guitar_4_4()

    def _strum(self, tick: int, chord_name: str, vel_base: int,
               direction: str = "down", duration_ratio: float = 0.8) -> List[MidiEvent]:
        """
        ストロークをシミュレート:
        - Downストローク: 低弦→高弦 (わずかなtick差)
        - Upストローク: 高弦→低弦
        """
        notes_raw = chord_name_to_notes(chord_name, octave=3)
        lo, hi    = RANGE["guitar"]
        notes     = sorted([n for n in notes_raw if lo <= n <= hi])
        if not notes:
            return []

        # ギターらしく3〜4音に限定
        if len(notes) > 4:
            notes = notes[:4]

        events: List[MidiEvent] = []
        strum_delay = int(self.tpb * 0.015)  # ストローク遅延 (約15ms相当)
        dur = int(self._eighth_ticks() * duration_ratio)

        if direction == "up":
            notes = list(reversed(notes))

        for i, note in enumerate(notes):
            strum_tick = tick + i * strum_delay
            vel = self._humanize_velocity(vel_base - i * 3)  # 上の弦は少し弱め
            events.append((strum_tick, CH_GUITAR, note, vel, dur))
        return events

    def _guitar_6_8(self) -> List[MidiEvent]:
        """
        6/8 Strumパターン (代表: D D U D U D)
        位置:  0  1  2  3  4  5 (8分音符)
        方向:  D     U  D  U  D
        """
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        # Folk/Anime比率でベロシティ調整
        vel_down = int(80 + self.energy * 20)
        vel_up   = int(55 + self.energy * 15)

        # パターン定義 (tick_offset, direction, vel_factor)
        patterns_dense = [
            (0,        "down", 1.0),
            (et,       "down", 0.7),
            (et * 2,   "up",   0.6),
            (et * 3,   "down", 0.9),
            (et * 4,   "up",   0.55),
            (et * 5,   "down", 0.75),
        ]
        patterns_sparse = [
            (0,        "down", 1.0),
            (et * 3,   "down", 0.85),
            (et * 5,   "up",   0.6),
        ]

        pattern = patterns_dense if self.density > 0.6 else patterns_sparse

        for bar in range(self.bars):
            bs    = self._bar_start(bar)
            chord = self._chord_for_bar(bar)

            for offset, direction, vel_factor in pattern:
                tick     = bs + offset
                vel_base = int((vel_down if direction == "down" else vel_up) * vel_factor)
                events.extend(self._strum(tick, chord, vel_base, direction))

        return events

    def _guitar_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        patterns = [
            (0,        "down", 1.0),
            (et * 2,   "down", 0.85),
            (et * 3,   "up",   0.65),
            (et * 4,   "down", 0.9),
            (et * 6,   "down", 0.8),
            (et * 7,   "up",   0.6),
        ]
        for bar in range(self.bars):
            bs    = self._bar_start(bar)
            chord = self._chord_for_bar(bar)
            for offset, direction, vf in patterns:
                tick = bs + offset
                vel  = int((75 + self.energy * 20) * vf)
                events.extend(self._strum(tick, chord, vel, direction))
        return events