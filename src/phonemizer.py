"""Deterministic Croatian phonemizer."""

from __future__ import annotations

import re


MULTI_LETTER_PHONEMES = ("dž", "lj", "nj")
ALLOWED_CROATIAN_LETTERS = set("abcčćdđefghijklmnoprsštuvzž")
REMOVABLE_PUNCTUATION_PATTERN = re.compile(r"[^\w\sčćđšž]", flags=re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase text, remove punctuation, and normalize whitespace."""
    lowered = text.lower()
    without_punctuation = REMOVABLE_PUNCTUATION_PATTERN.sub(" ", lowered)
    return WHITESPACE_PATTERN.sub(" ", without_punctuation).strip()


def phonemize(text: str) -> list[str]:
    """Parse Croatian text into phonemes using longest-match-first rules."""
    normalized = normalize_text(text)
    phonemes: list[str] = []
    i = 0
    while i < len(normalized):
        char = normalized[i]
        if char.isspace():
            i += 1
            continue
        matched = False
        for phoneme in MULTI_LETTER_PHONEMES:
            if normalized.startswith(phoneme, i):
                phonemes.append(phoneme)
                i += len(phoneme)
                matched = True
                break
        if matched:
            continue
        phonemes.append(char)
        i += 1
    return phonemes


def words(text: str) -> list[str]:
    """Return normalized word tokens."""
    normalized = normalize_text(text)
    if not normalized:
        return []
    return normalized.split()


def has_only_croatian_text_characters(text: str) -> bool:
    """Check normalized text contains only Croatian letters and spaces."""
    normalized = normalize_text(text)
    return all(char.isspace() or char in ALLOWED_CROATIAN_LETTERS for char in normalized)

