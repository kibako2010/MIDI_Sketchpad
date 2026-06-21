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
        """スケール上の隣接音を返す"""
        if note not in scale_notes:
            scale_notes = sorted(scale_notes + [note])
        idx = scale_notes.index(note)
        up1  = scale_notes[min(idx+1, len(scale_notes)-1)]
        up2  = scale_notes[min(idx+2, len(scale_notes)-1)]
        up3  = scale_notes[min(idx+3, len(scale_notes)-1)]
        dn1  = scale_notes[max(idx-1, 0)]
        dn2  = scale_notes[max(idx-2, 0)]
        return up1, up2, up3, dn1, dn2

    def _jig_phrase(self, bar: int, chord_name: str,
                    scale_notes: List[int],
                    section: str) -> List[MidiEvent]:
        """
        アイリッシュジグの典型フレーズ集。
        sectionに応じてパターンを選択。
        """
        events: List[MidiEvent] = []
        et  = self._eighth_ticks()
        bs  = self._bar_start(bar)
        bar_end = bs + self.ticks_per_bar

        chord_tones = self._chord_tones(chord_name, scale_notes)
        if not chord_tones:
            return events

        # コアノートはコードの根音に近いスケール音
        core = chord_tones[0]
        up1, up2, up3, dn1, dn2 = self._get_neighbors(core, scale_notes)

        # ---- フレーズパターン集（アイリッシュジグの典型） ----
        patterns = {
            "A_rise": [
                # 上昇系: コアから上へ駆け上がる
                [core, up1, up2, up3, up2, up1],
                [dn1,  core, up1, up2, up1, core],
                [core, up2, up1, up2, up3, up2],
            ],
            "A_fall": [
                # 下降系: 上から戻ってくる
                [up2, up1, core, dn1, core, up1],
                [up3, up2, up1, core, up1, core],
                [up1, core, dn1, dn2, dn1, core],
            ],
            "B_dance": [
                # ダンス系: 跳ねる動き
                [core, up2, core, up1, core, dn1],
                [up1,  core, up2, core, up1, up2],
                [core, dn1, core, up1, up2, up1],
            ],
            "B_ornament": [
                # 装飾系: ターンとモルデント
                [up1, core, up1, up2, up1, core],
                [core, up1, core, dn1, core, up1],
                [up2, up1, up2, up3, up2, up1],
            ],
            "climax": [
                # クライマックス: 力強い上昇
                [core, up1, up2, up3, up3, up3],
                [up1,  up2, up3, up2, up3, up3],
            ],
        }

        phrase_pool = patterns.get(section, patterns["A_rise"])
        motif = self.rng.choice(phrase_pool)

        # 音域クランプ
        lo, hi = RANGE["fiddle"]
        motif  = [max(lo, min(hi, n)) for n in motif]

        vel_base = int(80 + self.energy * 18)

        # セクションによってベロシティを変える
        if section == "climax":
            vel_base = int(95 + self.energy * 15)
        elif section in ("A_rise", "B_dance"):
            vel_base = int(82 + self.energy * 16)

        for i, note in enumerate(motif):
            tick   = bs + i * et
            accent = (i == 0 or i == 3)
            vel    = self._humanize_velocity(
                vel_base + (12 if accent else -6)
            )
            if i == 5:
                max_dur = bar_end - tick - 10
                dur     = min(int(et * 1.4), max(10, max_dur))
            else:
                dur = et - 12

            events.append((
                self._humanize_timing(tick),
                CH_FIDDLE, note, vel, dur
            ))

        # 装飾音（モルデント）を先頭に付ける
        if self.complexity > 0.5 and self.rng.random() < 0.5:
            grace_tick = bs - int(et * 0.15)
            if grace_tick >= 0:
                events.append((
                    grace_tick, CH_FIDDLE, up1,
                    self._humanize_velocity(55), int(et * 0.2)
                ))

        return events

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        root_pc     = self._root_pc()
        scale_notes = self._build_scale(root_pc)
        total_bars  = self.bars

        for bar in range(total_bars):
            chord = self._chord_for_bar(bar)

            # ---- 曲の構成に応じてセクションを決定 ----
            progress = bar / max(total_bars - 1, 1)  # 0.0〜1.0

            if progress < 0.25:
                # イントロ〜Aメロ: 上昇系
                section = "A_rise"
            elif progress < 0.5:
                # Aメロ後半: 下降系でバランス
                section = "A_fall"
            elif progress < 0.75:
                # Bメロ: ダンス系・装飾系をランダム
                section = self.rng.choice(["B_dance", "B_ornament"])
            else:
                # サビ〜クライマックス
                if self.anime_v > 0.6:
                    section = "climax"
                else:
                    section = self.rng.choice(["A_rise", "B_dance"])

            events.extend(
                self._jig_phrase(bar, chord, scale_notes, section)
            )

        return events
