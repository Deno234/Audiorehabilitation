"""Research metrics for validated candidate text."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
from typing import Any

from .phoneme_classes import PHONEME_CLASSES, PHONEME_TO_CLASS, count_by_class


def _parse_phoneme_cell(value: Any) -> list[str]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    return str(value).split()


def unique_candidate_rate(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    unique = {row.get("normalized_text", "") for row in rows}
    return len(unique) / len(rows)


def duplicate_rate(rows: list[dict[str, Any]]) -> float:
    return 1.0 - unique_candidate_rate(rows) if rows else 0.0


def phoneme_frequency(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(_parse_phoneme_cell(row.get("phonemes")))
    return dict(sorted(counts.items()))


def phoneme_class_distribution(rows: list[dict[str, Any]]) -> dict[str, int]:
    totals = {class_code: 0 for class_code in PHONEME_CLASSES}
    for row in rows:
        for class_code, count in count_by_class(_parse_phoneme_cell(row.get("phonemes"))).items():
            totals[class_code] += count
    return totals


def pcd_paper_style(left: list[str], right: list[str]) -> float:
    """Paper-style PCD based on unmatched phoneme content in the longer item."""
    if not left and not right:
        return 0.0
    longer, shorter = (left, right) if len(left) >= len(right) else (right, left)
    longer_counts = Counter(longer)
    shorter_counts = Counter(shorter)
    shared = sum(min(count, shorter_counts[phoneme]) for phoneme, count in longer_counts.items())
    unmatched = len(longer) - shared
    return unmatched / len(longer) if longer else 0.0


def pcd_vector_style(left: list[str], right: list[str]) -> float:
    """Normalized count-vector distance over all phonemes present in either item."""
    left_counts = Counter(left)
    right_counts = Counter(right)
    phonemes = set(left_counts) | set(right_counts)
    denominator = sum(max(left_counts[p], right_counts[p]) for p in phonemes)
    if denominator == 0:
        return 0.0
    numerator = sum(abs(left_counts[p] - right_counts[p]) for p in phonemes)
    return numerator / denominator


def pcd(left: list[str], right: list[str], version: str) -> float:
    if version == "pcd_paper_style":
        return pcd_paper_style(left, right)
    if version == "pcd_vector_style":
        return pcd_vector_style(left, right)
    raise ValueError(f"Unknown PCD version: {version}")


def pcd_matrix(rows: list[dict[str, Any]], version: str) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for i, left in enumerate(rows):
        for j, right in enumerate(rows):
            matrix.append(
                {
                    "left_index": i,
                    "right_index": j,
                    "left_candidate": left.get("normalized_text", ""),
                    "right_candidate": right.get("normalized_text", ""),
                    "pcd_version": version,
                    "pcd": pcd(
                        _parse_phoneme_cell(left.get("phonemes")),
                        _parse_phoneme_cell(right.get("phonemes")),
                        version,
                    ),
                }
            )
    return matrix


def average_pcd_by_group(rows: list[dict[str, Any]], version: str) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("model", ""),
            row.get("prompt_strategy", ""),
            row.get("target_class", ""),
            row.get("saturation_level", ""),
            row.get("text_type", ""),
        )
        groups[key].append(row)

    summaries: list[dict[str, Any]] = []
    for key, group_rows in groups.items():
        values = [
            pcd(
                _parse_phoneme_cell(left.get("phonemes")),
                _parse_phoneme_cell(right.get("phonemes")),
                version,
            )
            for left, right in combinations(group_rows, 2)
        ]
        model, prompt_strategy, target_class, saturation_level, text_type = key
        summaries.append(
            {
                "model": model,
                "prompt_strategy": prompt_strategy,
                "target_class": target_class,
                "saturation_level": saturation_level,
                "text_type": text_type,
                "pcd_version": version,
                "candidate_count": len(group_rows),
                "average_pcd": sum(values) / len(values) if values else 0.0,
            }
        )
    return summaries


def candidate_summary(rows: list[dict[str, Any]], pcd_version: str) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (
            row.get("run_id", ""),
            row.get("model", ""),
            row.get("prompt_strategy", ""),
            row.get("target_class", ""),
            row.get("saturation_level", ""),
            row.get("text_type", ""),
        )
        groups[key].append(row)

    pcd_lookup = {
        (
            row["model"],
            row["prompt_strategy"],
            row["target_class"],
            row["saturation_level"],
            row["text_type"],
        ): row["average_pcd"]
        for row in average_pcd_by_group(rows, pcd_version)
    }

    summaries: list[dict[str, Any]] = []
    for key, group_rows in sorted(groups.items(), key=lambda item: item[0]):
        run_id, model, prompt_strategy, target_class, saturation_level, text_type = key
        total = len(group_rows)
        valid_count = sum(str(row.get("is_valid")).lower() == "true" or row.get("is_valid") is True for row in group_rows)
        saturation_pass_count = sum(
            str(row.get("passes_saturation")).lower() == "true" or row.get("passes_saturation") is True
            for row in group_rows
        )
        avg_saturation = (
            sum(float(row.get("saturation_percentage", 0.0)) for row in group_rows) / total
            if total
            else 0.0
        )
        failure_counts = Counter()
        for row in group_rows:
            for reason in str(row.get("failure_reasons", "")).split(";"):
                if reason:
                    failure_counts[reason] += 1
        summaries.append(
            {
                "run_id": run_id,
                "model": model,
                "prompt_strategy": prompt_strategy,
                "target_class": target_class,
                "saturation_level": saturation_level,
                "text_type": text_type,
                "candidate_count": total,
                "valid_count": valid_count,
                "valid_rate": valid_count / total if total else 0.0,
                "saturation_pass_count": saturation_pass_count,
                "saturation_pass_rate": saturation_pass_count / total if total else 0.0,
                "unique_candidate_rate": unique_candidate_rate(group_rows),
                "duplicate_rate": duplicate_rate(group_rows),
                "average_saturation": avg_saturation,
                "pcd_version": pcd_version,
                "average_pcd": pcd_lookup.get(
                    (model, prompt_strategy, target_class, saturation_level, text_type), 0.0
                ),
                "failed_saturation": failure_counts.get("failed_saturation", 0),
                "invalid_characters": failure_counts.get("invalid_characters", 0),
                "wrong_word_count": failure_counts.get("wrong_word_count", 0),
                "duplicate": failure_counts.get("duplicate", 0),
                "repeated_words": failure_counts.get("repeated_words", 0),
                "dictionary_failed": failure_counts.get("dictionary_failed", 0),
            }
        )
    return summaries
