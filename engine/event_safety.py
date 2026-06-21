from typing import Dict, Iterable, List, Tuple

MidiEvent = Tuple[int, int, int, int, int]


def compute_total_ticks(ticks_per_beat: int, time_sig: tuple[int, int], bars: int) -> int:
    numerator, denominator = time_sig
    ticks_per_bar = int(ticks_per_beat * numerator * 4 / denominator)
    return max(0, ticks_per_bar * int(bars))


def _clip_event_list(events: Iterable[MidiEvent], total_ticks: int) -> List[MidiEvent]:
    safe_events: List[MidiEvent] = []

    for event in events:
        start_tick, channel, note, velocity, duration = event

        start_tick = int(start_tick)
        channel = int(channel)
        note = max(0, min(127, int(note)))
        velocity = max(1, min(127, int(velocity)))
        duration = int(duration)

        if start_tick < 0:
            start_tick = 0
        if start_tick >= total_ticks:
            continue
        if duration <= 0:
            continue

        if start_tick + duration > total_ticks:
            duration = total_ticks - start_tick
        if duration <= 0:
            continue

        safe_events.append((start_tick, channel, note, velocity, duration))

    return safe_events


def clip_events_to_song_bounds(
    events_by_part: Dict[str, Iterable[MidiEvent]],
    bars: int,
    ticks_per_beat: int,
    time_sig: tuple[int, int],
) -> Dict[str, List[MidiEvent]]:
    total_ticks = compute_total_ticks(ticks_per_beat, time_sig, bars)
    return {
        part_name: _clip_event_list(events, total_ticks)
        for part_name, events in events_by_part.items()
    }
