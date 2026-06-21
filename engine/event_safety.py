from typing import Iterable, List, Tuple

MidiEvent = Tuple[int, int, int, int, int]


def compute_total_ticks(ticks_per_beat: int, time_sig: tuple[int, int], bars: int) -> int:
    num, den = time_sig
    ticks_per_bar = int(ticks_per_beat * num * 4 / den)
    return max(0, ticks_per_bar * int(bars))


def clip_events_to_song_bounds(events: Iterable[MidiEvent], total_ticks: int) -> List[MidiEvent]:
    safe_events: List[MidiEvent] = []

    for event in events:
        start, channel, note, velocity, duration = event

        start = int(start)
        channel = int(channel)
        note = max(0, min(127, int(note)))
        velocity = max(1, min(127, int(velocity)))
        duration = int(duration)

        if start < 0:
            start = 0
        if start >= total_ticks:
            continue
        if duration <= 0:
            continue

        if start + duration > total_ticks:
            duration = total_ticks - start
        if duration <= 0:
            continue

        safe_events.append((start, channel, note, velocity, duration))

    return safe_events
