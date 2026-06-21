from chord_parser import estimate_key_and_scale


def test_estimate_key_and_scale_a_natural_minor_progression():
    key, scale = estimate_key_and_scale(["Am", "F", "C", "G"])
    assert key == "A"
    assert scale == "natural_minor"


def test_estimate_key_and_scale_d_natural_minor_progression():
    key, scale = estimate_key_and_scale(["Dm", "Bb", "F", "C"])
    assert key == "D"
    assert scale == "natural_minor"


def test_estimate_key_and_scale_d_dorian_progression():
    key, scale = estimate_key_and_scale(["Dm", "G", "C", "Dm"])
    assert key == "D"
    assert scale == "dorian"


def test_estimate_key_and_scale_c_major_progression():
    key, scale = estimate_key_and_scale(["C", "F", "G", "C"])
    assert key == "C"
    assert scale == "major"
