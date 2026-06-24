"""Candidate validation and saturation calculation."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import csv
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .phoneme_classes import class_phonemes, normalize_class_name
from .phonemizer import has_only_croatian_text_characters, normalize_text, phonemize, words


FAIL_FAILED_SATURATION = "failed_saturation"
FAIL_INVALID_CHARACTERS = "invalid_characters"
FAIL_WRONG_WORD_COUNT = "wrong_word_count"
FAIL_DUPLICATE = "duplicate"
FAIL_REPEATED_WORDS = "repeated_words"
FAIL_DICTIONARY_FAILED = "dictionary_failed"


@dataclass(frozen=True)
class SaturationResult:
    original_text: str
    normalized_text: str
    phonemes: list[str]
    total_phonemes: int
    target_class: str
    target_count: int
    saturation_percentage: float
    passes_saturation: bool


@dataclass(frozen=True)
class ValidationResult:
    original_text: str
    normalized_text: str
    phonemes: list[str]
    total_phonemes: int
    target_class: str
    target_count: int
    saturation_percentage: float
    saturation_level: float
    passes_saturation: bool
    is_valid: bool
    failure_reasons: list[str]
    word_count: int
    text_type: str
    dictionary_mode: str
    dictionary_backend: str
    dictionary_word_validity: str
    dictionary_invalid_words: str
    dictionary_unknown_words: str
    dictionary_review_complete: str

    def to_row(self) -> dict[str, Any]:
        row = asdict(self)
        row["phonemes"] = " ".join(self.phonemes)
        row["failure_reasons"] = ";".join(self.failure_reasons)
        return row


def calculate_saturation(
    candidate: str, target_class: str, saturation_level: float
) -> SaturationResult:
    """Calculate target-class saturation for a candidate."""
    canonical_class = normalize_class_name(target_class)
    candidate_phonemes = phonemize(candidate)
    target_phonemes = set(class_phonemes(canonical_class))
    target_count = sum(1 for phoneme in candidate_phonemes if phoneme in target_phonemes)
    total = len(candidate_phonemes)
    percentage = (target_count / total * 100.0) if total else 0.0
    return SaturationResult(
        original_text=candidate,
        normalized_text=normalize_text(candidate),
        phonemes=candidate_phonemes,
        total_phonemes=total,
        target_class=canonical_class,
        target_count=target_count,
        saturation_percentage=percentage,
        passes_saturation=percentage >= float(saturation_level),
    )


class DictionaryValidator:
    """Pluggable dictionary/manual-review validation."""

    def __init__(
        self,
        mode: str = "none",
        local_wordlist_path: str | None = None,
        manual_review_csv_path: str | None = None,
        hunspell_executable: str = "hunspell",
        hunspell_dictionary: str = "hr_HR",
    ) -> None:
        self.mode = mode
        self.hunspell_executable = hunspell_executable
        self.hunspell_dictionary = hunspell_dictionary
        self._hunspell_cache: dict[str, str] = {}
        self.local_words = self._load_wordlist(local_wordlist_path) if mode == "local_wordlist" else set()
        self.manual_review = (
            self._load_manual_review(manual_review_csv_path)
            if mode == "manual_review_csv"
            else {}
        )
        if mode == "hunspell_cli":
            self._check_hunspell_ready()

    @staticmethod
    def _load_wordlist(path: str | None) -> set[str]:
        if not path:
            return set()
        wordlist_path = Path(path)
        if not wordlist_path.exists():
            return set()
        with wordlist_path.open("r", encoding="utf-8", newline="") as handle:
            return {normalize_text(line).strip() for line in handle if normalize_text(line).strip()}

    @staticmethod
    def _load_manual_review(path: str | None) -> dict[str, bool]:
        if not path:
            return {}
        review_path = Path(path)
        if not review_path.exists():
            return {}
        with review_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            result: dict[str, bool] = {}
            for row in reader:
                candidate = normalize_text(row.get("candidate", ""))
                valid_value = (row.get("valid") or row.get("is_valid") or "").strip().lower()
                if candidate:
                    result[candidate] = valid_value in {"1", "true", "yes", "y", "valid"}
            return result

    def validate(self, candidate: str) -> bool:
        status = self.check_candidate(candidate)
        return status["dictionary_word_validity"] == "yes"

    def check_candidate(self, candidate: str) -> dict[str, str]:
        normalized_words = words(candidate)
        normalized_candidate = normalize_text(candidate)
        backend = self.mode
        if self.mode == "none":
            return self._candidate_status(backend, "yes", [], [])
        if self.mode == "local_wordlist":
            invalid = [word for word in normalized_words if word not in self.local_words]
            return self._candidate_status(
                backend,
                "yes" if normalized_words and not invalid else "no",
                invalid,
                [],
            )
        if self.mode == "manual_review_csv":
            valid = self.manual_review.get(normalized_candidate)
            if valid is None:
                return self._candidate_status(backend, "unsure", [], normalized_words)
            return self._candidate_status(backend, "yes" if valid else "no", [] if valid else normalized_words, [])
        if self.mode == "hunspell_cli":
            invalid: list[str] = []
            unknown: list[str] = []
            for word in normalized_words:
                try:
                    word_status = self._check_hunspell_word(word)
                except RuntimeError:
                    word_status = "unsure"
                if word_status == "no":
                    invalid.append(word)
                elif word_status == "unsure":
                    unknown.append(word)
            if unknown:
                return self._candidate_status("hunspell_cli", "unsure", invalid, unknown)
            return self._candidate_status(
                "hunspell_cli",
                "yes" if normalized_words and not invalid else "no",
                invalid,
                [],
            )
        raise ValueError(f"Unknown dictionary mode: {self.mode}")

    @staticmethod
    def _candidate_status(
        backend: str,
        validity: str,
        invalid_words: list[str],
        unknown_words: list[str],
    ) -> dict[str, str]:
        return {
            "dictionary_backend": backend,
            "dictionary_word_validity": validity,
            "dictionary_invalid_words": " ".join(invalid_words),
            "dictionary_unknown_words": " ".join(unknown_words),
            "dictionary_review_complete": "no" if unknown_words or validity == "unsure" else "yes",
        }

    def _check_hunspell_ready(self) -> None:
        if shutil.which(self.hunspell_executable) is None:
            raise RuntimeError(f"Hunspell executable is missing: {self.hunspell_executable}")
        result = subprocess.run(
            [self.hunspell_executable, "-D"],
            check=False,
            capture_output=True,
            text=True,
        )
        dictionaries = f"{result.stdout}\n{result.stderr}"
        if self.hunspell_dictionary not in dictionaries:
            raise RuntimeError(f"Hunspell dictionary is missing: {self.hunspell_dictionary}")

    def _check_hunspell_word(self, word: str) -> str:
        if word in self._hunspell_cache:
            return self._hunspell_cache[word]
        result = subprocess.run(
            build_hunspell_command(self.hunspell_executable, self.hunspell_dictionary),
            input=f"{word}\n",
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode not in {0, 1}:
            raise RuntimeError(result.stderr.strip() or "Hunspell word check failed.")
        misspelled = {normalize_text(line).strip() for line in result.stdout.splitlines() if line.strip()}
        status = "no" if word in misspelled or bool(misspelled) else "yes"
        self._hunspell_cache[word] = status
        return status


def build_hunspell_command(executable: str = "hunspell", dictionary: str = "hr_HR") -> list[str]:
    return [executable, "-d", dictionary, "-l"]


def validate_candidate(
    candidate: str,
    target_class: str,
    saturation_level: float,
    text_type: str,
    seen_normalized: set[str] | None = None,
    dictionary: DictionaryValidator | None = None,
    sentence_min_words: int = 3,
    sentence_max_words: int = 5,
) -> ValidationResult:
    """Validate one generated candidate and return structured failure reasons."""
    seen_normalized = seen_normalized if seen_normalized is not None else set()
    dictionary = dictionary or DictionaryValidator()
    saturation = calculate_saturation(candidate, target_class, saturation_level)
    candidate_words = words(candidate)
    failure_reasons: list[str] = []

    if not saturation.passes_saturation:
        failure_reasons.append(FAIL_FAILED_SATURATION)
    if not has_only_croatian_text_characters(candidate):
        failure_reasons.append(FAIL_INVALID_CHARACTERS)

    normalized_text_type = text_type.strip().lower()
    if normalized_text_type == "word" and len(candidate_words) != 1:
        failure_reasons.append(FAIL_WRONG_WORD_COUNT)
    elif normalized_text_type == "sentence" and not (
        sentence_min_words <= len(candidate_words) <= sentence_max_words
    ):
        failure_reasons.append(FAIL_WRONG_WORD_COUNT)

    if saturation.normalized_text in seen_normalized:
        failure_reasons.append(FAIL_DUPLICATE)

    word_counts = Counter(candidate_words)
    if any(count > 1 for count in word_counts.values()):
        failure_reasons.append(FAIL_REPEATED_WORDS)

    dictionary_status = dictionary.check_candidate(candidate)
    if dictionary_status["dictionary_word_validity"] != "yes":
        failure_reasons.append(FAIL_DICTIONARY_FAILED)

    return ValidationResult(
        original_text=saturation.original_text,
        normalized_text=saturation.normalized_text,
        phonemes=saturation.phonemes,
        total_phonemes=saturation.total_phonemes,
        target_class=saturation.target_class,
        target_count=saturation.target_count,
        saturation_percentage=saturation.saturation_percentage,
        saturation_level=float(saturation_level),
        passes_saturation=saturation.passes_saturation,
        is_valid=not failure_reasons,
        failure_reasons=failure_reasons,
        word_count=len(candidate_words),
        text_type=normalized_text_type,
        dictionary_mode=dictionary.mode,
        dictionary_backend=dictionary_status["dictionary_backend"],
        dictionary_word_validity=dictionary_status["dictionary_word_validity"],
        dictionary_invalid_words=dictionary_status["dictionary_invalid_words"],
        dictionary_unknown_words=dictionary_status["dictionary_unknown_words"],
        dictionary_review_complete=dictionary_status["dictionary_review_complete"],
    )


def validate_candidates(
    candidates: list[dict[str, Any]],
    dictionary: DictionaryValidator | None = None,
    sentence_min_words: int = 3,
    sentence_max_words: int = 5,
) -> list[dict[str, Any]]:
    """Validate rows from a generation adapter and preserve metadata."""
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    dictionary = dictionary or DictionaryValidator()

    for row in candidates:
        result = validate_candidate(
            candidate=str(row["candidate"]),
            target_class=str(row["target_class"]),
            saturation_level=float(row["saturation_level"]),
            text_type=str(row["text_type"]),
            seen_normalized=seen,
            dictionary=dictionary,
            sentence_min_words=sentence_min_words,
            sentence_max_words=sentence_max_words,
        )
        seen.add(result.normalized_text)
        merged = {**row, **result.to_row()}
        validated.append(merged)
    return validated
