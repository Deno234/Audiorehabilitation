from src.phoneme_classes import class_phonemes, normalize_class_name
from src.validators import (
    FAIL_DUPLICATE,
    FAIL_INVALID_CHARACTERS,
    FAIL_REPEATED_WORDS,
    FAIL_WRONG_WORD_COUNT,
    DictionaryValidator,
    validate_candidate,
)


def test_class_aliases():
    assert normalize_class_name("Niski") == "N"
    assert normalize_class_name("Srednjeniski") == "SN"
    assert "lj" in class_phonemes("Srednjeniski")


def test_invalid_characters_detected():
    result = validate_candidate("test123", "V", 50, "word")
    assert FAIL_INVALID_CHARACTERS in result.failure_reasons


def test_duplicate_detection():
    seen = {"panj"}
    result = validate_candidate("panj", "N", 50, "word", seen_normalized=seen)
    assert FAIL_DUPLICATE in result.failure_reasons


def test_repeated_word_detection():
    result = validate_candidate("škola škola", "SV", 40, "sentence")
    assert FAIL_REPEATED_WORDS in result.failure_reasons


def test_sentence_word_count_detection():
    result = validate_candidate("puna banana", "N", 40, "sentence")
    assert FAIL_WRONG_WORD_COUNT in result.failure_reasons


def test_dictionary_none_passes_dictionary_check():
    dictionary = DictionaryValidator(mode="none")
    result = validate_candidate("panj", "N", 50, "word", dictionary=dictionary)
    assert "dictionary_failed" not in result.failure_reasons

