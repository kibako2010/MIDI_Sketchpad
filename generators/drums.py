# generators/drums.py
from typing import List
from generators.base import BaseGenerator, MidiEvent
from config import DRUM, CH_DRUMS, CH_PERCUSSION


class DrumsGenerator(BaseGenerator):

    def generate(self) -> List[MidiEvent]:
        num, den = self.time_sig
        if den == 8 and num in (6, 12):
            return self._generate_6_8()
        return self._generate_4_4()

    def _generate_6_8(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        for bar in range(self.bars):
            bs = self._bar_start(bar)

            # Kick: 1拍目(0) と 4拍目(3)
            for beat_idx, vel_base in [(0, 100), (3, 80)]:
                tick = bs + beat_idx * et
                vel  = self._humanize_velocity(vel_base)
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                DRUM["kick"], vel, et - 10))

            # Snare / Rim: 3拍目(2) と 6拍目(5)
            for beat_idx in [2, 5]:
                tick = bs + beat_idx * et
                note = DRUM["snare"] if self.anime_v > 0.6 else DRUM["snare_rim"]
                vel  = self._humanize_velocity(int(75 + self.energy * 20))
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                note, vel, et - 10))

            # HiHat: 全6拍
            for i in range(6):
                tick   = bs + i * et
                accent = (i == 0 or i == 3)
                vel    = self._humanize_velocity(
                    int(55 + self.density * 20) + (15 if accent else 0)
                )
                if self.energy > 0.8 and i in [2, 5]:
                    note = DRUM["hihat_open"]
                    dur  = et * 2
                else:
                    note = DRUM["hihat_closed"]
                    dur  = et - 5
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                note, vel, dur))

            # クラッシュ: 4バーごとの先頭
            if bar % 4 == 0:
                events.append((bs, CH_DRUMS, DRUM["crash"],
                                self._humanize_velocity(90), et * 2))

        return events

    def _generate_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        for bar in range(self.bars):
            bs = self._bar_start(bar)

            for beat in [0, 4]:
                tick = bs + beat * et
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                DRUM["kick"],
                                self._humanize_velocity(95), et - 10))

            for beat in [2, 6]:
                tick = bs + beat * et
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                DRUM["snare"],
                                self._humanize_velocity(85), et - 10))

            for i in range(8):
                tick = bs + i * et
                vel  = self._humanize_velocity(60 + (15 if i % 2 == 0 else 0))
                events.append((self._humanize_timing(tick), CH_DRUMS,
                                DRUM["hihat_closed"], vel, et - 5))

        return events


class PercussionGenerator(BaseGenerator):

    def generate(self) -> List[MidiEvent]:
        num, den = self.time_sig
        if den == 8 and num in (6, 12):
            return self._bodhran_6_8()
        return self._perc_4_4()

    def _bodhran_6_8(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()

        DOWN = 64
        UP   = 63

        # 強弱弱 中弱弱 パターン
        pattern_vel   = [100, 45, 65, 85, 40, 60]
        pattern_notes = [DOWN, UP, UP, DOWN, UP, UP]

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            for i in range(6):
                tick = bs + i * et
                note = pattern_notes[i]
                vel  = self._humanize_velocity(
                    int(pattern_vel[i] * (0.7 + self.energy * 0.3))
                )
                events.append((self._humanize_timing(tick), CH_PERCUSSION,
                                note, vel, et - 15))

            # 装飾打
            if self.density > 0.7 and self.rng.random() < 0.4:
                extra_tick = bs + int(et * 2.5)
                events.append((self._humanize_timing(extra_tick), CH_PERCUSSION,
                                UP, self._humanize_velocity(50), int(et * 0.5)))

        return events

    def _perc_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        for bar in range(self.bars):
            bs = self._bar_start(bar)
            for i in [0, 2, 4, 6]:
                tick = bs + i * et
                events.append((tick, CH_PERCUSSION, 64,
                                self._humanize_velocity(75), et - 10))
        return events
