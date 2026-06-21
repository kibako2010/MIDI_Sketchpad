# generators/piano.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import chord_name_to_notes
from config import CH_PIANO, RANGE


class PianoGenerator(BaseGenerator):
    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        lo, hi = RANGE["piano"]

        for bar in range(self.bars):
            chord = self._chord_for_bar(bar)
            bs = self._bar_start(bar)
            notes = [n for n in chord_name_to_notes(chord, octave=4) if lo <= n <= hi]
            if not notes:
                continue

            if self.density > 0.6:
                # comping
                for step in [0, 2, 4]:
                    tick = bs + step * et
                    for note in notes:
                        events.append((self._humanize_timing(tick), CH_PIANO, note, self._humanize_velocity(64), et * 2 - 20))
            else:
                # sustain block
                dur = self.ticks_per_bar - 20
                for note in notes:
                    events.append((bs, CH_PIANO, note, self._humanize_velocity(60), dur))

        return events
