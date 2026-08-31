from capture_keys import applyCaptureKey


def test_append_char():
    assert applyCaptureKey("ab", "a", "c") == "abc"


def test_space_and_enter():
    assert applyCaptureKey("a", "space", " ") == "a "
    assert applyCaptureKey("a", "enter", None) == "a\n"


def test_backspace():
    assert applyCaptureKey("ab", "backspace", None) == "a"
    assert applyCaptureKey("", "backspace", None) == ""
    assert applyCaptureKey("ab", "\x08", None) == "a"


def test_delete_passes_through():
    assert applyCaptureKey("ab", "delete", None) is None


def test_pass_through_unknown_returns_none():
    assert applyCaptureKey("ab", "cmd", None) is None
    assert applyCaptureKey("ab", "ctrl_l", None) is None
