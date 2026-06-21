from main import build_generators, _variation_preset


def test_build_generators_includes_piano_and_lead_when_enabled():
    params = {
        "parts": {
            "drums": False,
            "percussion": False,
            "bass": True,
            "acoustic_guitar": False,
            "fiddle": False,
            "tin_whistle": False,
            "pad_strings": False,
            "piano": True,
            "lead_synth": True,
        },
        "energy": 70,
        "density": 60,
        "complexity": 60,
        "humanize": 70,
        "anime": 70,
        "folk": 70,
        "rock": 20,
        "orchestral": 50,
        "weirdness": 10,
    }
    gens = build_generators(["Dm", "Bb", "F", "C"], "D", "dorian", params, 4, 480, (6, 8), 42)
    assert "Piano" in gens
    assert "Lead" in gens
    assert "Bass" in gens
    assert "ChordTrack" in gens


def test_variation_preset_changes_characteristics():
    base = {"style": "anime_irish", "folk": 60, "anime": 60, "rock": 20, "weirdness": 5, "complexity": 50}
    weird = _variation_preset("Weird", base)
    rock = _variation_preset("Rock", base)

    assert weird["weirdness"] > base["weirdness"]
    assert rock["rock"] > base["rock"]
