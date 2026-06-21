# generators/base.py
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import random

MidiEvent = Tuple[int, int, int, int, int]


class BaseGenerator(ABC):

    def __init__(
        self,
        chords:         List[str],
        key:            str,
        scale:          str,
        params:         Dict[str, Any],
        bars:           int             = 8,
        ticks_per_beat: int             = 480,
        time_sig:       Tuple[int, int] = (6, 8),
        seed:           int             = 42,
    ):
        self.chords    = chords
        self.key       = key
        self.scale     = scale
        self.params    = params
        self.bars      = bars
        self.tpb       = ticks_per_beat
        self.time_sig  = time_sig
        self.seed      = seed
        self.rng       = random.Random(seed)

        num, den = time_sig

        # ---- tick計算を正しく修正 ----
        # 6/8: 1小節 = 8分音符6個 = (480/2)*6 = 1440 ticks
        # 4/4: 1小節 = 4分音符4個 = 480*4      = 1920 ticks
        # 共通式: ticks_per_beat * num * 4 / den  ← 浮動小数点除算
        self.ticks_per_bar = int(ticks_per_beat * num * 4 / den)

        self.ticks_per_beat_actual = ticks_per_beat

        # よく使うパラメータを短縮
        self.energy     = params.get("energy",     70) / 100.0
        self.density    = params.get("density",    70) / 100.0
        self.complexity = params.get("complexity", 60) / 100.0
        self.humanize_v = params.get("humanize",   70) / 100.0
        self.swing_v    = params.get("swing",      20) / 100.0
        self.anime_v    = params.get("anime",      80) / 100.0
        self.folk_v     = params.get("folk",       80) / 100.0
        self.rock_v     = params.get("rock",       20) / 100.0
        self.orchestral_v = params.get("orchestral", 45) / 100.0
        self.weirdness_v  = params.get("weirdness",  10) / 100.0

    # ------------------------------------------------------------------
    # ユーティリティ
    # ------------------------------------------------------------------

    def _chord_notes(self, chord_name: str, octave: int = 4) -> List[int]:
        from chord_parser import chord_name_to_notes
        return chord_name_to_notes(chord_name, octave)

    def _scale_notes(self, root_pc: int, octave_start: int = 3,
                     num_octaves: int = 3) -> List[int]:
        from config import SCALES
        intervals = SCALES.get(self.scale, SCALES["natural_minor"])
        notes = []
        for oct_i in range(num_octaves):
            for iv in intervals:
                n = root_pc + iv + (octave_start + oct_i) * 12
                notes.append(n)
        return notes

    def _root_pc(self) -> int:
        from config import NOTE_NAMES
        key_clean = self.key.replace("b", "").replace("#", "")
        try:
            idx = NOTE_NAMES.index(key_clean)
            if "b" in self.key:
                idx = (idx - 1) % 12
            elif "#" in self.key:
                idx = (idx + 1) % 12
        except ValueError:
            idx = 0
        return idx

    def _nearest_scale_note(self, note: int, scale_notes: List[int], lo: int | None = None, hi: int | None = None) -> int:
        if lo is not None:
            note = max(lo, note)
        if hi is not None:
            note = min(hi, note)
        if not scale_notes:
            return note

        candidates = [n for n in scale_notes if (lo is None or n >= lo) and (hi is None or n <= hi)]
        if not candidates:
            candidates = scale_notes

        return min(candidates, key=lambda n: (abs(n - note), n))

    def _humanize_velocity(self, vel: int, amount: float = None) -> int:
        if amount is None:
            amount = self.humanize_v
        deviation = int(15 * amount)
        v = vel + self.rng.randint(-deviation, deviation)
        return max(1, min(127, v))

    def _humanize_timing(self, tick: int, amount: float = None) -> int:
        if amount is None:
            amount = self.humanize_v
        deviation = int(self.tpb * 0.03 * amount)
        return max(0, tick + self.rng.randint(-deviation, deviation))

    def _bar_start(self, bar_idx: int) -> int:
        return bar_idx * self.ticks_per_bar

    def _chord_for_bar(self, bar_idx: int) -> str:
        if not self.chords:
            return "C"
        return self.chords[bar_idx % len(self.chords)]

    def _eighth_ticks(self) -> int:
        """8分音符のtick数"""
        num, den = self.time_sig
        # 8分音符 = ticks_per_beat * 4 / 8 = tpb / 2
        # ただし den=8 の場合も den=4 の場合も共通式で計算
        return int(self.tpb * 4 / 8)  # 常に tpb//2 = 240

    def _quarter_ticks(self) -> int:
        """4分音符のtick数"""
        return self.tpb  # 常に480

    def _sixteenth_ticks(self) -> int:
        """16分音符のtick数"""
        return self.tpb // 4  # 常に120

    def _dotted_quarter_ticks(self) -> int:
        """付点4分音符のtick数 (6/8の1拍)"""
        return int(self.tpb * 3 / 2)  # 720

    # ------------------------------------------------------------------
    # 抽象メソッド
    # ------------------------------------------------------------------

    @abstractmethod
    def generate(self) -> List[MidiEvent]:
        """
        MidiEventリストを返す。
        MidiEvent = (abs_tick, channel, note, velocity, duration_ticks)
        """
        ...
