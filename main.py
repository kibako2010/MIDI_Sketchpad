# main.py
import argparse
import os
import sys
import json
import random
import shutil

from config import OUTPUT_DIR
from prompt_interpreter import interpret_prompt, test_lm_studio_connection
from chord_generator import generate_chords
from midi_renderer import (
    export_part_files,
    export_merged_file,
    export_merged_from_part_midis,
)
from engine.generation_engine import GenerationEngine
from engine.variation_profiles import apply_variation_profile
from engine.session_utils import resolve_part_file_map
from engine.arrangement_plan import (
    summarize_arrangement_plan,
    validate_arrangement_plan_summary,
    build_arrangement_plan_document,
    load_deterministic_inputs_from_plan_file,
)


ENGINE = GenerationEngine()


def _save_session(path, payload):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _list_to_part_map(file_paths):
    result = {}
    for p in file_paths:
        name = os.path.splitext(os.path.basename(p))[0]
        result[name] = p
    return result


def _maybe_export_arrangement_plan_file(args, out_dir, params, chords, bars, seed, filename="arrangement_plan.json"):
    if not getattr(args, "save_arrangement_plan", False):
        return None

    payload = build_arrangement_plan_document(
        params=params,
        chords=chords,
        bars=bars,
        seed=seed,
    )
    file_path = os.path.join(out_dir, filename)
    _save_session(file_path, payload)
    print(f"  [OK] ArrangementPlan保存: {file_path}")
    return file_path


def _render_and_export(chords, key, scale, params, bars, out_dir, seed, merge=False, selected_parts=None):
    render = ENGINE.render_events(
        chords=chords,
        key=key,
        scale=scale,
        params=params,
        bars=bars,
        seed=seed,
        selected_parts=selected_parts,
    )

    print(
        f"[3/5] BPM: {render['bpm']} | 拍子: {render['time_sig'][0]}/{render['time_sig'][1]} | "
        f"キー: {render['key']} | スケール: {render['scale']}"
    )
    print(f"[4/5] MIDI生成 (seed={seed}, {bars}bars) ...")
    for part_name, events in render["events"].items():
        print(f"       {part_name}: {len(events)} events")

    print(f"\n[5/5] MIDIファイル書き出し -> {out_dir}")
    written = export_part_files(
        render["events"],
        out_dir,
        render["bpm"],
        render["ticks_per_beat"],
        tuple(render["time_sig"]),
    )

    merged_path = None
    if merge:
        merged_path = os.path.join(out_dir, "All_Parts.mid")
        export_merged_file(
            render["events"],
            merged_path,
            render["bpm"],
            render["ticks_per_beat"],
            tuple(render["time_sig"]),
        )

    return {
        "written": written,
        "part_file_map": _list_to_part_map(written),
        "merged_path": merged_path,
        "bpm": render["bpm"],
        "time_sig": render["time_sig"],
        "scale": render["scale"],
        "key": render["key"],
        "ticks_per_beat": render["ticks_per_beat"],
    }


def _run_variations(args, params, chords, key, scale):
    labels = [x.strip() for x in args.variations.split(",") if x.strip()]
    if not labels:
        print("[ERROR] --variations の指定が空です。")
        sys.exit(1)

    for idx, label in enumerate(labels):
        var_params = apply_variation_profile(label, params)
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

        arrangement_plan_file = _maybe_export_arrangement_plan_file(
            args,
            out_dir=out_dir,
            params=var_params,
            chords=chords,
            bars=args.bars,
            seed=var_seed,
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
            "arrangement_plan": summarize_arrangement_plan(var_params, chords, args.bars, var_seed),
            "arrangement_plan_file": arrangement_plan_file,
            "part_files": result["written"],
            "merged_file": result["merged_path"],
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

    recovered = load_deterministic_inputs_from_plan_file(
        state.get("arrangement_plan_file"),
        args.session,
    )

    recovered_used = False
    if recovered:
        if not state.get("chords"):
            state["chords"] = recovered["chords"]
            recovered_used = True
        if not state.get("params"):
            state["params"] = recovered["params"]
            recovered_used = True
        if state.get("bars") in (None, ""):
            state["bars"] = recovered["bars"]
            recovered_used = True

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

    plan_seed = int(state.get("seed", recovered["seed"] if recovered else seed))
    plan_validation = validate_arrangement_plan_summary(
        state.get("arrangement_plan", {}),
        params=params,
        chords=chords,
        bars=bars,
        seed=plan_seed,
    )

    print("\n=== MIDI Sketchpad: Regenerate Mode ===\n")
    print(f"[1/4] session読み込み: {args.session}")
    print(f"       対象パート: {requested}")
    if recovered_used:
        print("       arrangement_plan_file から deterministic inputs を補完しました")
    if not plan_validation["ok"]:
        print(
            "       [WARN] arrangement_plan summary mismatch: "
            f"{plan_validation['reason']} "
            f"(expected={plan_validation['expected_signature']}, actual={plan_validation['actual_signature']})"
        )

    # 既存パートの場所を解決
    existing_part_map = resolve_part_file_map(state.get("part_files", []), args.session)

    # 指定パートのみ再生成
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

    regenerated_map = result["part_file_map"]

    # 既存パート + 再生成パートを完全再統合
    final_part_map = dict(existing_part_map)
    final_part_map.update(regenerated_map)

    # 再生成していない既存パートを出力先にコピーしてセットを揃える
    for part_name, src_path in list(final_part_map.items()):
        if part_name in regenerated_map:
            continue
        dst_path = os.path.join(out_dir, f"{part_name}.mid")
        if os.path.abspath(src_path) != os.path.abspath(dst_path):
            shutil.copy2(src_path, dst_path)
        final_part_map[part_name] = dst_path

    print("[4/4] 全パート完全mergeを再構築...")
    merged_path = os.path.join(out_dir, "All_Parts.mid")
    export_merged_from_part_midis(
        final_part_map,
        merged_path,
        bpm=result["bpm"],
        ticks_per_beat=result["ticks_per_beat"],
        time_sig=tuple(result["time_sig"]),
    )

    arrangement_plan_file = _maybe_export_arrangement_plan_file(
        args,
        out_dir=out_dir,
        params=params,
        chords=chords,
        bars=bars,
        seed=seed,
        filename="arrangement_plan_regenerate.json",
    )

    regen_state = {
        "mode": "regenerate",
        "source_session": args.session,
        "regenerated_parts": requested,
        "seed": seed,
        "chords": chords,
        "bars": bars,
        "params": params,
        "key": result["key"],
        "scale": result["scale"],
        "bpm": result["bpm"],
        "time_sig": result["time_sig"],
        "arrangement_plan": summarize_arrangement_plan(params, chords, bars, seed),
        "arrangement_plan_file": arrangement_plan_file,
        "part_files": list(final_part_map.values()),
        "merged_file": merged_path,
    }
    _save_session(os.path.join(out_dir, "session_regenerate.json"), regen_state)
    print("\n完了! 指定パート再生成 + 既存パート再統合 + All_Parts再構築を実行しました。")


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

    if args.generate_chords:
        print("[2/5] コード進行を生成中...")
    elif args.midi:
        print(f"[2/5] MIDIファイルからコード進行を解析: {args.midi}")
    else:
        print(f"[2/5] テキストからコード進行をパース: {args.chords}")

    chords, key, scale = ENGINE.resolve_chords(args, params, use_llm, generate_chords)
    print(f"       コード: {' | '.join(chords)}")
    print(f"       キー: {key} / スケール: {scale}")

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

    arrangement_plan_file = _maybe_export_arrangement_plan_file(
        args,
        out_dir=out_dir,
        params=params,
        chords=chords,
        bars=args.bars,
        seed=seed,
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
        "arrangement_plan": summarize_arrangement_plan(params, chords, args.bars, seed),
        "arrangement_plan_file": arrangement_plan_file,
        "chords_generated": args.generate_chords,
        "part_files": result["written"],
        "merged_file": result["merged_path"],
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
    parser.add_argument(
        "--prompt",
        type=str,
        default="アニメ風アイリッシュ。冒険感があって少し切ない。フィドルとホイッスル、アコギ、バウロン。",
        help="スタイル・雰囲気の自然言語プロンプト",
    )
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
    parser.add_argument("--save-arrangement-plan", action="store_true", help="arrangement_plan.json も出力する")

    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()
