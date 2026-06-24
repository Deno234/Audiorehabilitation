"""Balanced candidate subset export for TTS comparison."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from .report import candidate_fieldnames, write_csv


GROUP_FIELDS = ["target_class", "saturation_level", "text_type"]


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1"}


def _status_yes(value: Any) -> bool:
    return str(value).strip().lower() == "yes"


def _failure_reasons(row: dict[str, Any]) -> set[str]:
    return {
        reason.strip()
        for reason in str(row.get("failure_reasons", "")).replace(";", ",").split(",")
        if reason.strip()
    }


def _candidate_key(row: dict[str, Any]) -> str:
    return str(row.get("normalized_text") or row.get("candidate") or "").strip().lower()


def _selection_score(row: dict[str, Any]) -> tuple[int, int, int, int, float]:
    reasons = _failure_reasons(row)
    try:
        saturation = float(row.get("saturation_percentage") or 0)
    except ValueError:
        saturation = 0.0
    return (
        1 if _truthy(row.get("is_valid")) else 0,
        1 if row.get("candidate_hjp_valid", "yes") in {"", "yes"} else 0,
        1 if row.get("dictionary_word_validity", "yes") in {"", "yes"} else 0,
        1 if "duplicate" not in reasons else 0,
        saturation,
    )


def export_tts_candidate_subset(
    input_path: str | Path,
    output_path: str | Path,
    per_group: int = 5,
) -> dict[str, Any]:
    """Export a balanced UTF-8 CSV grouped by class, saturation, and text type."""
    with Path(input_path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = tuple(str(row.get(field, "")).strip() for field in GROUP_FIELDS)
        grouped[key].append(row)

    selected: list[dict[str, Any]] = []
    seen_texts: set[str] = set()
    group_summaries: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda value: (value[2], value[0], float(value[1] or 0))):
        candidates = sorted(grouped[key], key=_selection_score, reverse=True)
        chosen: list[dict[str, Any]] = []
        for row in candidates:
            normalized = _candidate_key(row)
            if not normalized or normalized in seen_texts:
                continue
            chosen.append(row)
            seen_texts.add(normalized)
            if len(chosen) >= per_group:
                break
        selected.extend(chosen)
        group_summaries.append(
            {
                "target_class": key[0],
                "saturation_level": key[1],
                "text_type": key[2],
                "available": len(grouped[key]),
                "selected": len(chosen),
                "status": "filled" if len(chosen) >= per_group else "underfilled",
            }
        )

    fieldnames = candidate_fieldnames(selected) if selected else candidate_fieldnames(rows)
    output = write_csv(output_path, selected, fieldnames)
    filled = sum(summary["status"] == "filled" for summary in group_summaries)
    underfilled = [summary for summary in group_summaries if summary["status"] != "filled"]
    return {
        "output_path": output,
        "requested_groups": len(group_summaries),
        "filled_groups": filled,
        "missing_or_underfilled_groups": underfilled,
        "selected_candidates": len(selected),
        "per_group": per_group,
    }
