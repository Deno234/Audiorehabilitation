from src.phonemizer import phonemize


def test_multi_letter_phonemes():
    assert phonemize("panj") == ["p", "a", "nj"]
    assert phonemize("polje") == ["p", "o", "lj", "e"]
    assert phonemize("džep") == ["dž", "e", "p"]


def test_sentence_phonemizer_treats_nj_as_one():
    assert phonemize("puno banana u panju") == [
        "p",
        "u",
        "n",
        "o",
        "b",
        "a",
        "n",
        "a",
        "n",
        "a",
        "u",
        "p",
        "a",
        "nj",
        "u",
    ]

