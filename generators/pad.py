# generators/pad.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import chord_name_to_notes
from config import CH_PAD, RANGE


class PadGenerator(BaseGenerator):

    def _get_chord_notes(self, chord_name: str) -> List[int]:
        lo, hi = RANGE["pad"]
        notes  = chord_name_to_notes(chord_name, octave=4)
        result = [n for n in notes if lo <= n <= hi]
        if not result:
            result = [n for n in notes]
            while result and result[0] < lo:
                result = [n+12 for n in result]
        return sorted(result)

    def _add_color(self, notes: List[int]) -> List[int]:
        """9th/sus2的なカラーノートを追加（アニメ風の浮遊感）"""
        lo, hi = RANGE["pad"]
        if not notes:
            return notes
        ninth = notes[0] + 14
        if lo <= ninth <= hi and ninth not in notes:
            notes = notes + [ninth]
        return notes

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []

        for bar in range(self.bars):
            chord    = self._chord_for_bar(bar)
            progress = bar / max(self.bars - 1, 1)

            if progress < 0.25:
                # イントロ: 薄いサステイン
                events.extend(self._sustain(bar, chord, vel_base=45))

            elif progress < 0.5:
                # Aメロ: 少し厚いサステイン + カラーノート
                events.extend(self._sustain(bar, chord, vel_base=55,
                                            add_color=True))

            elif progress < 0.75:
                # Bメロ: アルペジオで動きを出す
                events.extend(self._arpeggio(bar, chord))

            else:
                # クライマックス: 厚いサステイン + オクターブ
                events.extend(self._climax_pad(bar, chord))

        return events

    def _sustain(self, bar: int, chord_name: str,
                 vel_base: int = 50,
                 add_color: bool = False) -> List[MidiEvent]:
        bs    = self._bar_start(bar)
        dur   = int(self.ticks_per_bar * 0.95)
        notes = self._get_chord_notes(chord_name)
        if add_color:
            notes = self._add_color(notes)
        events = []
        for note in notes:
            vel = self._humanize_velocity(vel_base)
            events.append((bs, CH_PAD, note, vel, dur))
        return events

    def _arpeggio(self, bar: int, chord_name: str) -> List[MidiEvent]:
        """上昇アルペジオ → 頂点サステイン"""
        events = []
        et     = self._eighth_ticks()
        bs     = self._bar_start(bar)
        notes  = self._get_chord_notes(chord_name)
        notes  = self._add_color(notes)
        lo, hi = RANGE["pad"]

        # アルペジオ（3音）
        arp = notes[:3]
        for i, note in enumerate(arp):
            tick = bs + i * et
            vel  = self._humanize_velocity(55 + i*8)
            events.append((self._humanize_timing(tick),
                           CH_PAD, note, vel, et*2))

        # 頂点ノートをサステイン
        if notes:
            top  = notes[-1]
            tick = bs + len(arp) * et
            dur  = self.ticks_per_bar - len(arp) * et - 20
            vel  = self._humanize_velocity(65)
            events.append((tick, CH_PAD, top, vel, max(dur, et)))

        return events

    def _climax_pad(self, bar: int, chord_name: str) -> List[MidiEvent]:
        """クライマックス: 全音+オクターブで厚みを出す"""
        events = []
        bs     = self._bar_start(bar)
        dur    = int(self.ticks_per_bar * 0.95)
        notes  = self._get_chord_notes(chord_name)
        notes  = self._add_color(notes)
        lo, hi = RANGE["pad"]

        # 通常コードトーン
        for note in notes:
            vel = self._humanize_velocity(int(70 + self.energy * 20))
            events.append((bs, CH_PAD, note, vel, dur))

        # オクターブ上のルート
        if notes:
            oct_up = notes[0] + 12
            if oct_up <= hi:
                vel = self._humanize_velocity(int(60 + self.energy * 15))
                events.append((bs, CH_PAD, oct_up, vel, dur))

        return events
