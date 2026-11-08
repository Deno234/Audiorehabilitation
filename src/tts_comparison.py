"""TTS comparison reports and listening review sampling."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from .audio_eval import format_compliance, manifest_audio_path, wav_technical_validation
from .report import write_csv


SUMMARY_FIELDS = [
    "tts_adapter",
    "tts_model_or_voice",
    "model",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
    "target_sample_rate",
    "resampling_method",
    "candidate_count",
    "synthesis_success_rate",
    "export_success_rate",
    "suitable_for_audio_eval_rate",
    "average_duration_seconds",
    "average_rms",
    "average_clipping_rate",
    "sample_rate_compliance_rate",
    "format_compliance_rate",
]

FAILURE_FIELDS = ["tts_adapter", "tts_model_or_voice", "failure_reason", "count", "stage", "target_sample_rate", "resampling_method"]

LISTENING_REVIEW_FIELDS = [
    "candidate_id",
    "candidate",
    "normalized_text",
    "tts_adapter",
    "tts_model_or_voice",
    "audio_path",
    "target_class",
    "saturation_level",
    "text_type",
    "human_intelligibility_score",
    "human_naturalness_score",
    "pronunciation_notes",
    "clinical_suitability_notes",
]


def compare_tts_audio(audio_manifest: str | Path, output_dir: str | Path, *, expected_sample_rate: int = 16000) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with Path(audio_manifest).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    enriched = []
    for row in rows:
        row["target_sample_rate"] = str(row.get("target_sample_rate") or expected_sample_rate)
        row["resampling_method"] = row.get("resampling_method") or "unrecorded"
        tech = (wav_technical_validation(manifest_audio_path(row, audio_manifest))
                if row.get("export_status", "success") == "success" else {"audio_readable": False})
        merged = {**row, **format_compliance(tech, row["target_sample_rate"]), **{f"technical_{key}": value for key, value in tech.items()}}
        enriched.append(merged)

    summary_rows = _summary(enriched)
    failure_rows = _failures(enriched)
    paths = {
        "tts_audio_summary": write_csv(output / "tts_audio_summary.csv", summary_rows, SUMMARY_FIELDS),
        "tts_failure_summary": write_csv(output / "tts_failure_summary.csv", failure_rows, FAILURE_FIELDS),
    }
    report_path = output / "tts_audio_report.md"
    report_path.write_text(_markdown(summary_rows, failure_rows), encoding="utf-8")
    paths["tts_audio_report"] = report_path
    return paths


def export_listening_review_sample(
    audio_manifest: str | Path,
    output_path: str | Path,
    per_adapter: int,
) -> Path:
    with Path(audio_manifest).open("r", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row.get("export_status", row.get("synthesis_status")) == "success"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row.get("tts_adapter", "")].append(row)

    sample_rows = []
    for adapter in sorted(grouped):
        for row in grouped[adapter][:per_adapter]:
            sample_rows.append(
                {
                    "candidate_id": row.get("candidate_id", ""),
                    "candidate": row.get("candidate", ""),
                    "normalized_text": row.get("normalized_text", ""),
                    "tts_adapter": row.get("tts_adapter", ""),
                    "tts_model_or_voice": row.get("tts_model_or_voice", ""),
                    "audio_path": str(manifest_audio_path(row, audio_manifest)),
                    "target_class": row.get("target_class", ""),
                    "saturation_level": row.get("saturation_level", ""),
                    "text_type": row.get("text_type", ""),
                    "human_intelligibility_score": "",
                    "human_naturalness_score": "",
                    "pronunciation_notes": "",
                    "clinical_suitability_notes": "",
                }
            )
    return write_csv(output_path, sample_rows, LISTENING_REVIEW_FIELDS)


def _summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                row.get("tts_adapter", ""),
                row.get("tts_model_or_voice", ""),
                row.get("model", ""),
                row.get("prompt_strategy", ""),
                row.get("target_class", ""),
                row.get("saturation_level", ""),
                row.get("text_type", ""),
                row["target_sample_rate"],
                row["resampling_method"],
            )
        ].append(row)
    output = []
    for key, group in grouped.items():
        total = len(group)
        success = [row for row in group if row.get("synthesis_status") == "success"]
        suitable = [row for row in group if row.get("suitable_for_audio_eval") == "yes"]
        readable = [row for row in group if row.get("technical_audio_readable")]
        output.append(
            {
                "tts_adapter": key[0],
                "tts_model_or_voice": key[1],
                "model": key[2],
                "prompt_strategy": key[3],
                "target_class": key[4],
                "saturation_level": key[5],
                "text_type": key[6],
                "target_sample_rate": key[7],
                "resampling_method": key[8],
                "candidate_count": total,
                "export_success_rate": _rate(group, lambda r: r.get("export_status") == "success")
                if "export_status" in group[0] else "",
                "synthesis_success_rate": len(success) / total if total else 0,
                "suitable_for_audio_eval_rate": len(suitable) / total if total else 0,
                "average_duration_seconds": _average(row.get("technical_duration_seconds") for row in readable),
                "average_rms": _average(row.get("technical_rms") for row in readable),
                "average_clipping_rate": _average(row.get("technical_clipping_rate") for row in readable),
                "sample_rate_compliance_rate": _rate(readable, lambda row: row["sample_rate_compliant"]),
                "format_compliance_rate": _rate(readable, lambda row: row["format_compliant"]),
            }
        )
    return output


def _failures(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = defaultdict(int)
    for row in rows:
        for stage in ("synthesis", "export"):
            status = row.get(f"{stage}_status")
            if status and status != "success":
                reason = row.get("export_error" if stage == "export" else "error") or status
                key = (row["tts_adapter"], row.get("tts_model_or_voice", ""), reason, stage,
                       row["target_sample_rate"], row["resampling_method"])
                counts[key] += 1
        if (not row.get("technical_audio_readable") and
                row.get("export_status", row.get("synthesis_status")) == "success"):
            reason = row.get("technical_error") or "Unreadable WAV"
            key = (row["tts_adapter"], row.get("tts_model_or_voice", ""), reason, "validation",
                   row["target_sample_rate"], row["resampling_method"])
            counts[key] += 1
    return [dict(tts_adapter=a, tts_model_or_voice=m, failure_reason=reason, stage=stage,
                 target_sample_rate=rate, resampling_method=method, count=count)
            for (a, m, reason, stage, rate, method), count in sorted(counts.items())]


def _average(values) -> float:
    parsed = [float(value) for value in values if value not in {"", None}]
    return sum(parsed) / len(parsed) if parsed else 0.0


def _rate(rows: list[dict[str, Any]], predicate) -> float:
    return sum(1 for row in rows if predicate(row)) / len(rows) if rows else 0.0


def _markdown(summary_rows: list[dict[str, Any]], failure_rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Croatian TTS Comparison Report",
        "",
        "- Expected format: mono PCM16 WAV at the target rate shown for each group.",
        "- ASR WER/CER is a proxy for intelligibility, not clinical proof.",
        "- Human listening review is recommended for final conclusions.",
        "",
        "## Summary",
        "",
        "| Adapter | Model/voice | Source model | Strategy | Class | Saturation | Type | Target Hz | Resampler | Synthesis success rate | Format compliance |",
        "|---|---|---|---|---:|---:|---|---:|---|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {tts_adapter} | {tts_model_or_voice} | {model} | {prompt_strategy} | {target_class} | "
            "{saturation_level} | {text_type} | {target_sample_rate} | {resampling_method} | {synthesis_success_rate:.3f} | {format_compliance_rate:.3f} |".format(**row)
        )
    lines.extend(["", "## Failures", ""])
    if failure_rows:
        for row in failure_rows[:20]:
            lines.append(f"- {row['tts_adapter']} / {row['tts_model_or_voice']} ({row['stage']}, {row['target_sample_rate']} Hz): {row['failure_reason']} ({row['count']})")
    else:
        lines.append("- No failures recorded.")
    return "\n".join(lines) + "\n"
