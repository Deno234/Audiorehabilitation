"""Phase-two ASR/STT evaluation scaffolds."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def wer(reference: str, hypothesis: str) -> float:
    """Compute word error rate with a small dynamic-programming edit distance."""
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return _edit_distance(ref_words, hyp_words) / len(ref_words)


def cer(reference: str, hypothesis: str) -> float:
    """Compute character error rate."""
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return _edit_distance(list(reference), list(hypothesis)) / len(reference)


def _edit_distance(left: list[str], right: list[str]) -> int:
    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            substitution = previous[j - 1] + (left_item != right_item)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


class LocalWhisperTranscriber:
    def transcribe(self, *_args: Any, **_kwargs: Any) -> str:
        raise NotImplementedError("Local Whisper/faster-whisper is a phase-two scaffold.")


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_path: str,
        language: str = "hr",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        if not model_path:
            raise RuntimeError("faster_whisper model_path is required; automatic model downloads are disabled.")
        if not Path(model_path).exists():
            raise RuntimeError(f"faster_whisper model_path does not exist: {model_path}. Automatic downloads are disabled.")
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError("faster-whisper is not installed. Install it locally and provide a model_path.") from exc
        self.language = language
        self.model = WhisperModel(model_path, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str) -> str:
        segments, _info = self.model.transcribe(audio_path, language=self.language)
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
