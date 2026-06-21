from typing import Dict, Any, List, Tuple

from chord_parser import parse_midi_to_chords, chords_from_text, estimate_key_and_scale
from style_planner import plan_style
from humanizer import apply_humanize

from generators.drums import DrumsGenerator, PercussionGenerator
from generators.bass import BassGenerator
from generators.guitar import GuitarGenerator
from generators.fiddle import FiddleGenerator
from generators.whistle import WhistleGenerator
from generators.pad import PadGenerator
from generators.piano import PianoGenerator
from generators.lead_synth import LeadSynthGenerator
from generators.chord_track import ChordTrackGenerator


class GenerationEngine:
    """
    CLI非依存の生成エンジン。
    将来のJUCE/C++移植時は、この責務分割をそのまま移植しやすい。
    """

    def build_generators(
        self,
        chords: List[str],
        key: str,
        scale: str,
        params: Dict[str, Any],
        bars: int,
        ticks_per_beat: int,
        time_sig: Tuple[int, int],
        seed: int,
    ):
        parts = params.get("parts", {})
        kwargs = dict(
            chords=chords,
            key=key,
            scale=scale,
            params=params,
            bars=bars,
            ticks_per_beat=ticks_per_beat,
            time_sig=time_sig,
            seed=seed,
        )
        gens = {}
        if parts.get("drums", True):
            gens["Drums"] = DrumsGenerator(**kwargs)
        if parts.get("percussion", True):
            gens["Percussion"] = PercussionGenerator(**kwargs)
        if parts.get("bass", True):
            gens["Bass"] = BassGenerator(**kwargs)
        if parts.get("acoustic_guitar", True):
            gens["Guitar"] = GuitarGenerator(**kwargs)
        if parts.get("fiddle", True):
            gens["Fiddle"] = FiddleGenerator(**kwargs)
        if parts.get("tin_whistle", True):
            gens["Whistle"] = WhistleGenerator(**kwargs)
        if parts.get("pad_strings", True):
            gens["Pad"] = PadGenerator(**kwargs)
        if parts.get("piano", False):
            gens["Piano"] = PianoGenerator(**kwargs)
        if parts.get("lead_synth", False):
            gens["Lead"] = LeadSynthGenerator(**kwargs)
        gens["ChordTrack"] = ChordTrackGenerator(**kwargs)
        return gens

    def resolve_chords(self, args, params: Dict[str, Any], use_llm: bool, chord_generator_fn):
        if args.generate_chords:
            result = chord_generator_fn(params, args.bars, args.seed or 42, use_llm)
            chords = result["chords"]
            key = result["key"]
            scale = result["scale"]
        elif args.midi:
            chords = parse_midi_to_chords(args.midi, bars=args.bars)
            key, scale = estimate_key_and_scale(chords)
        else:
            chords = chords_from_text(args.chords)
            key, scale = estimate_key_and_scale(chords)
        return chords, key, scale

    def render_events(
        self,
        chords: List[str],
        key: str,
        scale: str,
        params: Dict[str, Any],
        bars: int,
        seed: int,
        selected_parts: List[str] | None = None,
    ) -> Dict[str, Any]:
        plan = plan_style(params, chords, key, scale)
        bpm = plan["bpm"]
        time_sig = plan["time_sig"]
        final_scale = plan["scale"]
        final_key = plan["key"]
        ticks_per_beat = 480

        gens = self.build_generators(
            chords=chords,
            key=final_key,
            scale=final_scale,
            params=params,
            bars=bars,
            ticks_per_beat=ticks_per_beat,
            time_sig=time_sig,
            seed=seed,
        )

        if selected_parts is not None:
            normalized = {p.lower() for p in selected_parts}
            gens = {name: gen for name, gen in gens.items() if name.lower() in normalized}

        all_events = {}
        for part_name, gen in gens.items():
            events = gen.generate()
            if params.get("post_humanize", False):
                events = apply_humanize(events, params, seed=seed)
            all_events[part_name] = events

        return {
            "bpm": bpm,
            "time_sig": list(time_sig),
            "scale": final_scale,
            "key": final_key,
            "ticks_per_beat": ticks_per_beat,
            "events": all_events,
        }
