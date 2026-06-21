# config.py
from dataclasses import dataclass, field
from typing import Dict, Any
import os

# ---- 音名定義 ----
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]

# ---- MIDIチャンネル定義 (0-indexed) ----
CH_PIANO      = 0   # Ch1
CH_BASS       = 1   # Ch2
CH_GUITAR     = 2   # Ch3
CH_PAD        = 3   # Ch4
CH_LEAD       = 4   # Ch5
CH_FIDDLE     = 5   # Ch6
CH_WHISTLE    = 6   # Ch7
CH_BRASS      = 7   # Ch8
CH_PERCUSSION = 8   # Ch9
CH_DRUMS      = 9   # Ch10 (GM Drums)

# ---- 音域定義 (MIDI note number) ----
RANGE = {
    "bass":       (28, 55),   # E1 - G3
    "guitar":     (40, 76),   # E2 - E5
    "fiddle":     (55, 93),   # G3 - A6
    "whistle":    (74, 98),   # D5 - D7
    "pad":        (48, 84),   # C3 - C6
    "piano":      (48, 84),   # C3 - C6
    "lead":       (60, 96),   # C4 - C7
    "drums":      (35, 81),
    "percussion": (35, 81),
}

# ---- GM Drum Note番号 ----
DRUM = {
    "kick":         36,
    "snare":        38,
    "snare_rim":    37,
    "hihat_closed": 42,
    "hihat_open":   46,
    "hihat_pedal":  44,
    "ride":         51,
    "crash":        49,
    "tom_hi":       50,
    "tom_mid":      47,
    "tom_lo":       45,
    "tambourine":   54,
    "cowbell":      56,
    "clap":         39,
}

# ---- スケール定義 (半音インターバル) ----
SCALES = {
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian":        [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":    [0, 2, 4, 5, 7, 9, 10],
    "major":         [0, 2, 4, 5, 7, 9, 11],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
}

# ---- コード構成音定義 (ルートからの半音インターバル) ----
CHORD_INTERVALS = {
    "maj":    [0, 4, 7],
    "min":    [0, 3, 7],
    "7":      [0, 4, 7, 10],
    "maj7":   [0, 4, 7, 11],
    "min7":   [0, 3, 7, 10],
    "dim":    [0, 3, 6],
    "aug":    [0, 4, 8],
    "sus2":   [0, 2, 7],
    "sus4":   [0, 5, 7],
    "add9":   [0, 2, 4, 7],
    "min7b5": [0, 3, 6, 10],
    "6":      [0, 4, 7, 9],
    "min6":   [0, 3, 7, 9],
    "9":      [0, 4, 7, 10, 14],
    "maj9":   [0, 4, 7, 11, 14],
}

# ---- LM Studio設定 ----
# 優先: 環境変数 > デフォルト(localhost)
LM_STUDIO_API_URL = os.getenv(
    "LM_STUDIO_API_URL",
    "http://localhost:1234/v1/chat/completions",
)
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "local-model")

# ---- 互換エイリアス（既存コード向け） ----
OLLAMA_URL = LM_STUDIO_API_URL
OLLAMA_MODEL = LM_STUDIO_MODEL

# ---- デフォルト出力ディレクトリ ----
OUTPUT_DIR = "./output"

# ---- Anime Irish 代表的コード進行 ----
ANIME_IRISH_PROGRESSIONS = [
    ["Dm", "C",  "Bb", "C"],
    ["Dm", "Bb", "F",  "C"],
    ["Am", "F",  "C",  "G"],
    ["Em", "C",  "G",  "D"],
]
