from humanizer import apply_humanize
from midi_renderer import _events_to_track
from model.events import NoteEvent, event_to_tuple


def test_humanize_accepts_noteevent_and_preserves_type():
    events = [
        NoteEvent(0, 0, 60, 100, 240),
        NoteEvent(240, 9, 36, 110, 120),
    ]

    out = apply_humanize(events, {"humanize": 0, "swing": 0}, seed=123)

    assert len(out) == 2
    assert all(isinstance(ev, NoteEvent) for ev in out)
    assert event_to_tuple(out[0]) == (0, 0, 60, 100, 240)
    assert event_to_tuple(out[1]) == (240, 9, 36, 110, 120)


def test_humanize_accepts_legacy_tuple_events():
    events = [(0, 0, 64, 96, 240)]

    out = apply_humanize(events, {"humanize": 0, "swing": 0}, seed=999)

    assert isinstance(out[0], tuple)
    assert out[0] == (0, 0, 64, 96, 240)


def test_midi_renderer_accepts_noteevent_inputs():
    events = [NoteEvent(0, 1, 48, 90, 240)]

    track = _events_to_track(events, program=32, channel=1, track_name="Bass")

    note_on = [msg for msg in track if getattr(msg, "type", "") == "note_on"]
    note_off = [msg for msg in track if getattr(msg, "type", "") == "note_off"]
    assert len(note_on) == 1
    assert len(note_off) == 1
