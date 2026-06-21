# main.py
import argparse
import os
import sys
import json
import random
from copy import deepcopy

from config import OUTPUT_DIR
from chord_parser import parse_midi_to_chords, chords_from_text, estimate_key_and_scale
from prompt_interpreter import interpret_prompt, test_lm_studio_connection
from chord_generator import generate_chords
from style_planner import plan_style
from humanizer import apply_humanize
from midi_renderer import export_part_files, export_merged_file

from generators.drums import DrumsGenerator, PercussionGenerator
from generators.bass import BassGenerator
from generators.guitar import GuitarGenerator
from generators.fiddle import FiddleGenerator
from generators.whistle import WhistleGenerator
from generators.pad import PadGenerator
from generators.piano import PianoGenerator
from generators.lead_synth import LeadSynthGenerator
from generators.chord_track import ChordTrackGenerator


def build_generators(chords, key, scale, params, bars, ticks_per_beat, time_sig, seed):
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


def _resolve_chords(args, params, use_llm):
    if args.generate_chords:
        print("[2/5] コード進行を生成中...")
        result = generate_chords(params, args.bars, args.seed or 42, use_llm)
        chords = result["chords"]
        key = result["key"]
        scale = result["scale"]
    elif args.midi:
        print(f"[2/5] MIDIファイルからコード進行を解析: {args.midi}")
        chords = parse_midi_to_chords(args.midi, bars=args.bars)
        key, scale = estimate_key_and_scale(chords)
    else:
        print(f"[2/5] テキストからコード進行をパース: {args.chords}")
        chords = chords_from_text(args.chords)
        key, scale = estimate_key_and_scale(chords)

    print(f"       コード: {' | '.join(chords)}")
    print(f"       キー: {key} / スケール: {scale}")
    return chords, key, scale


def _render_and_export(chords, key, scale, params, bars, out_dir, seed, merge=False, selected_parts=None):
    plan = plan_style(params, chords, key, scale)
    bpm = plan["bpm"]
    time_sig = plan["time_sig"]
    scale = plan["scale"]
    key = plan["key"]
    print(f"[3/5] BPM: {bpm} | 拍子: {time_sig[0]}/{time_sig[1]} | キー: {key} | スケール: {scale}")

    ticks_per_beat = 480
    print(f"[4/5] MIDI生成 (seed={seed}, {bars}bars) ...")
    gens = build_generators(chords, key, scale, params, bars, ticks_per_beat, time_sig, seed)

    if selected_parts is not None:
        normalized = {p.lower() for p in selected_parts}
        gens = {name: gen for name, gen in gens.items() if name.lower() in normalized}

    all_events = {}
    for part_name, gen in gens.items():
        events = gen.generate()
        if params.get("post_humanize", False):
            events = apply_humanize(events, params, seed=seed)
        all_events[part_name] = events
        print(f"       {part_name}: {len(events)} events")

    print(f"\n[5/5] MIDIファイル書き出し -> {out_dir}")
    written = export_part_files(all_events, out_dir, bpm, ticks_per_beat, time_sig)

    if merge:
        merged_path = os.path.join(out_dir, "All_Parts.mid")
        export_merged_file(all_events, merged_path, bpm, ticks_per_beat, time_sig)

    return {
        "written": written,
        "bpm": bpm,
        "time_sig": list(time_sig),
        "scale": scale,
        "key": key,
        "events": all_events,
    }


def _save_session(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _variation_preset(label, base_params):
    p = deepcopy(base_params)
    name = label.strip().lower()

    if name == "folk":
        p["style"] = "anime_irish"
        p["folk"] = 92
        p["anime"] = max(45, p.get("anime", 70))
        p["rock"] = 15
    elif name == "anime":
        p["style"] = "anime_irish"
        p["anime"] = 95
        p["orchestral"] = 78
        p["density"] = max(70, p.get("density", 60))
    elif name == "rock":
        p["style"] = "celtic_rock"
        p["rock"] = 92
        p["energy"] = max(82, p.get("energy", 70))
        p["folk"] = max(55, p.get("folk", 70))
    elif name == "weird":
        p["style"] = "anime_irish"
        p["weirdness"] = 88
        p["complexity"] = max(82, p.get("complexity", 60))
    return p


def _run_variations(args, params, chords, key, scale):
    labels = [x.strip() for x in args.variations.split(",") if x.strip()]
    if not labels:
        print("[ERROR] --variations の指定が空です。")
        sys.exit(1)

    for idx, label in enumerate(labels):
        var_params = _variation_preset(label, params)
        var_seed = (args.seed if args.seed is not None else 42) + idx
        out_dir = os.path.join(args.output or OUTPUT_DIR, f"Variation_{label}")
        print(f"\n=== Variation: {label} ===")
        result = _render_and_export(
            chords=chords,
            key=key,
            scale=scale,
            params=var_params,
            bars=args.bars,
            out_dir=out_dir,
            seed=var_seed,
            merge=args.merge,
        )
        state = {
            "mode": "variation",
            "variation": label,
            "chords": chords,
            "prompt": args.prompt,
            "key": result["key"],
            "scale": result["scale"],
            "bpm": result["bpm"],
            "time_sig": result["time_sig"],
            "seed": var_seed,
            "bars": args.bars,
            "params": var_params,
            "part_files": result["written"],
        }
        _save_session(os.path.join(out_dir, "session.json"), state)


def _run_regenerate(args):
    if not args.session:
        print("[ERROR] --regenerate を使う場合は --session が必要です。")
        sys.exit(1)

    with open(args.session, "r", encoding="utf-8") as f:
        state = json.load(f)

    requested = [x.strip() for x in args.regenerate.split(",") if x.strip()]
    if not requested:
        print("[ERROR] --regenerate の指定が空です。")
        sys.exit(1)

    chords = state.get("chords", [])
    if not chords:
        print("[ERROR] session.json から chords を取得できません。")
        sys.exit(1)

    params = state.get("params", {})
    key = state.get("key", "C")
    scale = state.get("scale", "major")
    bars = int(state.get("bars", len(chords)))
    out_dir = args.output or os.path.dirname(os.path.abspath(args.session)) or OUTPUT_DIR
    seed = args.seed if args.seed is not None else random.randint(0, 99999)

    print("\n=== MIDI Sketchpad: Regenerate Mode ===\n")
    print(f"[1/3] session読み込み: {args.session}")
    print(f"       対象パート: {requested}")

    result = _render_and_export(
        chords=chords,
        key=key,
        scale=scale,
        params=params,
        bars=bars,
        out_dir=out_dir,
        seed=seed,
        merge=False,
        selected_parts=requested,
    )

    regen_state = {
        "mode": "regenerate",
        "source_session": args.session,
        "regenerated_parts": requested,
        "seed": seed,
        "part_files": result["written"],
    }
    _save_session(os.path.join(out_dir, "session_regenerate.json"), regen_state)
    print("\n完了! 指定パートのみ再生成しました。")


def run(args):
    if args.test_llm:
        result = test_lm_studio_connection()
        if result.get("ok"):
            print("[OK] LM Studio接続成功")
            print(result.get("response"))
            return
        print("[ERROR] LM Studio接続失敗")
        print(result.get("error"))
        sys.exit(1)

    if args.regenerate:
        _run_regenerate(args)
        return

    print("\n=== MIDI Sketchpad: Anime Irish Generator ===\n")

    use_llm = not args.no_llm
    print(f"[1/5] プロンプト解釈 ({'LLM' if use_llm else 'キーワードフォールバック'})")
    print(f"       '{args.prompt}'")
    params = interpret_prompt(args.prompt, use_llm=use_llm)
    print(
        f"       Style: {params.get('style')} | Energy: {params.get('energy')} | "
        f"Anime: {params.get('anime')} | Folk: {params.get('folk')} | Rock: {params.get('rock')}"
    )
    print(f"       Parts: {params.get('parts')}")

    chords, key, scale = _resolve_chords(args, params, use_llm)

    if not chords:
        print("[ERROR] コード進行を取得できませんでした。")
        sys.exit(1)

    if args.variations:
        _run_variations(args, params, chords, key, scale)
        return

    out_dir = args.output or OUTPUT_DIR
    seed = args.seed if args.seed is not None else random.randint(0, 99999)
    result = _render_and_export(
        chords=chords,
        key=key,
        scale=scale,
        params=params,
        bars=args.bars,
        out_dir=out_dir,
        seed=seed,
        merge=args.merge,
    )

    state = {
        "mode": "normal",
        "chords": chords,
        "prompt": args.prompt,
        "key": result["key"],
        "scale": result["scale"],
        "bpm": result["bpm"],
        "time_sig": result["time_sig"],
        "seed": seed,
        "bars": args.bars,
        "params": params,
        "chords_generated": args.generate_chords,
        "part_files": result["written"],
    }
    state_path = os.path.join(out_dir, "session.json")
    _save_session(state_path, state)
    print(f"  [OK] セッション保存: {state_path}")
    print(f"\n完了! {len(result['written'])}ファイルを {out_dir} に書き出しました。")
    print(f"  seed={seed} を控えておくと同じMIDIを再生成できます。\n")


def main():
    parser = argparse.ArgumentParser(description="MIDI Sketchpad - コード進行からジャンル伴奏MIDIを生成")
    parser.add_argument("--chords", type=str, default="Dm | Bb | F | C | Dm | Bb | C | Dm", help="コード進行テキスト")
    parser.add_argument("--midi", type=str, default=None, help="コード進行を含むMIDIファイルパス")
    parser.add_argument("--prompt", type=str,
                        default="アニメ風アイリッシュ。冒険感があって少し切ない。フィドルとホイッスル、アコギ、バウロン。",
                        help="スタイル・雰囲気の自然言語プロンプト")
    parser.add_argument("--bars", type=int, default=8, help="生成するバー数")
    parser.add_argument("--seed", type=int, default=None, help="乱数シード")
    parser.add_argument("--output", type=str, default=None, help="出力ディレクトリ")
    parser.add_argument("--merge", action="store_true", help="全パートを1つのMIDIに書き出す")
    parser.add_argument("--no-llm", action="store_true", help="LLMを使わずフォールバックのみ使用")
    parser.add_argument("--generate-chords", action="store_true", help="コード進行をゼロから生成する")

    parser.add_argument("--test-llm", action="store_true", help="LM Studio接続テストを実行")
    parser.add_argument("--regenerate", type=str, default=None, help="再生成するパート名(例: Drums,Bass)")
    parser.add_argument("--session", type=str, default=None, help="session.json のパス（regenerate用）")
    parser.add_argument("--variations", type=str, default=None, help="複数バリエーション(例: Folk,Anime,Rock,Weird)")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
