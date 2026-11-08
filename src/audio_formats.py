"""Native WAV decoding and deterministic PCM16 derivatives for TTS experiments."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from math import gcd
import ntpath
from pathlib import Path, PureWindowsPath
import struct
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory

import numpy as np
import scipy
from scipy.io import wavfile
from scipy.signal import resample_poly


METHODS = ("polyphase", "legacy-nearest")
CONVERSION_FIELDS = [
    "raw_audio_path", "raw_sample_rate", "raw_channels", "raw_encoding",
    "raw_sample_width_bits", "raw_decoder", "raw_frames", "raw_duration_seconds", "raw_sha256",
    "target_sample_rate", "resampling_method", "resampling_applied", "converter_version",
    "conversion_settings", "gain", "frames", "encoding", "audio_sha256",
]


def validate_method(method: str) -> str:
    if method not in METHODS:
        raise ValueError(f"Unknown resampling method {method!r}. Choose from {METHODS}.")
    return method


def validate_rate(rate: int) -> int:
    if not isinstance(rate, int) or isinstance(rate, bool) or not 1 <= rate <= 384000:
        raise ValueError(f"Expected an integer sample rate between 1 and 384000 Hz, got {rate!r}.")
    return rate


def safe_component(value: str) -> str:
    path = PureWindowsPath(value)
    reserved = ntpath.isreserved(value) if hasattr(ntpath, "isreserved") else path.is_reserved()
    if (not value or path.name != value or value in {".", ".."} or reserved
            or value.endswith((" ", ".")) or any(c in '<>:"/\\|?*' or ord(c) < 32 for c in value)):
        raise ValueError(f"Invalid adapter or candidate filename component: {value!r}")
    return value


@contextmanager
def staged_path(destination: Path):
    """A closed, same-filesystem temporary file, usable by Windows subprocesses."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destination.parent, prefix=".audio-", suffix=destination.suffix,
                            delete=False) as handle:
        path = Path(handle.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@dataclass
class NativeAudio:
    samples: np.ndarray  # frames x channels, in native integer or floating-point units
    metadata: dict


def _decode_with_ffmpeg(path: Path, executable: str, data: bytes, encoding: str, bits) -> NativeAudio:
    # Decode only. Preserve rate/channels and pass the samples through our selected resampler.
    with TemporaryDirectory() as folder:
        decoded = Path(folder) / "decoded.wav"
        args = [executable, "-v", "error", "-xerror", "-i", str(path), "-c:a", "pcm_f32le", str(decoded)]
        result = subprocess.run(args, capture_output=True)
        if result.returncode:
            raise ValueError(f"ffmpeg could not decode {path}: {result.stderr.decode(errors='replace')}")
        native = read_native(decoded)
    native.metadata.update(raw_encoding=encoding, raw_sample_width_bits=bits, raw_decoder="ffmpeg",
                           raw_sha256=sha256(data).hexdigest())
    return native


def read_native(path: Path, *, ffmpeg_executable: str | None = None) -> NativeAudio:
    data = path.read_bytes()
    if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError(f"Git LFS pointer in place of WAV: {path}")
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        if ffmpeg_executable:
            return _decode_with_ffmpeg(path, ffmpeg_executable, data, "external", "")
        raise ValueError(f"Expected a RIFF/WAVE file: {path}")
    end = int.from_bytes(data[4:8], "little") + 8
    if end > len(data):
        raise ValueError(f"Truncated RIFF file: {path}")

    # Check declared frame boundaries; some decoders accept a short final data chunk.
    offset = 12
    bits = block_align = payload = codec = 0
    while offset + 8 <= end:
        kind, size = struct.unpack_from("<4sI", data, offset)
        start = offset + 8
        if start + size > end:
            raise ValueError(f"Truncated WAV chunk: {path}")
        if kind == b"fmt " and size >= 16:
            codec, channels, rate, _, block_align, bits = struct.unpack_from("<HHIIHH", data, start)
            if not channels or not block_align:
                raise ValueError(f"Invalid channel count or block alignment: {path}")
            validate_rate(rate)
            if codec == 0xfffe and size >= 40:
                codec = int.from_bytes(data[start + 24:start + 26], "little")
        elif kind == b"data":
            payload = size
        offset = start + size + (size % 2)
    if codec and codec not in (1, 3) and ffmpeg_executable:
        return _decode_with_ffmpeg(path, ffmpeg_executable, data, f"WAVE_FORMAT_{codec:04x}", bits)
    if not block_align or not payload or payload % block_align:
        raise ValueError(f"Empty or incomplete WAV frames: {path}")

    try:
        rate, samples = wavfile.read(BytesIO(data))
    except (NotImplementedError, struct.error, ZeroDivisionError) as exc:
        raise ValueError(f"Unsupported or malformed WAV: {path}: {exc}") from exc
    if samples.ndim == 1:
        samples = samples[:, None]
    if len(samples) != payload // block_align or not np.isfinite(samples).all():
        raise ValueError(f"Incomplete or non-finite WAV samples: {path}")
    validate_rate(rate)
    return NativeAudio(samples, {
        "raw_sample_rate": rate, "raw_channels": samples.shape[1], "raw_sample_width_bits": bits,
        "raw_encoding": "FLOAT" if samples.dtype.kind == "f" else "PCM",
        "raw_decoder": "scipy", "raw_frames": len(samples), "raw_duration_seconds": len(samples) / rate,
        "raw_sha256": sha256(data).hexdigest(),
    })


def conversion_spec(method: str) -> dict:
    validate_method(method)
    settings = ("kaiser-beta=5;pad=constant-zero;downmix=mean;quantize=rint"
                if method == "polyphase" else "index=python-round;pcm16-downmix=floor")
    return {
        "resampling_method": method, "conversion_settings": settings,
        "converter_version": f"1 (numpy {np.__version__}, scipy {scipy.__version__})",
    }


def _pcm_units(samples: np.ndarray) -> np.ndarray:
    """Float64 measured in 16-bit LSBs. SciPy left-justifies packed 24-bit PCM."""
    values = samples.astype(np.float64)
    if samples.dtype.kind == "u":
        return (values - 128) * 256
    if samples.dtype.kind == "i":
        return values * (32768 / (2 ** (8 * samples.dtype.itemsize - 1)))
    return values * 32768


def write_derivative(native: NativeAudio, destination: Path, rate: int,
                     method: str = "polyphase", channels: int = 1) -> dict:
    spec = conversion_spec(method)
    validate_rate(rate)
    source_rate = native.metadata["raw_sample_rate"]
    samples = _pcm_units(native.samples)
    if channels != samples.shape[1]:
        if channels == 1:
            samples = samples.mean(axis=1, keepdims=True)
            if method == "legacy-nearest" and native.samples.dtype == np.int16:
                samples = np.floor(samples)  # historical integer stereo (left + right) // 2
        elif channels == 2 and samples.shape[1] == 1:
            samples = np.repeat(samples, 2, axis=1)
        else:
            raise ValueError(f"Unsupported channel conversion: {samples.shape[1]} to {channels}")
    if source_rate != rate:
        if method == "polyphase":
            divisor = gcd(source_rate, rate)
            samples = resample_poly(samples, rate // divisor, source_rate // divisor,
                                    axis=0, window=("kaiser", 5.0), padtype="constant")
        else:
            count = max(1, round(len(samples) * rate / source_rate))
            indices = [min(len(samples) - 1, round(i * source_rate / rate)) for i in range(count)]
            samples = samples[indices]
    if not np.isfinite(samples).all():
        raise ValueError("Non-finite values after audio conversion.")
    peak, trough = float(samples.max()), float(samples.min())
    gain = min(1.0, 32767 / peak if peak > 32767 else 1.0,
               -32768 / trough if trough < -32768 else 1.0)
    pcm = np.rint(samples * gain).clip(-32768, 32767).astype(np.int16)
    with staged_path(destination) as temp:
        wavfile.write(temp, rate, pcm)
        digest = file_hash(temp)
        temp.replace(destination)
    return {
        **spec, "target_sample_rate": rate, "resampling_applied": source_rate != rate,
        "sample_rate": rate, "channels": channels, "sample_width_bits": 16,
        "encoding": "PCM", "frames": len(pcm), "duration_seconds": len(pcm) / rate,
        "gain": gain, "audio_sha256": digest,
    }

