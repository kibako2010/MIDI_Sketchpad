# main.py
import argparse
import os
import sys
import json
import random

from config       import OUTPUT_DIR
from chord_parser import (
    parse_midi_to_chords, chords_from_text,
    estimate_key_and_scale,
)
from prompt_interpreter import interpret_prompt
from chord_generator    import generate_chords
from style_planner      import plan_style
from humanizer          import apply_humanize
from midi_renderer      import export_part_files, export_merged_file

from generators.drums       import DrumsGenerator, PercussionGenerator
from generators.bass        import BassGenerator
from generators.guitar      import GuitarGenerator
from generators.fiddle      import FiddleGenerator
from generators.whistle     import WhistleGenerator
from generators.pad         import PadGenerator
from generators.chord_track import ChordTrackGenerator


def build_generators(
    chords, key, scale, params, bars, ticks_per_beat, time_sig, seed
):
    parts  = params.get("parts", {})
    kwargs = dict(
        chords=chords, key=key, scale=scale, params=params,
        bars=bars, ticks_per_beat=ticks_per_beat,
        time_sig=time_sig, seed=seed,
    )
    gens = {}
    if parts.get("drums",           True):  gens["Drums"]      = DrumsGenerator(**kwargs)
    if parts.get("percussion",      True):  gens["Percussion"] = PercussionGenerator(**kwargs)
    if parts.get("bass",            True):  gens["Bass"]       = BassGenerator(**kwargs)
    if parts.get("acoustic_guitar", True):  gens["Guitar"]     = GuitarGenerator(**kwargs)
    if parts.get("fiddle",          True):  gens["Fiddle"]     = FiddleGenerator(**kwargs)
    if parts.get("tin_whistle",     True):  gens["Whistle"]    = WhistleGenerator(**kwargs)
    if parts.get("pad_strings",     True):  gens["Pad"]        = PadGenerator(**kwargs)
    gens["ChordTrack"] = ChordTrackGenerator(**kwargs)
    return gens


def run(args):
    print("\n=== MIDI Sketchpad: Anime Irish Generator ===\n")

    # 1. プロンプト解釈（コード生成より先に行う）
    use_llm = not args.no_llm
    print(f"[1/5] プロンプト解釈 ({'LLM' if use_llm else 'キーワードフォールバック'})")
    print(f"       '{args.prompt}'")
    params = interpret_prompt(args.prompt, use_llm=use_llm)
    print(f"       Style: {params.get('style')} | Energy: {params.get('energy')} | "
          f"Anime: {params.get('anime')} | Folk: {params.get('folk')}")
    print(f"       Parts: {params.get('parts')}")

    # 2. コード進行の取得
    if args.generate_chords:
        # コード進行をゼロから生成
        print(f"[2/5] コード進行を生成中...")
        result = generate_chords(params, args.bars, args.seed or 42, use_llm)
        chords = result["chords"]
        key    = result["key"]
        scale  = result["scale"]
        print(f"       生成コード: {' | '.join(chords)}")
        print(f"       キー: {key} / スケール: {scale}")

    elif args.midi:
        print(f"[2/5] MIDIファイルからコード進行を解析: {args.midi}")
        chords     = parse_midi_to_chords(args.midi, bars=args.bars)
        key, scale = estimate_key_and_scale(chords)
        print(f"       コード: {' | '.join(chords)}")
        print(f"       キー: {key} / スケール: {scale}")

    else:
        print(f"[2/5] テキストからコード進行をパース: {args.chords}")
        chords     = chords_from_text(args.chords)
        key, scale = estimate_key_and_scale(chords)
        print(f"       コード: {' | '.join(chords)}")
        print(f"       キー: {key} / スケール: {scale}")

    if not chords:
        print("[ERROR] コード進行を取得できませんでした。")
        sys.exit(1)

    # 3. スタイルプラン決定
    plan     = plan_style(params, chords, key, scale)
    bpm      = plan["bpm"]
    time_sig = plan["time_sig"]
    scale    = plan["scale"]
    key      = plan["key"]
    print(f"[3/5] BPM: {bpm} | 拍子: {time_sig[0]}/{time_sig[1]} | "
          f"キー: {key} | スケール: {scale}")

    # 4. MIDI生成
    seed = args.seed if args.seed is not None else random.randint(0, 99999)
    print(f"[4/5] MIDI生成 (seed={seed}, {args.bars}bars) ...")

    ticks_per_beat = 480
    gens = build_generators(
        chords, key, scale, params,
        args.bars, ticks_per_beat, time_sig, seed,
    )

    all_events = {}
    for part_name, gen in gens.items():
        events = gen.generate()
        events = apply_humanize(events, params, seed=seed)
        all_events[part_name] = events
        print(f"       {part_name}: {len(events)} events")

    # 5. 書き出し
    out_dir = args.output or OUTPUT_DIR
    print(f"\n[5/5] MIDIファイル書き出し -> {out_dir}")
    written = export_part_files(all_events, out_dir, bpm, ticks_per_beat, time_sig)

    if args.merge:
        merged_path = os.path.join(out_dir, "All_Parts.mid")
        export_merged_file(all_events, merged_path, bpm, ticks_per_beat, time_sig)

    state = {
        "chords":          chords,
        "prompt":          args.prompt,
        "key":             key,
        "scale":           scale,
        "bpm":             bpm,
        "time_sig":        list(time_sig),
        "seed":            seed,
        "params":          params,
        "chords_generated": args.generate_chords,
    }
    state_path = os.path.join(out_dir, "session.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"  [OK] セッション保存: {state_path}")
    print(f"\n完了! {len(written)}ファイルを {out_dir} に書き出しました。")
    print(f"  seed={seed} を控えておくと同じMIDIを再生成できます。\n")


def main():
    parser = argparse.ArgumentParser(
        description="MIDI Sketchpad - コード進行からジャンル伴奏MIDIを生成"
    )
    parser.add_argument("--chords", type=str,
                        default="Dm | Bb | F | C | Dm | Bb | C | Dm",
                        help="コード進行テキスト")
    parser.add_argument("--midi",   type=str, default=None,
                        help="コード進行を含むMIDIファイルパス")
    parser.add_argument("--prompt", type=str,
                        default="アニメ風アイリッシュ。冒険感があって少し切ない。フィドルとホイッスル、アコギ、バウロン。",
                        help="スタイル・雰囲気の自然言語プロンプト")
    parser.add_argument("--bars",   type=int, default=8,
                        help="生成するバー数")
    parser.add_argument("--seed",   type=int, default=None,
                        help="乱数シード")
    parser.add_argument("--output", type=str, default=None,
                        help="出力ディレクトリ")
    parser.add_argument("--merge",  action="store_true",
                        help="全パートを1つのMIDIに書き出す")
    parser.add_argument("--no-llm", action="store_true",
                        help="LLMを使わずフォールバックのみ使用")
    parser.add_argument("--generate-chords", action="store_true",
                        help="コード進行をゼロから生成する")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
