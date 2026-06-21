# generators/chord_track.py
"""
コードトラック: 各小節のコード構成音をサステインで配置する。
音源には割り当てず、コード進行の「ガイド」として使う。
DAW上でコード進行を視覚的に確認できる。
"""

from typing import List
from generators.base import BaseGenerator, MidiEvent
from chord_parser import chord_name_to_notes
from config import RANGE

# コードトラック専用チャンネル (Ch16 = index 15)
CH_CHORD_TRACK = 15


class ChordTrackGenerator(BaseGenerator):

    def generate(self) -> List[MidiEvent]:
        events: List[MidiEvent] = []

        for bar in range(self.bars):
            chord   = self._chord_for_bar(bar)
            bs      = self._bar_start(bar)
            # 小節いっぱいに伸ばす（少しだけ短くして次小節と重ならないように）
            dur     = self.ticks_per_bar - 10

            notes   = self._get_chord_notes(chord)
            for note in notes:
                # velocity は固定（音源に割り当てても目立たない音量）
                events.append((bs, CH_CHORD_TRACK, note, 64, dur))

        return events

    def _get_chord_notes(self, chord_name: str) -> List[int]:
        """
        コード構成音を適切なオクターブで取得。
        ピアノの中音域（C3〜C5）に収める。
        """
        lo, hi = 48, 72   # C3〜C5
        notes  = chord_name_to_notes(chord_name, octave=3)
        result = []
        for n in notes:
            while n < lo: n += 12
            while n > hi: n -= 12
            if lo <= n <= hi:
                result.append(n)
        return sorted(set(result))
