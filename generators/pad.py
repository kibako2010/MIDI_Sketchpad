# generators/pad.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import chord_name_to_notes
from config import CH_PAD, RANGE


class PadGenerator(BaseGenerator):

    def _get_chord_notes(self, chord_name: str) -> List[int]:
        lo, hi = RANGE["pad"]
        notes = chord_name_to_notes(chord_name, octave=4)
        result = [n for n in notes if lo <= n <= hi]
        if not result:
            result = [n for n in notes]
            while result and result[0] < lo:
                result = [n + 12 for n in result]
        return sorted(result)

    def _add_color(self, notes: List[int]) -> List[int]:
        lo, hi = RANGE["pad"]
        if not notes:
            return notes
        ninth = notes[0] + 14
        if lo <= ninth <= hi and ninth not in notes:
            notes = notes + [ninth]
        return notes

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        climax_start = 0.78 - (self.anime_v * 0.24)

        for bar in range(self.bars):
            chord = self._chord_for_bar(bar)
            progress = bar / max(self.bars - 1, 1)

            if progress < 0.25:
                events.extend(self._sustain(bar, chord, vel_base=42 + int(self.orchestral_v * 8)))
            elif progress < 0.5:
                events.extend(self._sustain(bar, chord, vel_base=54 + int(self.orchestral_v * 8), add_color=True))
            elif progress < max(0.55, climax_start):
                events.extend(self._arpeggio(bar, chord))
            else:
                events.extend(self._climax_pad(bar, chord))

        return events

    def _sustain(self, bar: int, chord_name: str, vel_base: int = 50, add_color: bool = False) -> List[MidiEvent]:
        bs = self._bar_start(bar)
        dur = int(self.ticks_per_bar * 0.95)
        notes = self._get_chord_notes(chord_name)
        if add_color or self.anime_v > 0.65:
            notes = self._add_color(notes)
        events = []
        for note in notes:
            vel = self._humanize_velocity(vel_base)
            events.append((bs, CH_PAD, note, vel, dur))
        return events

    def _arpeggio(self, bar: int, chord_name: str) -> List[MidiEvent]:
        events = []
        et = self._eighth_ticks()
        bs = self._bar_start(bar)
        notes = self._get_chord_notes(chord_name)
        notes = self._add_color(notes)

        # orchestralが高いと音数を増やす
        arp_count = 4 if self.orchestral_v > 0.55 else 3
        arp = notes[:arp_count]

        for i, note in enumerate(arp):
            tick = bs + i * et
            vel = self._humanize_velocity(52 + i * 8 + int(self.orchestral_v * 6))
            events.append((self._humanize_timing(tick), CH_PAD, note, vel, et * 2))

        if notes:
            top = notes[-1]
            tick = bs + len(arp) * et
            dur = self.ticks_per_bar - len(arp) * et - 20
            vel = self._humanize_velocity(64 + int(self.anime_v * 8))
            events.append((tick, CH_PAD, top, vel, max(dur, et)))

        return events

    def _climax_pad(self, bar: int, chord_name: str) -> List[MidiEvent]:
        events = []
        bs = self._bar_start(bar)
        dur = int(self.ticks_per_bar * 0.95)
        notes = self._get_chord_notes(chord_name)
        notes = self._add_color(notes)
        lo, hi = RANGE["pad"]

        spread = 1 if self.orchestral_v > 0.5 else 0
        for note in notes:
            vel = self._humanize_velocity(int(68 + self.energy * 22 + self.anime_v * 8))
            events.append((bs, CH_PAD, note, vel, dur))
            if spread and note + 12 <= hi:
                events.append((bs, CH_PAD, note + 12, self._humanize_velocity(58 + int(self.orchestral_v * 14)), dur))

        if notes:
            oct_up = notes[0] + 12
            if oct_up <= hi:
                vel = self._humanize_velocity(int(60 + self.energy * 15))
                events.append((bs, CH_PAD, oct_up, vel, dur))

        # weirdness高でたまにsus感を追加
        if self.weirdness_v > 0.5 and notes:
            sus = notes[0] + 5
            if lo <= sus <= hi:
                events.append((bs, CH_PAD, sus, self._humanize_velocity(54), dur))

        return events
