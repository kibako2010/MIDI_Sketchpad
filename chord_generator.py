# chord_generator.py
"""
コード進行生成モジュール。
LLMが使える場合はOllamaに生成させる。
使えない場合はスタイル別テンプレートから選ぶ。
"""

import json
import re
import requests
from typing import List, Dict, Any
from config import OLLAMA_URL, OLLAMA_MODEL


# ---- スタイル別コード進行テンプレート ----
CHORD_TEMPLATES = {
    "anime_irish": [
        ["Dm", "Bb", "F",  "C"],
        ["Dm", "Bb", "C",  "Dm"],
        ["Am", "F",  "C",  "G"],
        ["Em", "C",  "G",  "D"],
        ["Dm", "C",  "Bb", "C"],
        ["Am", "G",  "F",  "G"],
        ["Dm", "F",  "C",  "Bb"],
        ["Em", "G",  "D",  "A"],
    ],
    "city_pop": [
        ["Cmaj7", "Am7",  "Dm7",  "G7"],
        ["Fmaj7", "Em7",  "Am7",  "Dm7"],
        ["Cmaj7", "Fmaj7","Em7",  "Am7"],
        ["Amaj7", "F#m7", "Bm7",  "E7"],
    ],
    "jazz_ballad": [
        ["Cmaj7", "Am7",  "Dm7",  "G7"],
        ["Fmaj7", "Bb7",  "Cmaj7","A7"],
        ["Dm7",   "G7",   "Cmaj7","A7"],
        ["Am7",   "D7",   "Gmaj7","E7"],
    ],
    "celtic_rock": [
        ["Am", "G",  "F",  "G"],
        ["Dm", "Am", "Bb", "C"],
        ["Em", "D",  "C",  "D"],
        ["Am", "F",  "G",  "Am"],
    ],
    "synthwave": [
        ["Am", "F",  "C",  "G"],
        ["Dm", "Bb", "F",  "C"],
        ["Cm", "Ab", "Eb", "Bb"],
        ["Em", "C",  "G",  "D"],
    ],
    "trap": [
        ["Am", "F",  "C",  "G"],
        ["Cm", "Ab", "Bb", "Cm"],
        ["Dm", "Bb", "F",  "C"],
        ["Em", "C",  "D",  "Em"],
    ],
}

CHORD_GEN_PROMPT = """You are a music theory expert and chord progression generator.
Generate a chord progression for the following style description.

Rules:
- Output ONLY valid JSON, no explanation
- Generate exactly {bars} chords (one per bar)
- Use standard chord notation: C, Dm, G7, Cmaj7, Am7, etc.
- Match the style, mood, and key feel described
- For anime_irish: prefer natural minor / dorian, use Dm/Am/Em based progressions
- For city_pop: use jazz-influenced chords with 7ths and 9ths
- For jazz_ballad: use ii-V-I style progressions
- Output format: {{"chords": ["Dm", "Bb", "F", "C", ...], "key": "D", "scale": "dorian"}}

Style: {style}
Mood: {mood}
Energy: {energy}
Bars: {bars}
Additional notes: {notes}

Output ONLY the JSON object."""


def generate_chords_llm(
    params: Dict[str, Any],
    bars:   int,
) -> Dict[str, Any]:
    from config import OLLAMA_URL, OLLAMA_MODEL

    prompt = CHORD_GEN_PROMPT.format(
        style  = params.get("style",  "anime_irish"),
        mood   = ", ".join(params.get("mood", ["adventurous"])),
        energy = params.get("energy", 70),
        bars   = bars,
        notes  = params.get("generation_notes", {}).get("bass", ""),
    )

    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens":  512,
        "stream":      False,
    }
    try:
        resp = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        raw   = resp.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            chords = result.get("chords", [])
            if len(chords) < bars:
                while len(chords) < bars:
                    chords.extend(chords)
                chords = chords[:bars]
            elif len(chords) > bars:
                chords = chords[:bars]
            return {
                "chords": chords,
                "key":    result.get("key",   "D"),
                "scale":  result.get("scale", "dorian"),
            }
    except Exception as e:
        print(f"[WARN] LLM chord generation failed ({e}). Using template.")

    return None


def generate_chords_template(
    params: Dict[str, Any],
    bars:   int,
    seed:   int = 42,
) -> Dict[str, Any]:
    """
    テンプレートからコード進行を選んで返す。
    barsに合わせてループ展開する。
    """
    import random
    rng    = random.Random(seed)
    style  = params.get("style", "anime_irish")
    pool   = CHORD_TEMPLATES.get(style, CHORD_TEMPLATES["anime_irish"])
    base   = rng.choice(pool)

    # barsに合わせてループ展開
    chords = []
    while len(chords) < bars:
        chords.extend(base)
    chords = chords[:bars]

    # キーとスケールをテンプレートから推定
    from chord_parser import estimate_key_and_scale
    key, scale = estimate_key_and_scale(chords)

    # anime_irishはdorianを優先
    if "irish" in style or "celtic" in style:
        scale = "dorian"

    return {
        "chords": chords,
        "key":    key,
        "scale":  scale,
    }


def generate_chords(
    params:  Dict[str, Any],
    bars:    int,
    seed:    int  = 42,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    コード進行を生成するメインエントリ。
    LLM → テンプレートフォールバックの順で試みる。
    """
    if use_llm:
        result = generate_chords_llm(params, bars)
        if result:
            print(f"       [LLM] コード生成成功: {result['chords']}")
            return result
        print("       [WARN] LLMフォールバック → テンプレートを使用")

    result = generate_chords_template(params, bars, seed)
    print(f"       [Template] コード生成: {result['chords']}")
    return result
