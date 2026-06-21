from engine.event_safety import clip_events_to_song_bounds, compute_total_ticks
from engine.generation_engine import GenerationEngine
from generators.drums import DrumsGenerator
from generators.fiddle import FiddleGenerator
from generators.whistle import WhistleGenerator


def test_clip_events_to_song_bounds_applies_all_safety_rules():
    total_ticks = 100
    events = [
        (-10, 9, 140, 200, 20),   # start<0 + note/vel clamp
        (95, 9, 60, 90, 20),      # end overflow -> clip duration
        (100, 9, 60, 90, 10),     # start>=total -> drop
        (70, 9, 60, 90, 0),       # duration<=0 -> drop
        (80, 9, -5, -3, 10),      # note/vel lower clamp
    ]

    clipped_map = clip_events_to_song_bounds(
        {"Drums": events},
        bars=1,
        ticks_per_beat=100,
        time_sig=(1, 4),
    )

    assert clipped_map["Drums"] == [
        (0, 9, 127, 127, 20),
        (95, 9, 60, 90, 5),
        (80, 9, 0, 1, 10),
    ]


def test_generation_engine_events_are_clipped_within_song_bounds():
    engine = GenerationEngine()
    bars = 1
    render = engine.render_events(
        chords=["Am"],
        key="A",
        scale="natural_minor",
        params={
            "style": "anime_irish",
            "energy": 100,
            "density": 100,
            "complexity": 60,
            "humanize": 0,
            "post_humanize": True,
            "parts": {
                "drums": True,
                "percussion": True,
                "bass": False,
                "acoustic_guitar": False,
                "fiddle": False,
                "tin_whistle": False,
                "pad_strings": False,
                "piano": False,
                "lead_synth": False,
            },
        },
        bars=bars,
        seed=42,
    )

    total_ticks = compute_total_ticks(render["ticks_per_beat"], tuple(render["time_sig"]), bars)
    assert total_ticks > 0

    for events in render["events"].values():
        for start, _ch, _note, _vel, duration in events:
            assert 0 <= start < total_ticks
            assert duration > 0
            assert start + duration <= total_ticks


def test_drums_last_bar_prefers_closed_hihat_for_tail_safety():
    bars = 2
    drums = DrumsGenerator(
        chords=["Am", "F"],
        key="A",
        scale="natural_minor",
        params={"energy": 100, "density": 100, "humanize": 0, "rock": 0},
        bars=bars,
        time_sig=(6, 8),
        seed=42,
    )

    events = drums.generate()
    last_bar_start = drums.ticks_per_bar * (bars - 1)
    hihat_open_note = 46

    # 最終小節ではopen hihatを使わずclose優先にする。
    last_bar_open_hits = [ev for ev in events if ev[0] >= last_bar_start and ev[2] == hihat_open_note]
    assert not last_bar_open_hits


def test_fiddle_and_whistle_notes_snap_to_scale_even_with_weirdness():
    params = {
        "weirdness": 100,
        "density": 100,
        "energy": 80,
        "anime": 40,
        "folk": 70,
        "complexity": 60,
    }
    chords = ["Am", "E7", "F", "G"]

    fiddle = FiddleGenerator(
        chords=chords,
        key="A",
        scale="natural_minor",
        params=params,
        bars=4,
        time_sig=(6, 8),
        seed=7,
    )
    whistle = WhistleGenerator(
        chords=chords,
        key="A",
        scale="natural_minor",
        params=params,
        bars=4,
        time_sig=(6, 8),
        seed=11,
    )

    fiddle_scale_notes = set(fiddle._build_scale(fiddle._root_pc()))
    whistle_scale_notes = set(whistle._build_scale(whistle._root_pc()))

    for _start, _ch, note, _vel, _dur in fiddle.generate():
        assert note in fiddle_scale_notes

    for _start, _ch, note, _vel, _dur in whistle.generate():
        assert note in whistle_scale_notes
