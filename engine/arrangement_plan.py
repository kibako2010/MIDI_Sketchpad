import hashlib
import json
from typing import Any, Dict, List


ARRANGEMENT_PLAN_VERSION = "0.1"


def _signature_payload(params: Dict[str, Any], chords: List[str], bars: int, seed: int) -> Dict[str, Any]:
    return {
        "params": params,
        "chords": chords,
        "bars": bars,
        "seed": seed,
    }


def _calc_signature(params: Dict[str, Any], chords: List[str], bars: int, seed: int) -> str:
    payload = _signature_payload(params, chords, bars, seed)
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def summarize_arrangement_plan(
    params: Dict[str, Any],
    chords: List[str],
    bars: int,
    seed: int,
) -> Dict[str, Any]:
    """
    v0.1: session.json にはArrangementPlanの要約のみ保存する。
    完全再現は params/chords/bars/seed から deterministic に再生成する。
    """
    parts = params.get("parts", {}) or {}
    enabled_parts = sorted([name for name, on in parts.items() if bool(on)])

    preview_count = min(max(bars, 0), 8)
    bar_preview = []
    section_labels = ["A", "A'", "B", "A''"]

    for i in range(preview_count):
        chord = chords[i % len(chords)] if chords else "N.C."
        section_idx = (i * len(section_labels)) // max(preview_count, 1)
        bar_preview.append(
            {
                "bar": i + 1,
                "section": section_labels[min(section_idx, len(section_labels) - 1)],
                "chord": chord,
            }
        )

    return {
        "version": ARRANGEMENT_PLAN_VERSION,
        "storage": "summary",
        "signature": _calc_signature(params, chords, bars, seed),
        "seed": seed,
        "bars": bars,
        "enabled_parts": enabled_parts,
        "bar_preview": bar_preview,
        "deterministic_regeneration": {
            "source": ["params", "chords", "bars", "seed"],
            "full_plan_file": "arrangement_plan.json (future optional)",
        },
    }
