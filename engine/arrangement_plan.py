import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


ARRANGEMENT_PLAN_VERSION = "0.1"


@dataclass(frozen=True, slots=True)
class DeterministicRegenerationInfo:
    source: List[str]
    full_plan_file: str


@dataclass(frozen=True, slots=True)
class BarPreviewEntry:
    bar: int
    section: str
    chord: str


@dataclass(frozen=True, slots=True)
class ArrangementPlanSummary:
    version: str
    storage: str
    signature: str
    seed: int
    bars: int
    enabled_parts: List[str]
    bar_preview: List[BarPreviewEntry]
    deterministic_regeneration: DeterministicRegenerationInfo

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        # asdict() returns nested dict/list that is already JSON-serializable.
        return payload


def _signature_payload(params: Dict[str, Any], chords: List[str], bars: int, seed: int) -> Dict[str, Any]:
    return {
        "params": params,
        "chords": chords,
        "bars": bars,
        "seed": seed,
    }


def compute_arrangement_signature(params: Dict[str, Any], chords: List[str], bars: int, seed: int) -> str:
    payload = _signature_payload(params, chords, bars, seed)
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def build_arrangement_plan_summary(
    params: Dict[str, Any],
    chords: List[str],
    bars: int,
    seed: int,
) -> ArrangementPlanSummary:
    """
    v0.1: session.json にはArrangementPlanの要約のみ保存する。
    完全再現は params/chords/bars/seed から deterministic に再生成する。
    """
    parts = params.get("parts", {}) or {}
    enabled_parts = sorted([name for name, on in parts.items() if bool(on)])

    preview_count = min(max(bars, 0), 8)
    section_labels = ["A", "A'", "B", "A''"]
    bar_preview: List[BarPreviewEntry] = []

    for i in range(preview_count):
        chord = chords[i % len(chords)] if chords else "N.C."
        section_idx = (i * len(section_labels)) // max(preview_count, 1)
        bar_preview.append(
            BarPreviewEntry(
                bar=i + 1,
                section=section_labels[min(section_idx, len(section_labels) - 1)],
                chord=chord,
            )
        )

    return ArrangementPlanSummary(
        version=ARRANGEMENT_PLAN_VERSION,
        storage="summary",
        signature=compute_arrangement_signature(params, chords, bars, seed),
        seed=seed,
        bars=bars,
        enabled_parts=enabled_parts,
        bar_preview=bar_preview,
        deterministic_regeneration=DeterministicRegenerationInfo(
            source=["params", "chords", "bars", "seed"],
            full_plan_file="arrangement_plan.json (future optional)",
        ),
    )


def summarize_arrangement_plan(
    params: Dict[str, Any],
    chords: List[str],
    bars: int,
    seed: int,
) -> Dict[str, Any]:
    """Backward-compatible helper for JSON payloads."""
    return build_arrangement_plan_summary(params, chords, bars, seed).to_dict()


def validate_arrangement_plan_summary(
    arrangement_plan: Dict[str, Any],
    params: Dict[str, Any],
    chords: List[str],
    bars: int,
    seed: int,
) -> Dict[str, Any]:
    """
    Validate whether persisted arrangement_plan summary matches deterministic inputs.
    Returns a compact diagnostic dictionary for CLI logging and testing.
    """
    if not arrangement_plan:
        return {
            "ok": False,
            "reason": "missing_arrangement_plan",
            "expected_signature": compute_arrangement_signature(params, chords, bars, seed),
            "actual_signature": None,
        }

    expected = compute_arrangement_signature(params, chords, bars, seed)
    actual = arrangement_plan.get("signature")
    ok = actual == expected

    return {
        "ok": ok,
        "reason": "ok" if ok else "signature_mismatch",
        "expected_signature": expected,
        "actual_signature": actual,
    }
