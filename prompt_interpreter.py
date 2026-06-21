# prompt_interpreter.py
"""
自然言語プロンプト → 内部JSONパラメータ変換。
LLMモード: Ollamaに投げて詳細なパラメータを生成。
フォールバック: キーワードマッチング。
"""

import json
import re
import requests
from typing import Dict, Any
from config import OLLAMA_URL, OLLAMA_MODEL


SYSTEM_PROMPT = """\
You are a music style parameter extractor for a MIDI generation tool.
Given a natural language description, output ONLY valid JSON with exactly these fields:

{
  "style": string,
  "mood": list of strings,
  "tempo_feel": string,
  "energy": int 0-100,
  "density": int 0-100,
  "complexity": int 0-100,
  "anime": int 0-100,
  "folk": int 0-100,
  "rock": int 0-100,
  "orchestral": int 0-100,
  "humanize": int 0-100,
  "swing": int 0-100,
  "weirdness": int 0-100,
  "parts": {
    "drums": bool,
    "percussion": bool,
    "bass": bool,
    "acoustic_guitar": bool,
    "fiddle": bool,
    "tin_whistle": bool,
    "pad_strings": bool,
    "piano": bool,
    "lead_synth": bool
  },
  "generation_notes": {
    "fiddle": string,
    "tin_whistle": string,
    "guitar": string,
    "percussion": string,
    "bass": string,
    "strings": string
  }
}

Style values: anime_irish, city_pop, celtic_rock, jazz_ballad, synthwave,
              trap, uk_garage, bossa_nova, funk, ambient, drum_n_bass
Tempo feel values: fast_6_8, medium_6_8, slow_6_8,
                   fast_4_4, medium_4_4, slow_4_4, fast_12_8

For anime_irish style:
- Set folk: 70-90, anime: 70-90
- tempo_feel: fast_6_8 or medium_6_8
- drums/percussion/bass/acoustic_guitar/fiddle/tin_whistle/pad_strings: true
- generation_notes should describe Irish jig characteristics

Output ONLY the JSON. No explanation, no markdown."""


KEYWORD_STYLES = {
    "anime_irish": ["アニメ", "アイリッシュ", "irish", "anime", "ケルト", "celtic"],
    "city_pop":    ["シティポップ", "city pop", "シティ"],
    "celtic_rock": ["ケルトロック", "celtic rock"],
    "jazz_ballad": ["ジャズバラード", "jazz", "バラード"],
    "synthwave":   ["シンセウェーブ", "synthwave", "80s"],
    "trap":        ["トラップ", "trap", "ヒップホップ"],
    "uk_garage":   ["uk garage", "ガレージ"],
    "bossa_nova":  ["ボサノバ", "bossa"],
    "funk":        ["ファンク", "funk"],
    "ambient":     ["アンビエント", "ambient"],
    "drum_n_bass": ["ドラムンベース", "drum and bass", "dnb"],
}

KEYWORD_MOODS = {
    "adventurous": ["冒険", "疾走", "adventure"],
    "bittersweet": ["切ない", "bittersweet", "悲しい"],
    "bright":      ["明るい", "bright", "楽しい"],
    "dark":        ["暗い", "dark", "重い"],
    "dramatic":    ["ドラマ", "dramatic", "壮大"],
    "relaxed":     ["穏やか", "relaxed", "ゆったり"],
    "energetic":   ["元気", "energetic", "激しい"],
}

STYLE_DEFAULT_PARTS = {
    "anime_irish": {
        "drums": True, "percussion": True, "bass": True,
        "acoustic_guitar": True, "fiddle": True, "tin_whistle": True,
        "pad_strings": True, "piano": False, "lead_synth": False,
    },
    "city_pop": {
        "drums": True, "percussion": False, "bass": True,
        "acoustic_guitar": False, "fiddle": False, "tin_whistle": False,
        "pad_strings": True, "piano": True, "lead_synth": False,
    },
    "jazz_ballad": {
        "drums": True, "percussion": False, "bass": True,
        "acoustic_guitar": False, "fiddle": False, "tin_whistle": False,
        "pad_strings": True, "piano": True, "lead_synth": False,
    },
}

PART_KEYWORDS = {
    "drums":           ["ドラム", "drum"],
    "percussion":      ["バウロン", "bodhran", "パーカッション", "percussion"],
    "bass":            ["ベース", "bass"],
    "acoustic_guitar": ["ギター", "guitar", "アコギ"],
    "fiddle":          ["フィドル", "fiddle", "バイオリン"],
    "tin_whistle":     ["ホイッスル", "whistle", "フルート"],
    "pad_strings":     ["ストリングス", "strings", "パッド", "弦", "pad"],
    "piano":           ["ピアノ", "piano", "keys"],
    "lead_synth":      ["シンセ", "synth", "リード"],
}

EXCLUDE_KEYWORDS = {
    "drums":           ["ドラムなし", "ドラム抜き"],
    "percussion":      ["パーカッションなし", "パーカッション抜き"],
    "bass":            ["ベースなし", "ベース抜き"],
    "acoustic_guitar": ["ギターなし", "ギター抜き"],
    "fiddle":          ["フィドルなし"],
    "tin_whistle":     ["ホイッスルなし"],
    "pad_strings":     ["ストリングスなし", "パッドなし"],
    "piano":           ["ピアノなし"],
    "lead_synth":      ["シンセなし"],
}


def _get_default_parts(style: str) -> dict:
    return dict(STYLE_DEFAULT_PARTS.get(
        style, STYLE_DEFAULT_PARTS["anime_irish"]
    ))


def _validate_and_fill(params: Dict[str, Any],
                        prompt: str) -> Dict[str, Any]:
    """
    LLMの出力に抜け・型エラーがあれば補完する。
    """
    style = params.get("style", "anime_irish")

    # 数値パラメータのデフォルト
    int_fields = {
        "energy": 70, "density": 60, "complexity": 60,
        "anime": 70,  "folk": 70,    "rock": 20,
        "orchestral": 45, "humanize": 70, "swing": 20, "weirdness": 10,
    }
    for field, default in int_fields.items():
        val = params.get(field, default)
        try:
            params[field] = max(0, min(100, int(val)))
        except (TypeError, ValueError):
            params[field] = default

    # mood
    if not isinstance(params.get("mood"), list) or not params["mood"]:
        params["mood"] = ["adventurous"]

    # tempo_feel
    if not params.get("tempo_feel"):
        if "irish" in style or "celtic" in style:
            params["tempo_feel"] = "fast_6_8"
        else:
            params["tempo_feel"] = "medium_4_4"

    # parts: 抜けているキーをデフォルトで補完
    default_parts = _get_default_parts(style)
    parts = params.get("parts", {})
    if not isinstance(parts, dict):
        parts = {}
    for key, default_val in default_parts.items():
        if key not in parts:
            parts[key] = default_val
        else:
            parts[key] = bool(parts[key])
    params["parts"] = parts

    # generation_notes
    if not isinstance(params.get("generation_notes"), dict):
        params["generation_notes"] = {
            "fiddle":      "jig-like motif with ornamentation",
            "tin_whistle": "call and response countermelody",
            "guitar":      "driving acoustic strum",
            "percussion":  "bodhran-like pulse",
            "bass":        "root-fifth with approach notes",
            "strings":     "sustained anime-style lift",
        }

    return params


def _keyword_fallback(prompt: str) -> Dict[str, Any]:
    prompt_lower = prompt.lower()

    style = "anime_irish"
    for s, keywords in KEYWORD_STYLES.items():
        if any(kw in prompt_lower for kw in keywords):
            style = s
            break

    moods = [m for m, kws in KEYWORD_MOODS.items()
             if any(kw in prompt_lower for kw in kws)]
    if not moods:
        moods = ["adventurous"]

    if any(w in prompt_lower for w in ["速め", "激しい", "fast", "energetic", "疾走"]):
        energy = 85
    elif any(w in prompt_lower for w in ["穏やか", "ゆっくり", "slow", "soft"]):
        energy = 35
    else:
        energy = 70

    tempo_feel = ("fast_6_8"
                  if "irish" in style or "celtic" in style or "anime_irish" in style
                  else "medium_4_4")

    parts = _get_default_parts(style)
    for part, keywords in PART_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            parts[part] = True
    for part, keywords in EXCLUDE_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            parts[part] = False
    parts["drums"] = True
    parts["bass"]  = True

    anime_score = 80 if ("anime" in style or "アニメ" in prompt_lower) else 40
    folk_score  = 80 if ("irish" in style or "アイリッシュ" in prompt_lower) else 30
    rock_score  = 70 if "rock" in style else 20

    return {
        "style":      style,
        "mood":       moods,
        "tempo_feel": tempo_feel,
        "energy":     energy,
        "density":    int(energy * 0.85),
        "complexity": 60,
        "anime":      anime_score,
        "folk":       folk_score,
        "rock":       rock_score,
        "orchestral": 45,
        "humanize":   70,
        "swing":      20,
        "weirdness":  10,
        "parts":      parts,
        "generation_notes": {
            "fiddle":      "jig-like motif with ornamentation",
            "tin_whistle": "call and response countermelody",
            "guitar":      "driving acoustic strum",
            "percussion":  "bodhran-like pulse",
            "bass":        "root-fifth with approach notes",
            "strings":     "sustained anime-style lift",
        },
    }

def _call_lm_studio(prompt: str) -> str:
    """LM Studio / OpenAI互換APIを呼び出す"""
    payload = {
        "model":    OLLAMA_MODEL,
        "messages": [
            {"role": "system",  "content": SYSTEM_PROMPT},
            {"role": "user",    "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens":  1024,
        "stream":      False,
    }
    resp = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=60,
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def interpret_prompt(prompt: str, use_llm: bool = True) -> Dict[str, Any]:
    if not use_llm:
        return _keyword_fallback(prompt)

    try:
        raw   = _call_lm_studio(prompt)

        # JSONブロックを抽出
        match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if not match:
            match = re.search(r"\{.*\}", raw, re.DOTALL)

        if match:
            json_str = match.group(1) if match.lastindex else match.group()
            params   = json.loads(json_str)
            params   = _validate_and_fill(params, prompt)
            print("       [LLM] プロンプト解釈成功")
            return params

        print("[WARN] LLM response has no JSON. Using fallback.")
        return _keyword_fallback(prompt)

    except Exception as e:
        print(f"[WARN] LLM call failed ({e}). Using keyword fallback.")
        return _keyword_fallback(prompt)