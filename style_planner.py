# style_planner.py
from typing import Dict, Any, Tuple


def plan_style(
    params: Dict[str, Any],
    chords: list,
    key:    str,
    scale:  str,
) -> Dict[str, Any]:
    style      = params.get("style",      "anime_irish")
    tempo_feel = params.get("tempo_feel", "fast_6_8")
    energy     = params.get("energy",     70) / 100.0

    bpm, time_sig = _determine_tempo_and_meter(style, tempo_feel, energy)
    final_scale   = _determine_scale(style, scale, chords)

    return {
        "bpm":      bpm,
        "time_sig": time_sig,
        "scale":    final_scale,
        "key":      key,
    }


def _determine_tempo_and_meter(
    style: str, tempo_feel: str, energy: float
) -> Tuple[float, Tuple[int, int]]:

    if "irish" in style or "celtic" in style or "anime_irish" in style:
        if "12_8" in tempo_feel:
            bpm = 90 + energy * 40
            return round(bpm, 1), (12, 8)
        elif "4_4" in tempo_feel:
            bpm = 120 + energy * 40
            return round(bpm, 1), (4, 4)
        else:
            # fast_6_8 またはデフォルト → 必ず6/8
            bpm = 120 + energy * 50
            return round(bpm, 1), (6, 8)

    elif "city_pop" in style or "jazz" in style or "bossa" in style:
        bpm = 80 + energy * 50
        return round(bpm, 1), (4, 4)

    elif "trap" in style:
        bpm = 130 + energy * 20
        return round(bpm, 1), (4, 4)

    elif "synthwave" in style:
        bpm = 100 + energy * 30
        return round(bpm, 1), (4, 4)

    elif "drum_n_bass" in style or "dnb" in style:
        bpm = 160 + energy * 14
        return round(bpm, 1), (4, 4)

    else:
        bpm = 100 + energy * 40
        return round(bpm, 1), (4, 4)


def _determine_scale(style: str, detected_scale: str, chords: list) -> str:
    if "irish" in style or "celtic" in style or "anime_irish" in style:
        return "dorian"
    if "anime" in style:
        return (detected_scale
                if detected_scale in ("natural_minor", "dorian")
                else "natural_minor")
    return detected_scale
