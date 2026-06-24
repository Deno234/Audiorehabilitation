"""Lexical review queue helpers."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from .phonemizer import words
from .report import write_csv


LEXICAL_REVIEW_FIELDS = [
    "word",
    "hunspell_valid",
    "source_candidates_count",
    "example_candidates",
    "models",
    "source_adapters",
    "prompt_strategies",
    "target_classes",
    "text_types",
    "priority",
    "review_reason",
    "manual_hjp_valid",
    "reviewer_notes",
]

RARE_PHONEME_WORD_PARTS = ("dž", "đ", "lj", "nj", "ž")


def export_lexical_review_queue(input_path: str | Path, output_path: str | Path) -> Path:
    with Path(input_path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for word in words(row.get("normalized_text") or row.get("candidate", "")):
            grouped[word].append(row)

    output_rows = []
    for word, source_rows in sorted(grouped.items()):
        hunspell_valid = _hunspell_word_status(word, source_rows)
        priority, reason = _priority(word, source_rows, hunspell_valid)
        output_rows.append(
            {
                "word": word,
                "hunspell_valid": hunspell_valid,
                "source_candidates_count": len(source_rows),
                "example_candidates": "; ".join(_unique(row.get("candidate", "") for row in source_rows)[:5]),
                "models": "; ".join(_unique(row.get("model", "") for row in source_rows)),
                "source_adapters": "; ".join(_unique(row.get("source_adapter", "") for row in source_rows)),
                "prompt_strategies": "; ".join(_unique(row.get("prompt_strategy", "") for row in source_rows)),
                "target_classes": "; ".join(_unique(row.get("target_class", "") for row in source_rows)),
                "text_types": "; ".join(_unique(row.get("text_type", "") for row in source_rows)),
                "priority": priority,
                "review_reason": reason,
                "manual_hjp_valid": "",
                "reviewer_notes": "",
            }
        )
    return write_csv(output_path, output_rows, LEXICAL_REVIEW_FIELDS)


def _hunspell_word_status(word: str, rows: list[dict[str, Any]]) -> str:
    statuses = []
    for row in rows:
        invalid = set((row.get("dictionary_invalid_words") or "").split())
        unknown = set((row.get("dictionary_unknown_words") or "").split())
        if word in invalid:
            statuses.append("no")
        elif word in unknown:
            statuses.append("unsure")
        elif row.get("dictionary_backend") == "hunspell_cli" and row.get("dictionary_word_validity") == "yes":
            statuses.append("yes")
    if "no" in statuses:
        return "no"
    if "unsure" in statuses:
        return "unsure"
    if "yes" in statuses:
        return "yes"
    return ""


def _priority(word: str, rows: list[dict[str, Any]], hunspell_valid: str) -> tuple[str, str]:
    reasons = []
    technically_valid = any(_technical_without_dictionary(row) for row in rows)
    if hunspell_valid == "no" and technically_valid:
        reasons.append("hunspell_invalid_technical_candidate")
    if any(part in word for part in RARE_PHONEME_WORD_PARTS):
        reasons.append("rare_phoneme_word")
    if reasons:
        return "high", ";".join(reasons)
    if len(rows) >= 3:
        return "medium", "high_frequency_word"
    return "low", "hunspell_valid_or_not_screened"


def _technical_without_dictionary(row: dict[str, Any]) -> bool:
    failures = {
        failure
        for failure in (row.get("failure_reasons") or "").split(";")
        if failure
    }
    return not (failures - {"dictionary_failed"})


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
