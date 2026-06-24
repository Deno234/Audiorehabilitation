"""CSV, Markdown, and plot reporting."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .metrics import (
    average_pcd_by_group,
    candidate_summary,
    pcd_matrix,
    phoneme_class_distribution,
    phoneme_frequency,
)


CANDIDATE_FIELDS = [
    "run_id",
    "candidate_id",
    "candidate",
    "model",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
    "source_adapter",
    "source_file",
    "original_text",
    "normalized_text",
    "phonemes",
    "total_phonemes",
    "target_count",
    "saturation_percentage",
    "passes_saturation",
    "is_valid",
    "failure_reasons",
    "word_count",
    "dictionary_mode",
    "dictionary_backend",
    "dictionary_word_validity",
    "dictionary_invalid_words",
    "dictionary_unknown_words",
    "dictionary_review_complete",
]

AUDIO_EVAL_FIELDS = [
    "run_id",
    "candidate_id",
    "audio_path",
    "source_text",
    "transcription",
    "wer",
    "cer",
    "error_notes",
]


def candidate_fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    """Keep core columns first, then preserve safe pass-through metadata columns."""
    fieldnames = list(CANDIDATE_FIELDS)
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    return fieldnames


def write_csv(path: str | Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    """Write CSV with explicit UTF-8 encoding."""
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        field_set: list[str] = []
        for row in rows:
            for key in row:
                if key not in field_set:
                    field_set.append(key)
        fieldnames = field_set
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return csv_path


def _write_markdown_report(
    path: Path,
    run_id: str,
    rows: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    pcd_version: str,
) -> None:
    valid_rows = [row for row in rows if row.get("is_valid") is True]
    lines = [
        f"# Auditory Rehabilitation Experiment Report",
        "",
        f"- Run ID: `{run_id}`",
        f"- PCD version: `{pcd_version}`",
        f"- Total candidates: {len(rows)}",
        f"- Valid candidates: {len(valid_rows)}",
        "",
        "## Summary",
        "",
        "| Model | Prompt strategy | Class | Saturation | Type | Total candidates | Valid candidates | Valid rate | Avg saturation | Duplicate rate | Avg PCD |",
        "|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            "| {model} | {prompt_strategy} | {target_class} | {saturation_level} | {text_type} | "
            "{candidate_count} | {valid_count} | {valid_rate:.3f} | {average_saturation:.2f} | "
            "{duplicate_rate:.3f} | {average_pcd:.3f} |".format(**row)
        )

    lines.extend(
        [
            "",
            "## How to interpret results",
            "",
            "- Saturation pass rate is the share of candidates whose target-class phoneme percentage met the configured threshold.",
            "- Duplicate rate is based on normalized candidate text; duplicates reduce the useful variety of generated material.",
            "- Failure reasons identify deterministic validation problems such as saturation failure, invalid characters, wrong word count, duplicates, repeated words, or dictionary/manual-review failure.",
            "- PCD estimates phonetic-content diversity within a group. Higher values usually mean candidates share fewer phonemes, while lower values mean stronger phonetic overlap.",
            "- Valid text still needs human review. Python validation checks technical constraints, but meaning, naturalness, dialect fit, age appropriateness, and clinical suitability must be judged by a qualified reviewer.",
            "- Hunspell screening is not HJP validation. It may reject valid inflected Croatian words or accept words that are not appropriate for rehabilitation context, so treat it as automatic lexical screening only.",
        ]
    )

    if any(row.get("dictionary_backend") == "hunspell_cli" for row in rows):
        total = len(rows)
        dictionary_yes = sum(row.get("dictionary_word_validity") == "yes" for row in rows)
        technical_dictionary_yes = sum(
            row.get("dictionary_word_validity") == "yes"
            and (row.get("is_valid") is True or str(row.get("is_valid")).lower() == "true")
            for row in rows
        )
        lines.extend(
            [
                "",
                "## Croatian Dictionary Screening",
                "",
                f"- Hunspell valid rate: {dictionary_yes / total:.3f}" if total else "- Hunspell valid rate: 0.000",
                f"- Technical + Hunspell valid rate: {technical_dictionary_yes / total:.3f}" if total else "- Technical + Hunspell valid rate: 0.000",
                "- Hunspell is scalable, but it is not identical to HJP and is not final linguistic or clinical validation.",
            ]
        )
        invalid_examples = [row for row in rows if row.get("dictionary_invalid_words")]
        unknown_examples = [row for row in rows if row.get("dictionary_unknown_words")]
        if invalid_examples:
            lines.append("- Hunspell invalid word examples: " + "; ".join(row.get("dictionary_invalid_words", "") for row in invalid_examples[:5]))
        if unknown_examples:
            lines.append("- Hunspell unsure/missing word examples: " + "; ".join(row.get("dictionary_unknown_words", "") for row in unknown_examples[:5]))

    if any("candidate_hjp_valid" in row for row in rows):
        total = len(rows)
        hjp_yes = sum(row.get("candidate_hjp_valid") == "yes" for row in rows)
        technical_hjp_yes = sum(
            row.get("candidate_hjp_valid") == "yes"
            and (row.get("is_valid") is True or str(row.get("is_valid")).lower() == "true")
            for row in rows
        )
        lines.extend(
            [
                "",
                "## Manual HJP Review",
                "",
                f"- HJP valid rate: {hjp_yes / total:.3f}" if total else "- HJP valid rate: 0.000",
                f"- Technical + HJP valid rate: {technical_hjp_yes / total:.3f}" if total else "- Technical + HJP valid rate: 0.000",
            ]
        )
        invalid_examples = [row for row in rows if row.get("hjp_invalid_words")]
        unknown_examples = [row for row in rows if row.get("hjp_unknown_words")]
        if invalid_examples:
            lines.append("- HJP invalid word examples: " + "; ".join(row.get("hjp_invalid_words", "") for row in invalid_examples[:5]))
        if unknown_examples:
            lines.append("- HJP unsure/missing word examples: " + "; ".join(row.get("hjp_unknown_words", "") for row in unknown_examples[:5]))

    failure_examples = [row for row in rows if row.get("failure_reasons")]
    lines.extend(["", "## Top Failure Examples", ""])
    if failure_examples:
        for row in failure_examples[:10]:
            lines.append(
                f"- `{row.get('candidate')}`: {row.get('failure_reasons')} "
                f"(class {row.get('target_class')}, saturation {float(row.get('saturation_percentage', 0.0)):.2f}%)"
            )
    else:
        lines.append("- No failures.")

    lines.extend(["", "## Best Valid Candidates", ""])
    if valid_rows:
        for row in valid_rows[:10]:
            lines.append(
                f"- `{row.get('candidate')}`: {float(row.get('saturation_percentage', 0.0)):.2f}% "
                f"for {row.get('target_class')}"
            )
    else:
        lines.append("- No valid candidates in this run.")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_plots(
    output_dir: Path,
    run_id: str,
    rows: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return []

    plot_paths: list[Path] = []

    def save_bar(filename: str, labels: list[str], values: list[float], title: str, ylabel: str) -> None:
        if not labels:
            return
        plt.figure(figsize=(10, 5))
        plt.bar(labels, values)
        plt.xticks(rotation=30, ha="right")
        plt.title(title)
        plt.ylabel(ylabel)
        plt.tight_layout()
        path = output_dir / filename
        plt.savefig(path)
        plt.close()
        plot_paths.append(path)

    labels = [
        f"{row['model']}-{row['prompt_strategy']}-{row['target_class']}-{row['saturation_level']}-{row['text_type']}"
        for row in summaries
    ]
    save_bar(
        f"saturation_pass_rate_{run_id}.png",
        labels,
        [float(row["saturation_pass_rate"]) for row in summaries],
        "Saturation Pass Rate",
        "Pass rate",
    )
    save_bar(
        f"duplicate_rate_{run_id}.png",
        labels,
        [float(row["duplicate_rate"]) for row in summaries],
        "Duplicate Rate",
        "Duplicate rate",
    )

    class_distribution = phoneme_class_distribution(rows)
    save_bar(
        f"phoneme_class_distribution_{run_id}.png",
        list(class_distribution),
        [float(value) for value in class_distribution.values()],
        "Phoneme Class Distribution",
        "Count",
    )

    return plot_paths


def generate_reports(
    rows: list[dict[str, Any]],
    output_dir: str | Path,
    run_id: str,
    pcd_version: str,
) -> dict[str, Path]:
    """Generate all first-milestone reports."""
    report_dir = Path(output_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    valid_rows = [row for row in rows if row.get("is_valid") is True]
    summaries = candidate_summary(rows, pcd_version)
    pcd_rows = pcd_matrix(valid_rows, pcd_version)
    pcd_summary_rows = average_pcd_by_group(valid_rows, pcd_version)
    frequency_rows = [
        {"run_id": run_id, "phoneme": phoneme, "count": count}
        for phoneme, count in phoneme_frequency(rows).items()
    ]
    class_distribution_rows = [
        {"run_id": run_id, "phoneme_class": class_code, "count": count}
        for class_code, count in phoneme_class_distribution(rows).items()
    ]

    candidate_fields = candidate_fieldnames(rows)
    paths = {
        "all_candidates": write_csv(
            report_dir / f"all_candidates_{run_id}.csv", rows, candidate_fields
        ),
        "validated_candidates": write_csv(
            report_dir / f"validated_candidates_{run_id}.csv", valid_rows, candidate_fields
        ),
        "experiment_summary": write_csv(
            report_dir / f"experiment_summary_{run_id}.csv", summaries
        ),
        "audio_eval_summary": write_csv(
            report_dir / f"audio_eval_summary_{run_id}.csv", [], AUDIO_EVAL_FIELDS
        ),
        "pcd_matrix": write_csv(report_dir / f"pcd_matrix_{run_id}.csv", pcd_rows),
        "pcd_summary": write_csv(report_dir / f"pcd_summary_{run_id}.csv", pcd_summary_rows),
        "phoneme_frequency": write_csv(
            report_dir / f"phoneme_frequency_{run_id}.csv", frequency_rows
        ),
        "phoneme_class_distribution": write_csv(
            report_dir / f"phoneme_class_distribution_{run_id}.csv", class_distribution_rows
        ),
    }

    markdown_path = report_dir / f"report_{run_id}.md"
    _write_markdown_report(markdown_path, run_id, rows, summaries, pcd_version)
    paths["markdown_report"] = markdown_path

    for plot_path in _write_plots(report_dir, run_id, rows, summaries):
        paths[f"plot_{plot_path.stem}"] = plot_path

    return paths
