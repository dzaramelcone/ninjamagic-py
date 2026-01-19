from ninjamagic.util import auto_cap


def test_auto_cap_handles_apostrophes_in_words():
    text = (
        "the broadsword cleaves clean through bone! "
        "the wanderer's head is sent tumbling! "
        "his corpse falls."
    )
    expected = (
        "The broadsword cleaves clean through bone! "
        "The wanderer's head is sent tumbling! "
        "His corpse falls."
    )
    assert auto_cap(text) == expected


def test_auto_cap_ignores_text_in_quote_pairs():
    text = "he shouts! 'do not move.'"
    expected = "He shouts! 'do not move.'"
    assert auto_cap(text) == expected


def test_auto_cap_unmatched_quote_does_not_disable_caps():
    text = "he says 'hello! the night falls."
    expected = "He says 'hello! The night falls."
    assert auto_cap(text) == expected


def test_auto_cap_normalizes_sentence_spacing():
    text = "hello!   again."
    expected = "Hello!   Again."
    assert auto_cap(text) == expected


def test_auto_cap_doesnt_normalize_quoted_sentence_spacing():
    text = "'hello!   again.'"
    expected = text
    assert auto_cap(text) == expected
