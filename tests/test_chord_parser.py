import mido
from chord_parser import parse_chord_name, parse_midi_to_chords


def test_parse_chord_name_keeps_maj7_not_corrupted():
    root, ctype = parse_chord_name("Cmaj7")
    assert root == "C"
    assert ctype == "maj7"


def test_parse_midi_to_chords_handles_6_8_meter(tmp_path):
    path = tmp_path / "six_eight.mid"
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)

    tr.append(mido.MetaMessage("time_signature", numerator=6, denominator=8, time=0))
    tr.append(mido.MetaMessage("set_tempo", tempo=500000, time=0))

    # bar1 Dm (D F A) for 1440 ticks
    tr.append(mido.Message("note_on", note=62, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_on", note=65, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_on", note=69, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_off", note=62, velocity=0, time=1440, channel=0))
    tr.append(mido.Message("note_off", note=65, velocity=0, time=0, channel=0))
    tr.append(mido.Message("note_off", note=69, velocity=0, time=0, channel=0))

    # bar2 Bb (Bb D F) for 1440 ticks
    tr.append(mido.Message("note_on", note=58, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_on", note=62, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_on", note=65, velocity=90, time=0, channel=0))
    tr.append(mido.Message("note_off", note=58, velocity=0, time=1440, channel=0))
    tr.append(mido.Message("note_off", note=62, velocity=0, time=0, channel=0))
    tr.append(mido.Message("note_off", note=65, velocity=0, time=0, channel=0))

    mid.save(path)
    chords = parse_midi_to_chords(str(path), bars=2)

    assert len(chords) == 2
    assert chords[0].startswith("D")
    assert chords[1].startswith("A#") or chords[1].startswith("Bb")
