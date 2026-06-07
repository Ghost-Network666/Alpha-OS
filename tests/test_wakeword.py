from alpha_os.voice.wakeword import (
    contains_wake_word,
    normalize_wake_word,
    strip_wake_word,
)


def test_normalize_wake_word_defaults():
    assert normalize_wake_word("") == "hey alpha"
    assert normalize_wake_word("  Hey Alpha ") == "hey alpha"


def test_contains_wake_word_variants():
    assert contains_wake_word("hey alpha what time is it")
    assert contains_wake_word("HEY ALFA status")
    assert not contains_wake_word("alpha only")


def test_strip_wake_word():
    assert strip_wake_word("hey alpha open terminal") == "open terminal"
    assert strip_wake_word("status report") == "status report"