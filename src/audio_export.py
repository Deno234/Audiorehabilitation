"""Export native comparison WAVs without importing or invoking TTS models."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from filelock import FileLock

from .audio_formats import (
    conversion_spec, file_hash, read_native, safe_component, staged_path, validate_rate,
    write_derivative,
)
from .report import write_csv
from .tts import TTS_COMPARISON_MANIFEST_FIELDS


ADAPTERS = ("espeak_ng", "coqui_vits_hr", "speecht5_hr")
FIELDS = [*TTS_COMPARISON_MANIFEST_FIELDS, "source_run", "export_status", "export_error"]
SOURCE_FIELDS = (
    "run_id", "candidate", "normalized_text", "model", "source_adapter", "prompt_strategy",
    "target_class", "saturation_level", "text_type", "tts_model_or_voice",
    "croatian_voice_or_model_confirmed", "speaker_embedding_source", "synthesis_status", "error",
)
MANIFEST = "audio_export_manifest.csv"


@dataclass
class ExportResult:
    manifest: Path
    converted: int
    reused: int
    failed: int
    archive: Path | None


def _inventory(root: Path) -> dict:
    sources = {}
    with (root / "tts_comparison_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            adapter = row["tts_adapter"]
            if adapter not in ADAPTERS:
                raise ValueError(f"Unrecognized adapter in source manifest: {adapter}")
            key = adapter, safe_component(row["candidate_id"])
            if key in sources:
                raise ValueError(f"Duplicate (adapter, candidate_id) in source manifest: {key}")
            sources[key] = row
    for adapter in ADAPTERS:
        for path in (root / adapter).glob("*_raw.wav"):
            key = adapter, safe_component(path.name.removesuffix("_raw.wav"))
            sources.setdefault(key, None)
    if not sources:
        raise ValueError(f"No comparison recordings or manifest entries in {root}")
    if len({(a, c.casefold()) for a, c in sources}) != len(sources):
        raise ValueError("Case-insensitive candidate filename collision.")
    return sources


def _checkpoint(manifest: Path, entries: dict):
    with staged_path(manifest) as temp:
        write_csv(temp, list(entries.values()), FIELDS)
        temp.replace(manifest)


def _package(path: Path, output: Path, rows: list[dict]):
    csv_text = StringIO(newline="")
    writer = csv.DictWriter(csv_text, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    with staged_path(path) as temp:
        with ZipFile(temp, "w", ZIP_DEFLATED) as archive:
            archive.writestr(MANIFEST, csv_text.getvalue().encode("utf-8"))
            for row in rows:
                audio = output / row["audio_path"]
                content = audio.read_bytes()
                if sha256(content).hexdigest() != row["audio_sha256"]:
                    raise ValueError(f"Export changed before packaging: {audio}")
                archive.writestr(row["audio_path"], content)
        temp.replace(path)


def export_audio_formats(input_dir: str | Path, output_dir: str | Path, sample_rates,
                         *, resampling_method: str = "polyphase", make_zip: bool = False) -> ExportResult:
    root, output = Path(input_dir).resolve(), Path(output_dir).resolve()
    if root.is_relative_to(output) or output.is_relative_to(root):
        raise ValueError("Input and export directories must be separate, non-overlapping trees.")
    spec = conversion_spec(resampling_method)
    rates = sorted({validate_rate(rate) for rate in sample_rates})
    if not rates:
        raise ValueError("Select at least one target sample rate.")
    sources = _inventory(root)
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / MANIFEST
    if not manifest.exists() and any(p.name != ".audio-export.lock" for p in output.iterdir()):
        raise ValueError(f"Use an empty directory or an existing audio export: {output}")
    with FileLock(str(output / ".audio-export.lock"), timeout=0):
        return _export(root, output, manifest, sources, rates, spec, make_zip)


def _export(root, output, manifest, sources, rates, spec, make_zip):
    entries = {}
    if manifest.exists():
        with manifest.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != FIELDS:
                raise ValueError(f"Unrecognized export manifest: {manifest}")
            for row in reader:
                if row["resampling_method"] != spec["resampling_method"] or row["source_run"] != root.name:
                    raise ValueError(f"Destination contains {row['source_run']} / {row['resampling_method']}. "
                                     "Use a separate export directory.")
                if (row["tts_adapter"], row["candidate_id"]) in sources:
                    entries[row["audio_path"]] = row
    previous = entries.copy()
    selection = []
    for adapter, candidate in sorted(sources):
        for rate in rates:
            name = f"{adapter}/{rate}Hz/{candidate}.wav"
            dest = output / name
            if dest.resolve() != dest or (dest.exists() and name not in previous):
                raise ValueError(f"Unmanaged or redirected export destination: {dest}")
            selection.append(name)
            entries[name] = {**previous.get(name, {}), "source_run": root.name, "tts_adapter": adapter,
                             "candidate_id": candidate, "audio_path": name, "export_status": "pending",
                             "target_sample_rate": rate}
            if name not in previous:
                entries[name].update(spec)
    # Claim paths before any WAV is written. Interrupted, uncheckpointed rows can be regenerated.
    _checkpoint(manifest, entries)
    converted = reused = failed = 0
    for index, ((adapter, candidate), metadata) in enumerate(sorted(sources.items()), 1):
        raw = Path(adapter) / f"{candidate}_raw.wav"
        source_error = ""
        native = None
        try:
            if metadata is None:
                raise ValueError("Native WAV has no matching source manifest row.")
            decoder = "ffmpeg" if metadata.get("raw_decoder") == "ffmpeg" else None
            native = read_native(root / raw, ffmpeg_executable=decoder)
        except (OSError, ValueError, EOFError) as exc:
            source_error = str(exc)
        for rate in rates:
            name = f"{adapter}/{rate}Hz/{candidate}.wav"
            dest = output / name
            # Carry research metadata, never a previous derivative's technical measurements.
            row = {field: (metadata or {}).get(field, "") for field in SOURCE_FIELDS}
            row.update(spec, tts_adapter=adapter, candidate_id=candidate, raw_audio_path=raw.as_posix(),
                       source_run=root.name, target_sample_rate=rate, audio_path=name)
            try:
                if source_error:
                    raise ValueError(source_error)
                row.update(native.metadata)
                old = previous.get(name, {})
                if (old.get("export_status") in {"success", "pending"} and old.get("raw_sha256") == row["raw_sha256"]
                        and all(old.get(k) == v for k, v in spec.items())
                        and dest.is_file() and file_hash(dest) == old["audio_sha256"]):
                    row = {**old, **row}
                    reused += 1
                else:
                    row.update(write_derivative(native, dest, rate, spec["resampling_method"]))
                    converted += 1
                row.update(export_status="success", export_error="", suitable_for_audio_eval="yes")
            except (OSError, ValueError, EOFError) as exc:
                row.update(export_status="failed", export_error=str(exc), suitable_for_audio_eval="no")
                failed += 1
            entries[name] = row
        if index % 32 == 0:
            _checkpoint(manifest, entries)
    _checkpoint(manifest, entries)
    archive = None
    if make_zip and not failed:
        archive = output / ("audio_" + "_".join(map(str, rates)) + "Hz.zip")
        _package(archive, output, [entries[key] for key in selection])
    return ExportResult(manifest, converted, reused, failed, archive)

