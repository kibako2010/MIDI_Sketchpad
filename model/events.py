from dataclasses import dataclass
from typing import Sequence, Tuple, Union

MidiEventTuple = Tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class NoteEvent:
    abs_tick: int
    channel: int
    note: int
    velocity: int
    duration_ticks: int

    def as_tuple(self) -> MidiEventTuple:
        return (
            self.abs_tick,
            self.channel,
            self.note,
            self.velocity,
            self.duration_ticks,
        )

    @classmethod
    def from_tuple(cls, event: Sequence[int]) -> "NoteEvent":
        if len(event) != 5:
            raise ValueError(f"Midi event must have exactly 5 values, got {len(event)}")
        return cls(int(event[0]), int(event[1]), int(event[2]), int(event[3]), int(event[4]))


MidiEventLike = Union[MidiEventTuple, NoteEvent]


def event_to_tuple(event: MidiEventLike) -> MidiEventTuple:
    if isinstance(event, NoteEvent):
        return event.as_tuple()
    if len(event) != 5:
        raise ValueError(f"Midi tuple event must have exactly 5 values, got {len(event)}")
    return (
        int(event[0]),
        int(event[1]),
        int(event[2]),
        int(event[3]),
        int(event[4]),
    )


def event_with_values(
    reference: MidiEventLike,
    abs_tick: int,
    channel: int,
    note: int,
    velocity: int,
    duration_ticks: int,
) -> MidiEventLike:
    if isinstance(reference, NoteEvent):
        return NoteEvent(abs_tick, channel, note, velocity, duration_ticks)
    return (abs_tick, channel, note, velocity, duration_ticks)
