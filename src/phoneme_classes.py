"""Croatian phoneme class definitions and aliases."""

from __future__ import annotations

from collections.abc import Iterable


PHONEME_CLASSES: dict[str, tuple[str, ...]] = {
    "N": ("m", "n", "nj", "b", "p", "u"),
    "SN": ("v", "g", "o", "h", "l", "lj"),
    "S": ("a", "k", "r", "d", "dž", "f", "ž"),
    "SV": ("č", "e", "š", "t", "đ", "j"),
    "V": ("ć", "i", "c", "z", "s"),
}

CLASS_ALIASES: dict[str, str] = {
    "N": "N",
    "NISKI": "N",
    "SN": "SN",
    "SREDNJENISKI": "SN",
    "S": "S",
    "SREDNJI": "S",
    "SV": "SV",
    "SREDNJEVISOKI": "SV",
    "V": "V",
    "VISOKI": "V",
}

CLASS_NAMES: dict[str, str] = {
    "N": "Niski",
    "SN": "Srednjeniski",
    "S": "Srednji",
    "SV": "Srednjevisoki",
    "V": "Visoki",
}

ALL_PHONEMES: tuple[str, ...] = tuple(
    phoneme for phonemes in PHONEME_CLASSES.values() for phoneme in phonemes
)

PHONEME_TO_CLASS: dict[str, str] = {
    phoneme: class_code
    for class_code, phonemes in PHONEME_CLASSES.items()
    for phoneme in phonemes
}


def normalize_class_name(target_class: str) -> str:
    """Resolve a class code or Croatian class name to its canonical code."""
    key = target_class.strip().upper()
    try:
        return CLASS_ALIASES[key]
    except KeyError as exc:
        allowed = ", ".join(CLASS_ALIASES)
        raise ValueError(f"Unknown phoneme class {target_class!r}. Allowed: {allowed}") from exc


def class_phonemes(target_class: str) -> tuple[str, ...]:
    """Return the phonemes for a target class code or alias."""
    return PHONEME_CLASSES[normalize_class_name(target_class)]


def count_by_class(phonemes: Iterable[str]) -> dict[str, int]:
    """Count phonemes by Croatian phoneme class."""
    counts = {class_code: 0 for class_code in PHONEME_CLASSES}
    for phoneme in phonemes:
        class_code = PHONEME_TO_CLASS.get(phoneme)
        if class_code:
            counts[class_code] += 1
    return counts

