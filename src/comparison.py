"""Comparison reports for validated candidate-level CSVs."""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from pathlib import Path
from typing import Any

from .metrics import duplicate_rate, phoneme_frequency
from .phoneme_classes import PHONEME_TO_CLASS
from .report import write_csv

GROUP_FIELDS = ["model", "source_adapter", "prompt_strategy", "target_class", "saturation_level", "text_type"]
RARE_PHONEMES = ("dž", "đ", "lj", "nj", "ž")


def read_rows(paths: list[str | Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            rows.extend(csv.DictReader(handle))
    return rows


def compare_runs(input_paths: list[str | Path], output_dir: str | Path) -> dict[str, Path]:
    rows = read_rows(input_paths)
    out = Path(output_dir)
    plots = out / "plots"
    plots.mkdir(parents=True, exist_ok=True)
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[tuple(row.get(field, "") for field in GROUP_FIELDS)].append(row)

    summary = []
    failure_summary = []
    for key, group_rows in sorted(groups.items()):
        data = dict(zip(GROUP_FIELDS, key))
        total = len(group_rows)
        valid = sum(_truthy(row.get("is_valid")) for row in group_rows)
        saturation = sum(_truthy(row.get("passes_saturation")) for row in group_rows)
        repeated = sum("repeated_words" in row.get("failure_reasons", "") for row in group_rows)
        avg_sat = sum(float(row.get("saturation_percentage") or 0) for row in group_rows) / total if total else 0
        hjp_yes = sum(row.get("candidate_hjp_valid") == "yes" for row in group_rows)
        technical_hjp = sum(_truthy(row.get("is_valid")) and row.get("candidate_hjp_valid") == "yes" for row in group_rows)
        data.update(
            {
                "total_candidates": total,
                "valid_candidates": valid,
                "valid_rate": valid / total if total else 0,
                "saturation_pass_rate": saturation / total if total else 0,
                "hjp_valid_rate": hjp_yes / total if total else "",
                "technical_plus_hjp_valid_rate": technical_hjp / total if total else "",
                "duplicate_rate": duplicate_rate(group_rows),
                "repeated_word_rate": repeated / total if total else 0,
                "average_saturation": avg_sat,
            }
        )
        summary.append(data)
        failures = Counter()
        for row in group_rows:
            for reason in row.get("failure_reasons", "").split(";"):
                if reason:
                    failures[reason] += 1
        for reason, count in sorted(failures.items()):
            failure_summary.append({**dict(zip(GROUP_FIELDS, key)), "failure_reason": reason, "count": count})

    phoneme_rows = []
    frequencies = phoneme_frequency(rows)
    for phoneme, count in frequencies.items():
        phoneme_rows.append(
            {
                "phoneme": phoneme,
                "phoneme_class": PHONEME_TO_CLASS.get(phoneme, ""),
                "count": count,
                "is_rare_focus": "yes" if phoneme in RARE_PHONEMES else "no",
            }
        )

    paths = {
        "comparison_summary": write_csv(out / "comparison_summary.csv", summary),
        "failure_reason_summary": write_csv(out / "failure_reason_summary.csv", failure_summary),
        "phoneme_usage_comparison": write_csv(out / "phoneme_usage_comparison.csv", phoneme_rows),
    }
    report = out / "comparison_report.md"
    report.write_text(_comparison_markdown(summary, failure_summary, phoneme_rows), encoding="utf-8")
    paths["comparison_report"] = report
    return paths


def _truthy(value: Any) -> bool:
    return str(value).lower() == "true" or value is True


def _comparison_markdown(summary: list[dict[str, Any]], failures: list[dict[str, Any]], phonemes: list[dict[str, Any]]) -> str:
    rare = [row for row in phonemes if row["is_rare_focus"] == "yes"]
    return "\n".join(
        [
            "# Comparison Report",
            "",
            "## Research question",
            "How do manual ChatGPT Plus and local Ollama compare for Croatian phoneme-controlled material generation?",
            "",
            "## Experiment design",
            f"Compared groups: {len(summary)}",
            "",
            "## Model/source comparison",
            "See `comparison_summary.csv`.",
            "",
            "## Prompt-strategy comparison",
            "See grouped valid rates and failure summaries.",
            "",
            "## Class difficulty ranking",
            "Rank by valid rate in `comparison_summary.csv`.",
            "",
            "## Saturation difficulty ranking",
            "Higher saturation thresholds are expected to be harder.",
            "",
            "## Word vs sentence comparison",
            "Compare `text_type` groups in `comparison_summary.csv`.",
            "",
            "## Failure analysis",
            f"Failure rows: {len(failures)}",
            "",
            "## Rare phoneme analysis",
            ", ".join(f"{row['phoneme']}={row['count']}" for row in rare) or "No rare phonemes found.",
            "",
            "## Limitations",
            "Generated material is not clinically approved and HJP validity requires manual/local review.",
            "",
            "## Interpretation for audiorehabilitation material generation",
            "Use technically valid and manually reviewed candidates as research material candidates only.",
            "",
        ]
    )

