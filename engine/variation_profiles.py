from copy import deepcopy
from typing import Dict, Any


# C++/JUCE移植時にそのまま構造体化しやすいよう、
# プリセットをデータ駆動で定義する。
VARIATION_PROFILES: Dict[str, Dict[str, Any]] = {
    "folk": {
        "style": "anime_irish",
        "energy": 68,
        "density": 58,
        "complexity": 62,
        "anime": 45,
        "folk": 95,
        "rock": 12,
        "orchestral": 28,
        "humanize": 78,
        "swing": 30,
        "weirdness": 8,
        "generation_notes": {
            "fiddle": "traditional ornament-heavy jig motif",
            "percussion": "bodhran-forward pulse with subtle ghost hits",
        },
    },
    "anime": {
        "style": "anime_irish",
        "energy": 82,
        "density": 74,
        "complexity": 72,
        "anime": 98,
        "folk": 72,
        "rock": 26,
        "orchestral": 86,
        "humanize": 64,
        "swing": 16,
        "weirdness": 18,
        "generation_notes": {
            "strings": "wide cinematic lift with emotional tension",
            "fiddle": "heroic lead-like contour for climax",
        },
        "parts": {
            "pad_strings": True,
            "piano": True,
        },
    },
    "rock": {
        "style": "celtic_rock",
        "energy": 90,
        "density": 80,
        "complexity": 68,
        "anime": 35,
        "folk": 62,
        "rock": 96,
        "orchestral": 22,
        "humanize": 55,
        "swing": 8,
        "weirdness": 12,
        "generation_notes": {
            "guitar": "aggressive accent strums with driving momentum",
            "bass": "tight root-5th pulse with push into downbeats",
        },
        "parts": {
            "lead_synth": True,
        },
    },
    "weird": {
        "style": "anime_irish",
        "energy": 76,
        "density": 68,
        "complexity": 90,
        "anime": 70,
        "folk": 65,
        "rock": 42,
        "orchestral": 58,
        "humanize": 72,
        "swing": 24,
        "weirdness": 94,
        "generation_notes": {
            "fiddle": "unexpected leaps and asymmetrical ornaments",
            "tin_whistle": "counter-lines with chromatic color tones",
        },
        "parts": {
            "lead_synth": True,
            "piano": True,
        },
    },
}


def apply_variation_profile(label: str, base_params: Dict[str, Any]) -> Dict[str, Any]:
    """Return detailed variation params merged over base_params."""
    result = deepcopy(base_params)
    profile = VARIATION_PROFILES.get(label.strip().lower())
    if not profile:
        return result

    for key, value in profile.items():
        if key in ("parts", "generation_notes"):
            merged = dict(result.get(key, {}))
            merged.update(value)
            result[key] = merged
        else:
            result[key] = value
    return result
