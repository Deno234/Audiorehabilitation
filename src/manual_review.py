"""Manual HJP and suitability review workflows."""

from __future__ import annotations

from collections import defaultdict
import csv
from pathlib import Path
from typing import Any

from .phonemizer import words
from .report import write_csv


HJP_REVIEW_FIELDS = [
    "word",
    "source_candidates_count",
    "example_candidates",
    "models",
    "source_adapters",
    "prompt_strategies",
    "target_classes",
    "text_types",
    "hjp_valid",
    "hjp_entry_checked",
    "reviewer",
    "reviewer_notes",
]


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def export_hjp_word_review(input_path: str | Path, output_path: str | Path) -> Path:
    rows = read_csv(input_path)
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        candidate_words = words(row.get("normalized_text") or row.get("candidate", ""))
        for word in candidate_words:
            entry = grouped.setdefault(
                word,
                {
                    "word": word,
                    "source_candidates": set(),
                    "examples": [],
                    "models": set(),
                    "source_adapters": set(),
                    "prompt_strategies": set(),
                    "target_classes": set(),
                    "text_types": set(),
                },
            )
            candidate = row.get("candidate") or row.get("normalized_text", "")
            entry["source_candidates"].add(row.get("candidate_id") or candidate)
            if candidate and candidate not in entry["examples"] and len(entry["examples"]) < 5:
                entry["examples"].append(candidate)
            for key in ("models", "source_adapters", "prompt_strategies", "target_classes", "text_types"):
                value_key = {
                    "models": "model",
                    "source_adapters": "source_adapter",
                    "prompt_strategies": "prompt_strategy",
                    "target_classes": "target_class",
                    "text_types": "text_type",
                }[key]
                if row.get(value_key):
                    entry[key].add(row[value_key])
    output_rows = []
    for word, entry in sorted(grouped.items()):
        output_rows.append(
            {
                "word": word,
                "source_candidates_count": len(entry["source_candidates"]),
                "example_candidates": " | ".join(entry["examples"]),
                "models": ";".join(sorted(entry["models"])),
                "source_adapters": ";".join(sorted(entry["source_adapters"])),
                "prompt_strategies": ";".join(sorted(entry["prompt_strategies"])),
                "target_classes": ";".join(sorted(entry["target_classes"])),
                "text_types": ";".join(sorted(entry["text_types"])),
                "hjp_valid": "",
                "hjp_entry_checked": "",
                "reviewer": "",
                "reviewer_notes": "",
            }
        )
    return write_csv(output_path, output_rows, HJP_REVIEW_FIELDS)


def apply_hjp_word_review(
    input_path: str | Path, word_review_path: str | Path, output_path: str | Path
) -> Path:
    rows = read_csv(input_path)
    review_rows = read_csv(word_review_path)
    review = {row["word"]: row.get("hjp_valid", "").strip().lower() for row in review_rows}
    output_rows = []
    for row in rows:
        candidate_words = words(row.get("normalized_text") or row.get("candidate", ""))
        invalid = [word for word in candidate_words if review.get(word) == "no"]
        unknown = [
            word
            for word in candidate_words
            if review.get(word) not in {"yes", "no"}
        ]
        if invalid:
            status = "no"
        elif unknown:
            status = "unsure"
        else:
            status = "yes" if candidate_words else "unsure"
        merged = dict(row)
        merged["candidate_hjp_valid"] = status
        merged["hjp_unknown_words"] = " ".join(unknown)
        merged["hjp_invalid_words"] = " ".join(invalid)
        merged["hjp_review_complete"] = "yes" if not unknown else "no"
        output_rows.append(merged)
    return write_csv(output_path, output_rows)


def export_manual_review(input_path: str | Path, output_path: str | Path) -> Path:
    rows = read_csv(input_path)
    seen = set()
    output = []
    for row in rows:
        normalized = row.get("normalized_text", "")
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(
            {
                "candidate": row.get("candidate", ""),
                "normalized_text": normalized,
                "words": " ".join(words(normalized)),
                "model": row.get("model", ""),
                "source_adapter": row.get("source_adapter", ""),
                "prompt_strategy": row.get("prompt_strategy", ""),
                "target_class": row.get("target_class", ""),
                "saturation_level": row.get("saturation_level", ""),
                "text_type": row.get("text_type", ""),
                "technical_is_valid": row.get("is_valid", ""),
                "manual_semantic_naturalness": "",
                "manual_clinical_suitability": "",
                "reviewer_notes": "",
            }
        )
    return write_csv(output_path, output)


def apply_manual_review(input_path: str | Path, review_path: str | Path, output_path: str | Path) -> Path:
    rows = read_csv(input_path)
    review = {row["normalized_text"]: row for row in read_csv(review_path)}
    output = []
    for row in rows:
        merged = dict(row)
        review_row = review.get(row.get("normalized_text", ""), {})
        for key in ("manual_semantic_naturalness", "manual_clinical_suitability", "reviewer_notes"):
            merged[key] = review_row.get(key, "")
        output.append(merged)
    return write_csv(output_path, output)

