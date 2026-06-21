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
        notes_raw = chord_name_to_notes(chord_name, octave=3)
        lo, hi = RANGE["guitar"]
        notes = sorted([n for n in notes_raw if lo <= n <= hi])
        if not notes:
            return []

        if len(notes) > 4:
            notes = notes[:4]

        events: List[MidiEvent] = []
        strum_delay = int(self.tpb * 0.015)
        dur = int(self._eighth_ticks() * duration_ratio)

        if direction == "up":
            notes = list(reversed(notes))

        for i, note in enumerate(notes):
            strum_tick = tick + i * strum_delay
            vel = self._humanize_velocity(vel_base - i * 3)
            events.append((strum_tick, CH_GUITAR, note, vel, dur))
        return events

    def _guitar_6_8(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        folk_boost = int(self.folk_v * 12)
        rock_boost = int(self.rock_v * 14)

        vel_down = int(78 + self.energy * 22 + folk_boost + rock_boost)
        vel_up = int(52 + self.energy * 16 + folk_boost // 2)

        patterns_dense = [
            (0, "down", 1.0),
            (et, "down", 0.7),
            (et * 2, "up", 0.6),
            (et * 3, "down", 0.9),
            (et * 4, "up", 0.55),
            (et * 5, "down", 0.75),
        ]
        patterns_sparse = [
            (0, "down", 1.0),
            (et * 3, "down", 0.85),
            (et * 5, "up", 0.6),
        ]

        pattern = patterns_dense if self.density > 0.58 else patterns_sparse

        # weirdnessが高いと反復を崩す
        if self.weirdness_v > 0.5:
            pattern = pattern[:-1] + [(et * 5, "up", 0.45)]

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            chord = self._chord_for_bar(bar)
            for offset, direction, vel_factor in pattern:
                tick = bs + offset
                vel_base = int((vel_down if direction == "down" else vel_up) * vel_factor)
                events.extend(self._strum(tick, chord, vel_base, direction))

        return events

    def _guitar_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        patterns = [
            (0, "down", 1.0),
            (et * 2, "down", 0.85),
            (et * 3, "up", 0.65),
            (et * 4, "down", 0.9),
            (et * 6, "down", 0.8),
            (et * 7, "up", 0.6),
        ]
        if self.density < 0.45:
            patterns = [(0, "down", 1.0), (et * 4, "down", 0.85), (et * 7, "up", 0.6)]

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            chord = self._chord_for_bar(bar)
            for offset, direction, vf in patterns:
                tick = bs + offset
                vel = int((74 + self.energy * 20 + self.rock_v * 10) * vf)
                events.extend(self._strum(tick, chord, vel, direction))
        return events
