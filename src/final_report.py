"""Final scientific Markdown report builder."""

from __future__ import annotations

import csv
from pathlib import Path


REQUIRED_SECTIONS = [
    "Title",
    "Abstract",
    "Research question",
    "Relation to the reference paper",
    "ROGJ task 16 relation",
    "Dataset / generated candidate description",
    "Croatian phoneme classes",
    "Saturation formula",
    "Experimental design",
    "Models/sources",
    "Prompt strategies",
    "Text evaluation metrics",
    "Lexical validation levels",
    "Audio generation",
    "Audio evaluation",
    "Main findings",
    "Limitations",
    "Future work",
]


def build_final_report(comparison_dir: str | Path | None, audio_eval_dir: str | Path | None, output: str | Path) -> Path:
    comparison = Path(comparison_dir) if comparison_dir else None
    audio = Path(audio_eval_dir) if audio_eval_dir else None
    audio_eval_text = _audio_evaluation_text(audio)
    lines = ["# Evaluation of Language Generative Models for Auditory Rehabilitation Needs", ""]
    content = {
        "Title": "Evaluation of language generative models for auditory rehabilitation needs",
        "Abstract": "This report summarizes the reproducible Croatian phoneme-controlled generation workflow.",
        "Research question": "Can LLM sources generate Croatian words and sentences satisfying deterministic phoneme-class saturation constraints?",
        "Relation to the reference paper": "The paper-style prompt and saturation evaluation are reproduced where possible.",
        "ROGJ task 16 relation": "The workflow supports a full comparison and audio layer for the task.",
        "Dataset / generated candidate description": "Candidate-level CSVs and manifests describe the generated material.",
        "Croatian phoneme classes": "N, SN, S, SV, V as defined in the project phoneme class table.",
        "Saturation formula": "target_count / total_phonemes * 100.",
        "Experimental design": "ChatGPT Plus manual import and local Ollama generation can be compared.",
        "Models/sources": "ChatGPT Plus manual; Ollama local.",
        "Prompt strategies": "paper_style and strict_plain_list.",
        "Text evaluation metrics": "Saturation pass rate, duplicate rate, PCD, failure reasons, and HJP/manual review where available.",
        "Lexical validation levels": "Technical phoneme validity, Hunspell Croatian dictionary/spellcheck screening, manual HJP validity, semantic naturalness, and clinical suitability are separate levels. Hunspell is scalable but not identical to HJP; it may reject valid inflected Croatian words or accept words that are not appropriate for rehabilitation context. ChatGPT is not ground-truth validation.",
        "Audio generation": "not yet evaluated" if not audio else "See audio manifest and evaluation directory.",
        "Audio evaluation": audio_eval_text,
        "Main findings": "not yet evaluated" if not comparison else "See comparison report.",
        "Limitations": "HJP is not automatically verified; Hunspell is automatic lexical screening, not final linguistic or clinical validation; ChatGPT Plus is manual; Ollama varies by model/hardware; eSpeak NG is a technical baseline; TTS quality requires listening review; generated material is not clinically approved.",
        "Future work": "Human listening studies, clinical review, and stronger Croatian lexical resources.",
    }
    for section in REQUIRED_SECTIONS:
        lines.extend([f"## {section}", content[section], ""])
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _audio_evaluation_text(audio_dir: Path | None) -> str:
    if not audio_dir:
        return "not yet evaluated"
    summary_path = audio_dir / "audio_eval_summary.csv"
    if not summary_path.exists():
        return "WAV technical checks and optional ASR/manual WER/CER."
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    profiles = sorted({row.get("asr_profile", "") for row in rows if row.get("asr_profile")})
    models = sorted({row.get("asr_model_name", "") for row in rows if row.get("asr_model_name")})
    if profiles or models:
        profile_text = ", ".join(profiles) if profiles else "direct adapter"
        model_text = ", ".join(models) if models else "unspecified ASR model"
        return f"WAV technical checks and ASR WER/CER were evaluated with ASR profile(s): {profile_text}; model(s): {model_text}."
    return "WAV technical checks and optional ASR/manual WER/CER."
