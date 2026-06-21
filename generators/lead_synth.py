# generators/lead_synth.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from config import CH_LEAD, RANGE, SCALES


class LeadSynthGenerator(BaseGenerator):
    def _scale_notes(self):
        root_pc = self._root_pc()
        intervals = SCALES.get(self.scale, SCALES["natural_minor"])
        lo, hi = RANGE["lead"]
        notes = []
        for oct_i in range(4, 8):
            for iv in intervals:
                n = root_pc + iv + oct_i * 12
                if lo <= n <= hi:
                    notes.append(n)
        return sorted(set(notes))

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        notes = self._scale_notes()
        if not notes:
            return events

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            progress = bar / max(1, self.bars - 1)
            active_steps = [0, 2, 4] if self.density > 0.55 else [0, 3]

            for step in active_steps:
                idx = (bar + step) % len(notes)
                note = notes[idx]
                if self.weirdness_v > 0.5 and self.rng.random() < 0.2:
                    note = min(RANGE["lead"][1], note + 1)
                tick = bs + step * et
                dur = et * 2 if progress < 0.7 else et
                vel = self._humanize_velocity(68 + int(self.energy * 18) + int(self.rock_v * 8))
                events.append((self._humanize_timing(tick), CH_LEAD, note, vel, dur))

        return events
