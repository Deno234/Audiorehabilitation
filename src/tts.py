"""Local/free Croatian TTS adapters."""

from __future__ import annotations

import csv
from pathlib import Path
import shutil
import shlex
import subprocess
import struct
import wave
from typing import Any

from .report import write_csv


AUDIO_MANIFEST_FIELDS = [
    "run_id",
    "candidate_id",
    "candidate",
    "normalized_text",
    "model",
    "source_adapter",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
    "tts_adapter",
    "tts_voice",
    "tts_command_template",
    "croatian_voice_or_model_confirmed",
    "audio_path",
    "sample_rate",
    "channels",
    "sample_width_bits",
    "duration_seconds",
    "synthesis_status",
    "error",
    "suitable_for_audio_eval",
]

TTS_COMPARISON_MANIFEST_FIELDS = [
    "run_id",
    "candidate_id",
    "candidate",
    "normalized_text",
    "model",
    "source_adapter",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
    "tts_adapter",
    "tts_model_or_voice",
    "croatian_voice_or_model_confirmed",
    "speaker_embedding_source",
    "audio_path",
    "sample_rate",
    "channels",
    "sample_width_bits",
    "duration_seconds",
    "synthesis_status",
    "error",
    "suitable_for_audio_eval",
]


def espeak_ng_available(executable: str = "espeak-ng") -> bool:
    return shutil.which(executable) is not None


def espeak_ng_voices(executable: str = "espeak-ng") -> str:
    if not espeak_ng_available(executable):
        raise RuntimeError("espeak-ng is not installed or not on PATH.")
    result = subprocess.run([executable, "--voices"], check=True, capture_output=True, text=True)
    return result.stdout


def require_croatian_voice(executable: str = "espeak-ng") -> str:
    voices = espeak_ng_voices(executable)
    for line in voices.splitlines():
        parts = line.split()
        if len(parts) >= 4 and (parts[1] == "hr" or parts[3] == "hr"):
            return "hr"
    raise RuntimeError("Croatian eSpeak NG voice 'hr' is not available; refusing non-Croatian fallback.")


def build_espeak_command(executable: str, text: str, output_path: str | Path, voice: str = "hr") -> list[str]:
    return [executable, "-v", voice, "-w", str(output_path), text]


def build_coqui_command(
    executable: str,
    text: str,
    model_name: str,
    output_path: str | Path,
) -> list[str]:
    return [executable, "--text", text, "--model_name", model_name, "--out_path", str(output_path)]


def synthesize_audio(
    input_csv: str | Path,
    adapter: str,
    output_dir: str | Path,
    limit: int | None = None,
    executable: str = "espeak-ng",
    tts_config: dict[str, Any] | None = None,
) -> Path:
    tts_config = tts_config or {}
    if adapter not in {"espeak_ng", "external_command"}:
        raise ValueError("Only espeak_ng and external_command are implemented; Piper is scaffold-only.")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    voice = ""
    command_template = ""
    croatian_confirmed = ""
    if adapter == "espeak_ng":
        voice = require_croatian_voice(executable)
        croatian_confirmed = "yes"
    else:
        external_config = tts_config.get("external_command", tts_config)
        command_template = external_config.get("command_template", "")
        croatian_confirmed = "yes" if external_config.get("croatian_voice_or_model_confirmed") is True else "no"
        if croatian_confirmed != "yes":
            raise RuntimeError("external_command TTS requires croatian_voice_or_model_confirmed: true.")
    with Path(input_csv).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    manifest_rows = []
    for index, row in enumerate(rows[:limit] if limit else rows):
        audio_path = output / f"{row.get('candidate_id') or index:04}.wav"
        error = ""
        status = "success"
        suitable = "yes"
        try:
            text_to_synthesize = row.get("normalized_text") or row.get("candidate", "")
            if adapter == "espeak_ng":
                command = build_espeak_command(executable, text_to_synthesize, audio_path, voice)
            else:
                command = build_external_tts_command(
                    command_template,
                    text_to_synthesize,
                    audio_path,
                    tts_config.get("external_command", tts_config).get("output_wav_argument", "{output_path}"),
                    tts_config.get("external_command", tts_config).get("text_argument", "{text}"),
                )
            subprocess.run(command, check=True, capture_output=True, text=True)
            meta = wav_metadata(audio_path)
        except Exception as exc:
            error = str(exc)
            status = "failed"
            suitable = "no"
            meta = {"sample_rate": "", "channels": "", "sample_width_bits": "", "duration_seconds": ""}
        manifest_rows.append(
            {
                "run_id": row.get("run_id", ""),
                "candidate_id": row.get("candidate_id", ""),
                "candidate": row.get("candidate", ""),
                "normalized_text": row.get("normalized_text", ""),
                "model": row.get("model", ""),
                "source_adapter": row.get("source_adapter", ""),
                "prompt_strategy": row.get("prompt_strategy", ""),
                "target_class": row.get("target_class", ""),
                "saturation_level": row.get("saturation_level", ""),
                "text_type": row.get("text_type", ""),
                "tts_adapter": adapter,
                "tts_voice": voice,
                "tts_command_template": command_template,
                "croatian_voice_or_model_confirmed": croatian_confirmed,
                "audio_path": str(audio_path),
                "sample_rate": meta.get("sample_rate", ""),
                "channels": meta.get("channels", ""),
                "sample_width_bits": meta.get("sample_width_bits", ""),
                "duration_seconds": meta.get("duration_seconds", ""),
                "synthesis_status": status,
                "error": error,
                "suitable_for_audio_eval": suitable,
            }
        )
    return write_csv(output / "audio_manifest.csv", manifest_rows, AUDIO_MANIFEST_FIELDS)


def synthesize_audio_comparison(
    input_csv: str | Path,
    config: dict[str, Any],
    output_dir: str | Path,
    limit: int | None = None,
) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with Path(input_csv).open("r", encoding="utf-8", newline="") as handle:
        candidate_rows = list(csv.DictReader(handle))
    if limit:
        candidate_rows = candidate_rows[:limit]

    audio_config = config.get("audio", {})
    target = {
        "sample_rate": int(audio_config.get("target_sample_rate", 16000)),
        "channels": int(audio_config.get("target_channels", 1)),
        "sample_width_bits": int(audio_config.get("target_sample_width_bits", 16)),
    }
    manifest_rows: list[dict[str, Any]] = []
    for adapter_config in config.get("tts_comparison", {}).get("adapters", []):
        if not adapter_config.get("enabled", False):
            continue
        adapter_name = adapter_config["name"]
        adapter_dir = output / adapter_name
        adapter_dir.mkdir(parents=True, exist_ok=True)
        for index, row in enumerate(candidate_rows):
            manifest_rows.append(
                _synthesize_comparison_row(row, index, adapter_config, adapter_dir, target)
            )
    return write_csv(output / "tts_comparison_manifest.csv", manifest_rows, TTS_COMPARISON_MANIFEST_FIELDS)


def _synthesize_comparison_row(
    row: dict[str, Any],
    index: int,
    adapter_config: dict[str, Any],
    adapter_dir: Path,
    target: dict[str, int],
) -> dict[str, Any]:
    adapter = adapter_config["name"]
    candidate_id = row.get("candidate_id") or f"{index:04}"
    raw_path = adapter_dir / f"{candidate_id}_raw.wav"
    final_path = adapter_dir / f"{candidate_id}.wav"
    model_or_voice = _tts_model_or_voice(adapter_config)
    confirmed = "yes" if adapter_config.get("croatian_voice_or_model_confirmed", adapter == "espeak_ng") else "no"
    base = _manifest_base(row, adapter, model_or_voice, confirmed, final_path)
    try:
        if adapter == "espeak_ng":
            voice = adapter_config.get("voice", "hr")
            if voice != "hr":
                raise RuntimeError("eSpeak NG comparison requires Croatian voice 'hr'.")
            require_croatian_voice(adapter_config.get("executable", "espeak-ng"))
            command = build_espeak_command(adapter_config.get("executable", "espeak-ng"), _row_text(row), raw_path, voice)
            subprocess.run(command, check=True, capture_output=True, text=True)
        elif adapter == "coqui_vits_hr":
            if not adapter_config.get("croatian_voice_or_model_confirmed"):
                raise RuntimeError("coqui_vits_hr requires croatian_voice_or_model_confirmed: true.")
            executable = adapter_config.get("command", "tts")
            if shutil.which(executable) is None:
                raise RuntimeError(f"Coqui TTS CLI is missing: {executable}")
            command = build_coqui_command(
                executable,
                _row_text(row),
                adapter_config.get("model_name", "tts_models/hr/cv/vits"),
                raw_path,
            )
            subprocess.run(command, check=True, capture_output=True, text=True)
        elif adapter == "speecht5_hr":
            speaker_source = _synthesize_speecht5(row, raw_path, adapter_config)
            base["speaker_embedding_source"] = speaker_source
        else:
            raise RuntimeError(f"Unsupported TTS comparison adapter: {adapter}")
        normalize_wav(
            raw_path,
            final_path,
            target_sample_rate=target["sample_rate"],
            target_channels=target["channels"],
            target_sample_width_bits=target["sample_width_bits"],
            ffmpeg_executable=adapter_config.get("ffmpeg_executable", "ffmpeg"),
            allow_ffmpeg=bool(adapter_config.get("allow_ffmpeg", False)),
        )
        meta = wav_metadata(final_path)
        base.update(
            {
                "sample_rate": meta["sample_rate"],
                "channels": meta["channels"],
                "sample_width_bits": meta["sample_width_bits"],
                "duration_seconds": meta["duration_seconds"],
                "synthesis_status": "success",
                "error": "",
                "suitable_for_audio_eval": "yes",
            }
        )
    except Exception as exc:
        base.update(
            {
                "sample_rate": "",
                "channels": "",
                "sample_width_bits": "",
                "duration_seconds": "",
                "synthesis_status": "failed",
                "error": str(exc),
                "suitable_for_audio_eval": "no",
            }
        )
    return base


def _synthesize_speecht5_scaffold(row: dict[str, Any], raw_path: Path, adapter_config: dict[str, Any]) -> None:
    _synthesize_speecht5(row, raw_path, adapter_config)


def _synthesize_speecht5(row: dict[str, Any], raw_path: Path, adapter_config: dict[str, Any]) -> str:
    if not adapter_config.get("croatian_voice_or_model_confirmed"):
        raise RuntimeError("speecht5_hr requires croatian_voice_or_model_confirmed: true.")
    local_files_only = bool(adapter_config.get("local_files_only", True))
    model_path = adapter_config.get("model_path", "")
    processor_path = adapter_config.get("processor_path") or model_path
    vocoder_path = adapter_config.get("vocoder_path", "")
    if local_files_only and not model_path:
        raise RuntimeError("speecht5_hr requires model_path when local_files_only is true; automatic downloads are disabled.")
    if model_path and not Path(model_path).exists():
        raise RuntimeError(f"speecht5_hr model_path does not exist: {model_path}")
    if processor_path and not Path(processor_path).exists():
        raise RuntimeError(f"speecht5_hr processor_path does not exist: {processor_path}")
    if not vocoder_path:
        raise RuntimeError("speecht5_hr requires vocoder_path.")
    if vocoder_path and not Path(vocoder_path).exists():
        raise RuntimeError(f"speecht5_hr vocoder_path does not exist: {vocoder_path}")
    if not adapter_config.get("speaker_embedding_path") and not adapter_config.get("allow_default_zero_speaker_embedding"):
        raise RuntimeError(
            "speecht5_hr requires speaker_embedding_path or allow_default_zero_speaker_embedding: true."
        )
    try:
        import numpy as np
        import soundfile as sf
        import torch
        from transformers import SpeechT5ForTextToSpeech, SpeechT5HifiGan, SpeechT5Processor
    except ImportError as exc:
        raise RuntimeError("speecht5_hr dependencies are missing: install transformers torch soundfile numpy.") from exc

    speaker_embeddings, speaker_source = _load_speecht5_speaker_embedding(adapter_config, np, torch)
    processor = SpeechT5Processor.from_pretrained(processor_path, local_files_only=local_files_only)
    model = SpeechT5ForTextToSpeech.from_pretrained(model_path, local_files_only=local_files_only)
    vocoder = SpeechT5HifiGan.from_pretrained(vocoder_path, local_files_only=local_files_only)
    device = adapter_config.get("device", "cpu")
    if hasattr(model, "to"):
        model = model.to(device)
    if hasattr(vocoder, "to"):
        vocoder = vocoder.to(device)
    if hasattr(speaker_embeddings, "to"):
        speaker_embeddings = speaker_embeddings.to(device)
    inputs = processor(text=_row_text(row), return_tensors="pt")
    if hasattr(inputs, "to"):
        inputs = inputs.to(device)
    elif isinstance(inputs, dict):
        inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
    speech = model.generate_speech(
        inputs["input_ids"],
        speaker_embeddings,
        vocoder=vocoder,
    )
    if hasattr(speech, "detach"):
        speech = speech.detach().cpu().numpy()
    elif hasattr(speech, "cpu"):
        speech = speech.cpu().numpy()
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(raw_path), speech, int(adapter_config.get("raw_sample_rate", 16000)))
    return speaker_source


def _load_speecht5_speaker_embedding(adapter_config: dict[str, Any], np: Any, torch: Any) -> tuple[Any, str]:
    embedding_path = adapter_config.get("speaker_embedding_path", "")
    embedding_dim = int(adapter_config.get("speaker_embedding_dim", 512))
    if embedding_path:
        path = Path(embedding_path)
        if not path.exists():
            raise RuntimeError(f"speecht5_hr speaker_embedding_path does not exist: {embedding_path}")
        embedding = np.load(path)
        source = str(path)
    elif adapter_config.get("allow_default_zero_speaker_embedding"):
        embedding = np.zeros((1, embedding_dim), dtype="float32")
        source = "default_zero_experimental"
    else:
        raise RuntimeError(
            "speecht5_hr requires speaker_embedding_path or allow_default_zero_speaker_embedding: true."
        )
    embedding = np.asarray(embedding, dtype="float32")
    if embedding.ndim == 1:
        embedding = embedding.reshape(1, -1)
    if embedding.ndim != 2 or embedding.shape[0] != 1:
        raise RuntimeError("speecht5_hr speaker embedding must have shape (dim,) or (1, dim).")
    return torch.tensor(embedding), source


def normalize_wav(
    input_path: str | Path,
    output_path: str | Path,
    *,
    target_sample_rate: int = 16000,
    target_channels: int = 1,
    target_sample_width_bits: int = 16,
    ffmpeg_executable: str = "ffmpeg",
    allow_ffmpeg: bool = False,
) -> Path:
    input_wav = Path(input_path)
    output_wav = Path(output_path)
    try:
        with wave.open(str(input_wav), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.getnframes()
            data = handle.readframes(frames)
    except Exception:
        if allow_ffmpeg:
            return _normalize_with_ffmpeg(input_wav, output_wav, target_sample_rate, target_channels, ffmpeg_executable)
        raise RuntimeError("Audio normalization requires readable WAV input or configured ffmpeg.")

    if sample_width != 2:
        if allow_ffmpeg:
            return _normalize_with_ffmpeg(input_wav, output_wav, target_sample_rate, target_channels, ffmpeg_executable)
        raise RuntimeError(f"Unsupported WAV sample width for stdlib normalization: {sample_width * 8} bits.")
    if target_sample_width_bits != 16:
        raise RuntimeError("Stdlib normalization currently supports 16-bit PCM output only.")
    samples = list(struct.unpack("<" + "h" * (len(data) // 2), data)) if data else []
    if channels != target_channels:
        if target_channels == 1 and channels == 2:
            samples = [(samples[i] + samples[i + 1]) // 2 for i in range(0, len(samples), 2)]
            channels = 1
        elif target_channels == 2 and channels == 1:
            samples = [sample for sample in samples for _ in range(2)]
            channels = 2
        else:
            raise RuntimeError(f"Unsupported channel conversion: {channels} to {target_channels}.")
    if sample_rate != target_sample_rate:
        samples = _resample_nearest(samples, sample_rate, target_sample_rate, channels)
        sample_rate = target_sample_rate
    data = struct.pack("<" + "h" * len(samples), *samples) if samples else b""

    output_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(data)
    return output_wav


def _resample_nearest(samples: list[int], source_rate: int, target_rate: int, channels: int) -> list[int]:
    if not samples or source_rate == target_rate:
        return samples
    frame_count = len(samples) // channels
    target_frame_count = max(1, round(frame_count * target_rate / source_rate))
    output: list[int] = []
    for target_index in range(target_frame_count):
        source_index = min(frame_count - 1, round(target_index * source_rate / target_rate))
        start = source_index * channels
        output.extend(samples[start : start + channels])
    return output


def _normalize_with_ffmpeg(
    input_path: Path,
    output_path: Path,
    sample_rate: int,
    channels: int,
    executable: str,
) -> Path:
    if shutil.which(executable) is None:
        raise RuntimeError(f"ffmpeg is required for this audio conversion but is missing: {executable}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            executable,
            "-y",
            "-i",
            str(input_path),
            "-ac",
            str(channels),
            "-ar",
            str(sample_rate),
            "-sample_fmt",
            "s16",
            str(output_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def _manifest_base(
    row: dict[str, Any],
    adapter: str,
    model_or_voice: str,
    confirmed: str,
    audio_path: Path,
) -> dict[str, Any]:
    return {
        "run_id": row.get("run_id", ""),
        "candidate_id": row.get("candidate_id", ""),
        "candidate": row.get("candidate", ""),
        "normalized_text": row.get("normalized_text", ""),
        "model": row.get("model", ""),
        "source_adapter": row.get("source_adapter", ""),
        "prompt_strategy": row.get("prompt_strategy", ""),
        "target_class": row.get("target_class", ""),
        "saturation_level": row.get("saturation_level", ""),
        "text_type": row.get("text_type", ""),
        "tts_adapter": adapter,
        "tts_model_or_voice": model_or_voice,
        "croatian_voice_or_model_confirmed": confirmed,
        "speaker_embedding_source": "",
        "audio_path": str(audio_path),
    }


def _row_text(row: dict[str, Any]) -> str:
    return row.get("normalized_text") or row.get("candidate", "")


def _tts_model_or_voice(adapter_config: dict[str, Any]) -> str:
    if adapter_config["name"] == "espeak_ng":
        return adapter_config.get("voice", "hr")
    if adapter_config["name"] == "coqui_vits_hr":
        return adapter_config.get("model_name", "tts_models/hr/cv/vits")
    if adapter_config["name"] == "speecht5_hr":
        return adapter_config.get("model_path") or adapter_config.get("model_id", "nikolab/speecht5_tts_hr")
    return adapter_config.get("model", "")


def build_external_tts_command(
    command_template: str,
    text: str,
    output_path: str | Path,
    output_wav_argument: str = "{output_path}",
    text_argument: str = "{text}",
) -> list[str]:
    if not command_template.strip():
        raise RuntimeError("external_command TTS requires a non-empty command_template.")
    values = {"text": text, "output_path": str(output_path)}
    command = shlex.split(command_template.format(**values))
    if "{output_path}" not in command_template and output_wav_argument:
        command.extend(shlex.split(output_wav_argument.format(**values)))
    if "{text}" not in command_template and text_argument:
        command.extend(shlex.split(text_argument.format(**values)))
    return command


def wav_metadata(path: str | Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        sample_rate = handle.getframerate()
        channels = handle.getnchannels()
        sample_width_bits = handle.getsampwidth() * 8
        duration = frames / sample_rate if sample_rate else 0.0
    return {
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bits": sample_width_bits,
        "duration_seconds": duration,
    }


class PiperTTS:
    def __init__(self, executable: str, model_path: str) -> None:
        self.executable = executable
        self.model_path = model_path

    def check_ready(self) -> None:
        if not shutil.which(self.executable):
            raise RuntimeError(f"Piper executable is missing: {self.executable}")
        if not Path(self.model_path).exists():
            raise RuntimeError(f"Piper Croatian model is missing: {self.model_path}")
