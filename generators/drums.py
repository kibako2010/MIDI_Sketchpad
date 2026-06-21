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
        rock_push = int(self.rock_v * 20)
        song_end = self.ticks_per_bar * self.bars

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            bar_end = bs + self.ticks_per_bar
            is_last_bar = (bar == self.bars - 1)

            for beat_idx, vel_base in [(0, 98 + rock_push), (3, 78 + rock_push // 2)]:
                tick = bs + beat_idx * et
                vel = self._humanize_velocity(vel_base)
                events.append((self._humanize_timing(tick), CH_DRUMS, DRUM["kick"], vel, et - 10))

            # rock値でスネアの押し出しを強化
            for beat_idx in [2, 5]:
                tick = bs + beat_idx * et
                note = DRUM["snare"] if (self.anime_v > 0.6 or self.rock_v > 0.45) else DRUM["snare_rim"]
                vel = self._humanize_velocity(int(72 + self.energy * 22 + self.rock_v * 10))
                events.append((self._humanize_timing(tick), CH_DRUMS, note, vel, et - 10))

            # densityでハイハット密度調整
            hihat_steps = range(6) if self.density > 0.45 else [0, 2, 3, 5]
            for i in hihat_steps:
                tick = bs + i * et
                accent = (i == 0 or i == 3)
                vel = self._humanize_velocity(int(52 + self.density * 22) + (15 if accent else 0))

                # 終端ではclose優先。特に最終小節はopenを使わない。
                can_open = self.energy > 0.8 and i == 2 and not is_last_bar
                if can_open:
                    tentative_dur = et * 2
                    max_safe_dur = min(bar_end - tick, song_end - tick) - 5
                    if max_safe_dur > et:
                        note = DRUM["hihat_open"]
                        dur = min(tentative_dur, max_safe_dur)
                    else:
                        note = DRUM["hihat_closed"]
                        dur = et - 5
                else:
                    note = DRUM["hihat_closed"]
                    dur = et - 5

                events.append((self._humanize_timing(tick), CH_DRUMS, note, vel, dur))

            if bar % 4 == 0:
                events.append((bs, CH_DRUMS, DRUM["crash"], self._humanize_velocity(88 + rock_push // 2), et * 2))

        return events

    def _generate_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        rock_push = int(self.rock_v * 18)

        for bar in range(self.bars):
            bs = self._bar_start(bar)

            for beat in [0, 4]:
                tick = bs + beat * et
                events.append((self._humanize_timing(tick), CH_DRUMS,
                               DRUM["kick"], self._humanize_velocity(92 + rock_push), et - 10))

            for beat in [2, 6]:
                tick = bs + beat * et
                events.append((self._humanize_timing(tick), CH_DRUMS,
                               DRUM["snare"], self._humanize_velocity(82 + rock_push), et - 10))

            for i in range(8):
                tick = bs + i * et
                vel = self._humanize_velocity(58 + (15 if i % 2 == 0 else 0) + int(self.density * 10))
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
        UP = 63

        folk_weight = 0.5 + self.folk_v * 0.7
        pattern_vel = [100, 45, 65, 85, 40, 60]
        pattern_notes = [DOWN, UP, UP, DOWN, UP, UP]

        for bar in range(self.bars):
            bs = self._bar_start(bar)
            for i in range(6):
                tick = bs + i * et
                note = pattern_notes[i]
                vel = self._humanize_velocity(int(pattern_vel[i] * folk_weight * (0.7 + self.energy * 0.3)))
                events.append((self._humanize_timing(tick), CH_PERCUSSION, note, vel, et - 15))

            # folk・densityが高いと装飾打が増える
            extra_prob = 0.15 + self.folk_v * 0.35 + self.density * 0.25
            if self.rng.random() < min(0.85, extra_prob):
                extra_tick = bs + int(et * 2.5)
                events.append((self._humanize_timing(extra_tick), CH_PERCUSSION,
                               UP, self._humanize_velocity(48 + int(self.folk_v * 20)), int(et * 0.5)))

        return events

    def _perc_4_4(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []
        et = self._eighth_ticks()
        for bar in range(self.bars):
            bs = self._bar_start(bar)
            for i in [0, 2, 4, 6]:
                tick = bs + i * et
                events.append((tick, CH_PERCUSSION, 64, self._humanize_velocity(70 + int(self.folk_v * 15)), et - 10))
        return events
