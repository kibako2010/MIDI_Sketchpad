# humanizer.py
"""
ヒューマナイズ処理モジュール。
生成済みMidiEventリストに対してマクロレベルの処理を行う。
"""

from typing import List, Dict, Any
import random
from generators.base import MidiEvent


def apply_humanize(
    events: List[MidiEvent],
    params: Dict[str, Any],
    seed: int = 42,
) -> List[MidiEvent]:
    """
    MidiEventリストにヒューマナイズを適用して返す。
    現在の処理:
    - velocity microvariation (全体)
    - timing jitter (non-drums)
    - swing (optional)
    """
    rng    = random.Random(seed + 9999)
    amount = params.get("humanize", 70) / 100.0
    swing  = params.get("swing",    20) / 100.0
    tpb    = 480  # デフォルト

    result = []
    for (tick, ch, note, vel, dur) in events:
        # ドラム（ch9）はtimingを動かさない
        if ch == 9:
            new_vel  = _micro_vel(vel, amount, rng)
            result.append((tick, ch, note, new_vel, dur))
            continue

        new_tick = _timing_jitter(tick, amount, tpb, rng)
        new_vel  = _micro_vel(vel, amount, rng)

        # Swing: 8分音符の奇数番目を少し遅らせる
        if swing > 0.05:
            eighth = tpb // 2
            beat_pos = tick % (tpb * 2)  # 2拍周期
            if eighth <= beat_pos < eighth * 2:
                new_tick += int(eighth * swing * 0.33)

        result.append((max(0, new_tick), ch, note, new_vel, dur))

    return result


def _micro_vel(vel: int, amount: float, rng: random.Random) -> int:
    dev = int(8 * amount)
    return max(1, min(127, vel + rng.randint(-dev, dev)))


def _timing_jitter(tick: int, amount: float, tpb: int,
                   rng: random.Random) -> int:
    dev = int(tpb * 0.025 * amount)
    return tick + rng.randint(-dev, dev)