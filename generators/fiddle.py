# generators/fiddle.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from config import CH_FIDDLE, RANGE, SCALES, CHORD_INTERVALS


class FiddleGenerator(BaseGenerator):

    def _build_scale(self, root_pc: int) -> List[int]:
        intervals = SCALES.get(self.scale, SCALES["dorian"])
        lo, hi = RANGE["fiddle"]
        notes = []
        for oct_i in range(3, 7):
            for iv in intervals:
                n = root_pc + iv + oct_i * 12
                if lo <= n <= hi:
                    notes.append(n)
        return sorted(set(notes))

    def _chord_tones(self, chord_name: str, scale_notes: List[int]) -> List[int]:
        from chord_parser import parse_chord_name
        from config import NOTE_NAMES
        parsed = parse_chord_name(chord_name)
        if not parsed:
            return scale_notes[:4]
        root_name, ctype = parsed
        name = root_name.replace("b", "").replace("#", "")
        try:
            root_pc = NOTE_NAMES.index(name)
            if "b" in root_name:
                root_pc = (root_pc - 1) % 12
            elif "#" in root_name:
                root_pc = (root_pc + 1) % 12
        except ValueError:
            root_pc = 0
        intervals = CHORD_INTERVALS.get(ctype, CHORD_INTERVALS["min"])
        chord_pcs = set((root_pc + iv) % 12 for iv in intervals)
        result = [n for n in scale_notes if n % 12 in chord_pcs]
        return result if result else scale_notes[:4]

    def _get_neighbors(self, note: int, scale_notes: List[int]):
        if note not in scale_notes:
            scale_notes = sorted(scale_notes + [note])
        idx = scale_notes.index(note)
        up1 = scale_notes[min(idx + 1, len(scale_notes) - 1)]
        up2 = scale_notes[min(idx + 2, len(scale_notes) - 1)]
        up3 = scale_notes[min(idx + 3, len(scale_notes) - 1)]
        dn1 = scale_notes[max(idx - 1, 0)]
        dn2 = scale_notes[max(idx - 2, 0)]
        return up1, up2, up3, dn1, dn2

    def _jig_phrase(self, bar: int, chord_name: str, scale_notes: List[int], section: str) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        bs = self._bar_start(bar)
        bar_end = bs + self.ticks_per_bar

        chord_tones = self._chord_tones(chord_name, scale_notes)
        if not chord_tones:
            return events

        core = chord_tones[0]
        up1, up2, up3, dn1, dn2 = self._get_neighbors(core, scale_notes)

        patterns = {
            "A_rise": [
                [core, up1, up2, up3, up2, up1],
                [dn1, core, up1, up2, up1, core],
                [core, up2, up1, up2, up3, up2],
            ],
            "A_fall": [
                [up2, up1, core, dn1, core, up1],
                [up3, up2, up1, core, up1, core],
                [up1, core, dn1, dn2, dn1, core],
            ],
            "B_dance": [
                [core, up2, core, up1, core, dn1],
                [up1, core, up2, core, up1, up2],
                [core, dn1, core, up1, up2, up1],
            ],
            "B_ornament": [
                [up1, core, up1, up2, up1, core],
                [core, up1, core, dn1, core, up1],
                [up2, up1, up2, up3, up2, up1],
            ],
            "climax": [
                [core, up1, up2, up3, up3, up3],
                [up1, up2, up3, up2, up3, up3],
            ],
        }

        phrase_pool = patterns.get(section, patterns["A_rise"])
        motif = self.rng.choice(phrase_pool)

        lo, hi = RANGE["fiddle"]
        motif = [max(lo, min(hi, n)) for n in motif]

        vel_base = int(80 + self.energy * 18 + self.folk_v * 6)
        if section == "climax":
            vel_base = int(94 + self.energy * 16 + self.anime_v * 8)

        # densityが低いと休符増
        rest_prob = max(0.0, 0.4 - self.density * 0.35)

        for i, note in enumerate(motif):
            if i not in (0, 3) and self.rng.random() < rest_prob:
                continue

            tick = bs + i * et
            accent = (i == 0 or i == 3)
            vel = self._humanize_velocity(vel_base + (12 if accent else -6))
            if i == 5:
                max_dur = bar_end - tick - 10
                dur = min(int(et * 1.4), max(10, max_dur))
            else:
                dur = et - 12

            # weirdnessが高いと時々跳躍
            if self.weirdness_v > 0.55 and self.rng.random() < 0.15:
                note = min(hi, note + 2)

            events.append((self._humanize_timing(tick), CH_FIDDLE, note, vel, dur))

        # folkに応じて装飾音頻度を制御
        ornament_prob = 0.2 + self.folk_v * 0.45 + self.complexity * 0.2
        if self.rng.random() < min(0.95, ornament_prob):
            grace_tick = bs - int(et * 0.15)
            if grace_tick >= 0:
                events.append((grace_tick, CH_FIDDLE, up1, self._humanize_velocity(55), int(et * 0.2)))

        return events

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        root_pc = self._root_pc()
        scale_notes = self._build_scale(root_pc)
        total_bars = self.bars

        # anime値でクライマックス開始位置を前倒し
        climax_start = 0.75 - (self.anime_v * 0.20)

        for bar in range(total_bars):
            chord = self._chord_for_bar(bar)
            progress = bar / max(total_bars - 1, 1)

            if progress < 0.25:
                section = "A_rise"
            elif progress < 0.5:
                section = "A_fall"
            elif progress < max(0.55, climax_start):
                section = self.rng.choice(["B_dance", "B_ornament"])
            else:
                section = "climax" if self.anime_v > 0.45 else self.rng.choice(["A_rise", "B_dance"])

            events.extend(self._jig_phrase(bar, chord, scale_notes, section))

        return events
