# generators/whistle.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from config import CH_WHISTLE, SCALES, CHORD_INTERVALS


class WhistleGenerator(BaseGenerator):

    def _build_scale(self, root_pc: int) -> List[int]:
        intervals = SCALES.get(self.scale, SCALES["dorian"])
        lo, hi = 74, 98
        notes = []
        for oct_i in range(3, 8):
            for iv in intervals:
                n = root_pc + iv + oct_i * 12
                if lo <= n <= hi:
                    notes.append(n)
        return sorted(set(notes))

    def _chord_tones_in_scale(self, chord_name: str,
                               scale_notes: List[int]) -> List[int]:
        from chord_parser import parse_chord_name
        from config import NOTE_NAMES
        parsed = parse_chord_name(chord_name)
        if not parsed:
            return scale_notes[:4]
        root_name, ctype = parsed
        name = root_name.replace("b","").replace("#","")
        try:
            root_pc = NOTE_NAMES.index(name)
            if "b" in root_name: root_pc = (root_pc - 1) % 12
            elif "#" in root_name: root_pc = (root_pc + 1) % 12
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
        up1 = scale_notes[min(idx+1, len(scale_notes)-1)]
        up2 = scale_notes[min(idx+2, len(scale_notes)-1)]
        up3 = scale_notes[min(idx+3, len(scale_notes)-1)]
        dn1 = scale_notes[max(idx-1, 0)]
        dn2 = scale_notes[max(idx-2, 0)]
        return up1, up2, up3, dn1, dn2

    def _make_phrase(self, bar: int, chord_name: str,
                     scale_notes: List[int],
                     phrase_type: str,
                     section: str) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et      = self._eighth_ticks()
        bs      = self._bar_start(bar)
        bar_end = bs + self.ticks_per_bar

        if not scale_notes:
            return events

        chord_tones = self._chord_tones_in_scale(chord_name, scale_notes)
        core = chord_tones[len(chord_tones)//2]
        up1, up2, up3, dn1, dn2 = self._get_neighbors(core, scale_notes)

        # ---- ホイッスルはフィドルと対になる動きを持つ ----
        # フィドルが上昇(A_rise)→ホイッスルは下降気味
        # フィドルが下降(A_fall)→ホイッスルは上昇気味
        # フィドルがdance→ホイッスルは長めのトーンで対比
        # クライマックス→ホイッスルも上昇

        if section == "A_rise":
            # フィドルが上昇するのでホイッスルは高い位置からカウンター
            patterns = [
                [up2, up1, core, up1, up2, up3],
                [up3, up2, up1, up2, up1, core],
                [up1, up2, up1, core, up1, up2],
            ]
        elif section == "A_fall":
            # フィドルが下降するのでホイッスルは上昇で対比
            patterns = [
                [core, up1, up2, up1, up2, up3],
                [dn1,  core, up1, up2, up3, up2],
                [core, up2, up3, up2, up1, up2],
            ]
        elif section in ("B_dance", "B_ornament"):
            # ダンス系: 短いモチーフの繰り返し感
            patterns = [
                [up1, core, up1, core, up2, up1],
                [up2, up1, up2, up1, core, up1],
                [core, up1, core, up2, up1, core],
            ]
        elif section == "climax":
            # クライマックス: 高音域でユニゾン気味
            patterns = [
                [up2, up3, up2, up3, up2, up3],
                [up1, up2, up3, up2, up3, up3],
                [up3, up2, up3, up2, up1, up2],
            ]
        else:
            if phrase_type == "call":
                patterns = [[core, up1, up2, up1, core, dn1]]
            else:
                patterns = [[up2, up1, core, dn1, core, core]]

        motif = self.rng.choice(patterns)

        # 音域クランプ
        lo, hi = 74, 98
        motif  = [max(lo, min(hi, n)) for n in motif]

        vel_base = int(72 + self.energy * 15)
        if section == "climax":
            vel_base = int(88 + self.energy * 12)

        for i, note in enumerate(motif):
            tick   = bs + i * et
            accent = (i == 0 or i == 3)
            vel    = self._humanize_velocity(
                vel_base + (10 if accent else -5)
            )
            if i == 5:
                max_dur = bar_end - tick - 10
                dur     = min(int(et * 1.3), max(10, max_dur))
            else:
                dur = et - 15

            events.append((
                self._humanize_timing(tick),
                CH_WHISTLE, note, vel, dur
            ))

        return events

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        root_pc     = self._root_pc()
        scale_notes = self._build_scale(root_pc)

        if not scale_notes:
            return events

        for bar in range(self.bars):
            chord    = self._chord_for_bar(bar)
            progress = bar / max(self.bars - 1, 1)

            # フィドルと同じsectionロジックで対になる動きを作る
            if progress < 0.25:
                section = "A_rise"
            elif progress < 0.5:
                section = "A_fall"
            elif progress < 0.75:
                section = self.rng.choice(["B_dance", "B_ornament"])
            else:
                section = "climax" if self.anime_v > 0.6 else "A_rise"

            phrase_type = "call" if bar % 2 == 0 else "response"
            events.extend(
                self._make_phrase(bar, chord, scale_notes,
                                  phrase_type, section)
            )

        return events
