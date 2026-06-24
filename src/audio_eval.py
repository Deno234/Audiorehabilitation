"""Audio technical and optional ASR/manual transcription evaluation."""

from __future__ import annotations

import csv
import math
from pathlib import Path
import re
import struct
from typing import Any, Callable
import wave

from .asr_eval import FasterWhisperTranscriber, cer, wer
from .report import write_csv


AUDIO_EVAL_FIELDS = [
    "run_id",
    "candidate_id",
    "audio_path",
    "tts_adapter",
    "tts_model_or_voice",
    "target_class",
    "saturation_level",
    "text_type",
    "source_text",
    "normalized_source_text",
    "asr_profile",
    "asr_adapter",
    "asr_model_name",
    "asr_model_path",
    "asr_language",
    "asr_device",
    "asr_compute_type",
    "asr_model",
    "asr_transcription",
    "normalized_asr_transcription",
    "wer",
    "cer",
    "audio_readable",
    "sample_rate",
    "channels",
    "sample_width_bits",
    "duration_seconds",
    "rms",
    "clipping_rate",
    "eval_status",
    "error",
    "listener_notes_optional",
]

ASR_TTS_SUMMARY_FIELDS = [
    "asr_profile",
    "asr_model_name",
    "tts_adapter",
    "tts_model_or_voice",
    "target_class",
    "saturation_level",
    "text_type",
    "count_evaluated",
    "count_failed",
    "average_wer",
    "average_cer",
    "worst_wer_examples",
    "worst_cer_examples",
]


def normalize_audio_eval_text(text: str) -> str:
    lowered = text.lower()
    cleaned = re.sub(r"[^a-zčćđšž\s]", " ", lowered)
    return re.sub(r"\s+", " ", cleaned).strip()


def wav_technical_validation(path: str | Path) -> dict[str, Any]:
    result = {
        "audio_readable": False,
        "sample_rate": "",
        "channels": "",
        "sample_width_bits": "",
        "duration_seconds": "",
        "rms": "",
        "clipping_rate": "",
        "error": "",
    }
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            sample_rate = handle.getframerate()
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            data = handle.readframes(frames)
        result.update(
            {
                "audio_readable": True,
                "sample_rate": sample_rate,
                "channels": channels,
                "sample_width_bits": sample_width * 8,
                "duration_seconds": frames / sample_rate if sample_rate else 0,
            }
        )
        if sample_width == 2 and data:
            samples = struct.unpack("<" + "h" * (len(data) // 2), data)
            if samples:
                result["rms"] = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
                clipped = sum(abs(sample) >= 32767 for sample in samples)
                result["clipping_rate"] = clipped / len(samples)
    except Exception as exc:
        result["error"] = str(exc)
    return result


def evaluate_audio(
    audio_manifest: str | Path,
    output_dir: str | Path,
    *,
    asr_adapter: str | None = None,
    asr_model: str = "",
    asr_profile: str = "",
    asr_transcriber: Callable[[str], str] | None = None,
    asr_config: dict[str, Any] | None = None,
    manual_transcriptions: str | Path | None = None,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    resolved_profile = resolve_asr_profile(asr_profile, asr_adapter, asr_model, asr_config or {})
    if resolved_profile["adapter"]:
        asr_adapter = resolved_profile["adapter"]
        asr_model = resolved_profile["model_name"]
    with Path(audio_manifest).open("r", encoding="utf-8", newline="") as handle:
        manifest_rows = list(csv.DictReader(handle))
    manual = _read_manual_transcriptions(manual_transcriptions) if manual_transcriptions else {}
    rows = []
    for row in manifest_rows:
        source = row.get("normalized_text") or row.get("candidate", "")
        normalized_source = normalize_audio_eval_text(source)
        adapter = asr_adapter or ("manual_transcription" if manual_transcriptions else "technical_only")
        raw_transcription = ""
        notes = ""
        status = "technical_only"
        error = ""
        if asr_adapter:
            if asr_transcriber is None:
                asr_transcriber = build_asr_transcriber(asr_adapter, resolved_profile)
            raw_transcription = asr_transcriber(row["audio_path"])
            status = "success"
        elif manual_transcriptions:
            match = manual.get(row.get("candidate_id", ""), {})
            raw_transcription = match.get("transcription", "")
            notes = match.get("listener_notes", "")
            status = "success" if raw_transcription else "missing_transcription"
        tech = wav_technical_validation(row["audio_path"])
        normalized_hypothesis = normalize_audio_eval_text(raw_transcription)
        rows.append(
            {
                "run_id": row.get("run_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "audio_path": row.get("audio_path", ""),
                "tts_adapter": row.get("tts_adapter", ""),
                "tts_model_or_voice": row.get("tts_model_or_voice") or row.get("tts_voice", ""),
                "target_class": row.get("target_class", ""),
                "saturation_level": row.get("saturation_level", ""),
                "text_type": row.get("text_type", ""),
                "source_text": source,
                "normalized_source_text": normalized_source,
                "asr_profile": resolved_profile["profile"],
                "asr_adapter": adapter,
                "asr_model_name": resolved_profile["model_name"],
                "asr_model_path": resolved_profile["model_path"],
                "asr_language": resolved_profile["language"],
                "asr_device": resolved_profile["device"],
                "asr_compute_type": resolved_profile["compute_type"],
                "asr_model": asr_model,
                "asr_transcription": raw_transcription,
                "normalized_asr_transcription": normalized_hypothesis,
                "wer": wer(normalized_source, normalized_hypothesis) if raw_transcription else "",
                "cer": cer(normalized_source, normalized_hypothesis) if raw_transcription else "",
                "audio_readable": tech["audio_readable"],
                "sample_rate": tech["sample_rate"],
                "channels": tech["channels"],
                "sample_width_bits": tech["sample_width_bits"],
                "duration_seconds": tech["duration_seconds"],
                "rms": tech["rms"],
                "clipping_rate": tech["clipping_rate"],
                "eval_status": status,
                "error": error or tech["error"],
                "listener_notes_optional": notes,
            }
        )
    summary_path = write_csv(output / "audio_eval_summary.csv", rows, AUDIO_EVAL_FIELDS)
    tts_summary_path = write_csv(output / "audio_eval_tts_summary.csv", _tts_asr_summary(rows), ASR_TTS_SUMMARY_FIELDS)
    report_path = output / "audio_eval_report.md"
    report_path.write_text(_audio_report(rows), encoding="utf-8")
    return {"audio_eval_summary": summary_path, "audio_eval_tts_summary": tts_summary_path, "audio_eval_report": report_path}


def build_asr_transcriber(asr_adapter: str, asr_config: dict[str, Any]) -> Callable[[str], str]:
    if asr_adapter != "faster_whisper":
        raise RuntimeError(f"ASR adapter {asr_adapter} is not configured or installed.")
    faster_config = asr_config.get("faster_whisper", asr_config)
    if faster_config.get("local_files_only", False) and not faster_config.get("model_path"):
        raise RuntimeError(
            "ASR profile uses local_files_only: true but model_path is empty. "
            "Provide a local faster-whisper model path or explicitly allow downloads in a future config."
        )
    transcriber = FasterWhisperTranscriber(
        model_path=faster_config.get("model_path", ""),
        language=faster_config.get("language", "hr"),
        device=faster_config.get("device", "cpu"),
        compute_type=faster_config.get("compute_type", "int8"),
    )
    return transcriber.transcribe


def resolve_asr_profile(
    asr_profile: str | None,
    asr_adapter: str | None,
    asr_model: str,
    asr_config: dict[str, Any],
) -> dict[str, str]:
    if asr_profile:
        profiles = asr_config.get("asr_profiles", {})
        if asr_profile not in profiles:
            raise RuntimeError(f"ASR profile is not configured: {asr_profile}")
        profile = profiles[asr_profile]
        return {
            "profile": asr_profile,
            "adapter": profile.get("adapter", ""),
            "model_name": profile.get("model_name", ""),
            "model_path": profile.get("model_path", ""),
            "language": profile.get("language", "hr"),
            "device": profile.get("device", "cpu"),
            "compute_type": profile.get("compute_type", "int8"),
            "local_files_only": profile.get("local_files_only", False),
        }
    faster_config = asr_config.get("faster_whisper", asr_config)
    return {
        "profile": "",
        "adapter": asr_adapter or "",
        "model_name": asr_model or faster_config.get("model_name", ""),
        "model_path": faster_config.get("model_path", ""),
        "language": faster_config.get("language", "hr") if asr_adapter else "",
        "device": faster_config.get("device", "cpu") if asr_adapter else "",
        "compute_type": faster_config.get("compute_type", "int8") if asr_adapter else "",
        "local_files_only": faster_config.get("local_files_only", False),
    }


def _read_manual_transcriptions(path: str | Path) -> dict[str, dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return {row["candidate_id"]: row for row in csv.DictReader(handle)}


def _audio_report(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        [
            "# Audio Evaluation Report",
            "",
            f"- Items evaluated: {len(rows)}",
            "- ASR WER/CER is a proxy for intelligibility, not a perfect TTS pronunciation measure.",
            "- ASR WER/CER is a relative proxy for TTS intelligibility, not a perfect pronunciation-quality score.",
            "- High WER/CER may reflect TTS weakness, ASR weakness, or the phoneme-heavy nature of generated material.",
            "- Use one fixed ASR profile for the main TTS comparison to avoid confounding TTS differences with ASR model differences.",
            "- Human listening review is recommended for clinical suitability.",
            "",
        ]
    )


def _tts_asr_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if not row.get("tts_adapter"):
            continue
        key = (
            row.get("asr_profile", ""),
            row.get("asr_model_name", ""),
            row.get("tts_adapter", ""),
            row.get("tts_model_or_voice", ""),
            row.get("target_class", ""),
            row.get("saturation_level", ""),
            row.get("text_type", ""),
        )
        grouped.setdefault(key, []).append(row)
    output = []
    for key, group in grouped.items():
        evaluated = [row for row in group if row.get("wer") not in {"", None}]
        failed = [row for row in group if row.get("eval_status") not in {"success", "technical_only"}]
        output.append(
            {
                "asr_profile": key[0],
                "asr_model_name": key[1],
                "tts_adapter": key[2],
                "tts_model_or_voice": key[3],
                "target_class": key[4],
                "saturation_level": key[5],
                "text_type": key[6],
                "count_evaluated": len(evaluated),
                "count_failed": len(failed),
                "average_wer": _average(row.get("wer") for row in evaluated),
                "average_cer": _average(row.get("cer") for row in evaluated),
                "worst_wer_examples": _worst_examples(evaluated, "wer"),
                "worst_cer_examples": _worst_examples(evaluated, "cer"),
            }
        )
    return output


def _average(values) -> float:
    parsed = [float(value) for value in values if value not in {"", None}]
    return sum(parsed) / len(parsed) if parsed else 0.0


def _worst_examples(rows: list[dict[str, Any]], metric: str) -> str:
    sorted_rows = sorted(rows, key=lambda row: float(row.get(metric) or 0), reverse=True)
    return "; ".join(f"{row.get('candidate_id', '')}:{row.get(metric, '')}" for row in sorted_rows[:3])
