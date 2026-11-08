import csv
from hashlib import sha256
from pathlib import Path
import sys
import wave
from zipfile import ZipFile

import numpy as np
import pytest
from scipy.io import wavfile

from src import audio_export, tts
from src.audio_eval import evaluate_audio
from src.audio_export import ADAPTERS, export_audio_formats
from src.audio_formats import read_native, write_derivative
from src.pipeline import main
from src.report import write_csv
from src.tts_comparison import compare_tts_audio


def records(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def mock_run(root, count=1, adapters=ADAPTERS):
    rows = []
    for adapter in adapters:
        folder = root / adapter
        folder.mkdir(parents=True)
        for i in range(count):
            candidate = f"c{i}"
            signal = np.array([0, -32768, -3, 14, 5000, 32767, 0], dtype=np.int16)
            wavfile.write(folder / f"{candidate}_raw.wav", 22050, signal)
            rows.append(dict(candidate_id=candidate, candidate="Čuješ li?", normalized_text="čuješ li",
                             tts_adapter=adapter, tts_model_or_voice=f"voice-{adapter}",
                             synthesis_status="success"))
    write_csv(root / "tts_comparison_manifest.csv", rows)


@pytest.mark.parametrize(("target", "expected"), [
    (8000, [-2, 20]), (16000, [-2, 10, 20, -32]),
    (32000, [-2, -2, 10, 20, 20, 20, -32, -32]),
    (10000, [-2, 20]),  # round(4 * 10000 / 16000) = round(2.5) = 2
])
def test_legacy_exact_pcm(tmp_path, target, expected):
    source, dest = tmp_path / "native.wav", tmp_path / "out.wav"
    wavfile.write(source, 16000, np.array([[-3, 0], [9, 12], [19, 21], [-33, -30]], dtype=np.int16))
    meta = write_derivative(read_native(source), dest, target, "legacy-nearest")
    with wave.open(str(dest)) as stream:
        assert stream.getparams()[:4] == (1, 2, target, len(expected))
        assert stream.readframes(len(expected)) == np.array(expected, dtype="<i2").tobytes()
    assert meta["resampling_applied"] == (target != 16000)
    assert meta["resampling_method"] == "legacy-nearest"


@pytest.mark.parametrize("target", [16000, 22050, 44100, 48000, 32003])
def test_polyphase_tone_and_duration(tmp_path, target):
    source, dest = tmp_path / "native.wav", tmp_path / "export.wav"
    rate = 22050
    time = np.arange(2207) / rate
    wavfile.write(source, rate, (0.4 * np.sin(2 * np.pi * 1000 * time)).astype(np.float32))
    native = read_native(source)
    meta = write_derivative(native, dest, target)
    fs, data = wavfile.read(dest)
    assert fs == target and data.dtype == np.int16 and data.ndim == 1
    assert abs(len(data) / fs - len(time) / rate) < 1 / fs
    reference = 0.4 * np.sin(2 * np.pi * 1000 * np.arange(len(data)) / fs)
    np.testing.assert_allclose(data[50:-50] / 32768, reference[50:-50], atol=0.002)
    assert meta["resampling_applied"] == (rate != target)
    assert meta["resampling_method"] == "polyphase"


def test_anti_alias_filter(tmp_path):
    src, dst = tmp_path / "tone.wav", tmp_path / "alias.wav"
    t = np.arange(4800) / 48000
    wavfile.write(src, 48000, np.sin(2 * np.pi * 12000 * t).astype(np.float32))
    write_derivative(read_native(src), dst, 16000)
    assert np.max(np.abs(wavfile.read(dst)[1][32:-32])) < 100


@pytest.mark.parametrize("bits", [8, 16, 24, 32])
def test_native_pcm_width_level_and_full_scale(tmp_path, bits, monkeypatch):
    native_file, dest = tmp_path / "raw.wav", tmp_path / "converted.wav"
    values = [-(2 ** (bits - 1)), 0, 2 ** (bits - 2)]
    if bits == 16:
        values.append(32767)
    with wave.open(str(native_file), "wb") as stream:
        stream.setparams((1, bits // 8, 22050, 0, "NONE", "not compressed"))
        stream.writeframes(b"".join((v + (128 if bits == 8 else 0)).to_bytes(
            bits // 8, "little", signed=bits != 8) for v in values))
    native = read_native(native_file)
    assert native.metadata["raw_sample_width_bits"] == bits
    monkeypatch.setattr("src.audio_formats.resample_poly", lambda *a, **kw: pytest.fail("same-rate filter"))
    meta = write_derivative(native, dest, 22050)
    expected = [-32768, 0, 16384] + ([32767] if bits == 16 else [])
    np.testing.assert_array_equal(wavfile.read(dest)[1], expected)
    assert meta["gain"] == 1.0


def test_stereo_float_overload_gain(tmp_path):
    src, dst = tmp_path / "raw.wav", tmp_path / "export.wav"
    wavfile.write(src, 16000, np.array([[1., 3.], [-2., -2.], [1., -1.]], dtype=np.float32))
    native = read_native(src)
    meta = write_derivative(native, dst, 16000)
    assert meta["gain"] == pytest.approx(32767 / 65536)
    np.testing.assert_array_equal(wavfile.read(dst)[1], [32767, -32767, 0])


@pytest.mark.parametrize("method", ["polyphase", "legacy-nearest"])
def test_synthesis_export_same_wav_and_provenance(tmp_path, monkeypatch, method):
    source = tmp_path / "candidates.csv"
    write_csv(source, [dict(candidate_id="c0", candidate="čuj")])
    run = tmp_path / "synth"
    def generate(row, config, path):
        wavfile.write(path, 22050, np.array([0, 7000, -5432, 123, -30000, 0], dtype=np.int16))
        return ""
    monkeypatch.setattr(tts, "_generate_native", generate)
    config = {"tts_comparison": {"adapters": [{"name": "espeak_ng", "enabled": True}]}}
    kwargs = {} if method == "polyphase" else {"resampling_method": method}
    synthesis = tts.synthesize_audio_comparison(source, config, run, **kwargs)
    row, = records(synthesis)
    final = Path(row["audio_path"])
    raw = run / row["raw_audio_path"]
    before = raw.read_bytes()
    expected = final.read_bytes()
    assert row["resampling_method"] == method and row["resampling_applied"] == "True"
    final.write_bytes(b"unused standardized file")
    out = tmp_path / "out"
    result = export_audio_formats(run, out, [16000, 22050], **kwargs)
    for entry in records(result.manifest):
        assert entry["resampling_method"] == method
        assert entry["raw_sha256"] == sha256(before).hexdigest()
        actual = (out / entry["audio_path"]).read_bytes()
        if entry["target_sample_rate"] == "16000":
            assert actual == expected and row["audio_sha256"] == entry["audio_sha256"]
        else:
            assert actual == before and entry["resampling_applied"] == "False"
    with pytest.raises(FileExistsError):
        tts.synthesize_audio_comparison(source, config, run)
    assert raw.read_bytes() == before


def test_synthesis_preflight_protects_later_raw(tmp_path, monkeypatch):
    root = tmp_path / "run"
    folder = root / "espeak_ng"
    folder.mkdir(parents=True)
    original = folder / "b_raw.wav"
    original.write_bytes(b"preserve me")
    source = tmp_path / "candidates.csv"
    write_csv(source, [{"candidate_id": "a"}, {"candidate_id": "b"}])
    monkeypatch.setattr(tts, "_generate_native", lambda *a: pytest.fail("inference during preflight"))
    with pytest.raises(FileExistsError):
        tts.synthesize_audio_comparison(source, {"tts_comparison": {"adapters": [
            {"name": "espeak_ng", "enabled": True}]}}, root)
    assert original.read_bytes() == b"preserve me"
    assert list(folder.iterdir()) == [original]
    assert not (root / "tts_comparison_manifest.csv").exists()


def test_single_rate_zip_and_portable_reports_after_multirate(tmp_path, monkeypatch):
    root, out = tmp_path / "run", tmp_path / "out"
    mock_run(root)
    result = export_audio_formats(root, out, [16000, 22050, 44100, 48000, 22050])
    assert result.converted == 12
    monkeypatch.setattr(sys, "argv", ["pipeline", "--export-audio-formats", "--input-dir", str(root),
                                     "--output-dir", str(out), "--sample-rates", "22050", "--zip"])
    main()
    unpacked = tmp_path / "collaborator"
    with ZipFile(out / "audio_22050Hz.zip") as archive:
        assert archive.testzip() is None and len(archive.namelist()) == 4
        archive.extractall(unpacked)
    manifest = unpacked / audio_export.MANIFEST
    rows = records(manifest)
    assert {r["tts_adapter"] for r in rows} == set(ADAPTERS)
    for row in rows:
        assert row["candidate"] == "Čuješ li?" and row["tts_model_or_voice"] == "voice-" + row["tts_adapter"]
        assert row["audio_path"] == f"{row['tts_adapter']}/22050Hz/c0.wav"
        assert sha256((unpacked / row["audio_path"]).read_bytes()).hexdigest() == row["audio_sha256"]
        with wave.open(str(unpacked / row["audio_path"])) as stream:
            assert stream.getparams()[:3] == (1, 2, 22050)
    summary = records(compare_tts_audio(manifest, tmp_path / "report")["tts_audio_summary"])
    assert all(float(r["format_compliance_rate"]) == 1 for r in summary)
    combined = records(evaluate_audio(result.manifest, tmp_path / "eval")["audio_eval_tts_summary"])
    assert len(combined) == 12
    # An inaccurate declared rate must fail, even when measured Hz matches the original manifest.
    rows[0]["target_sample_rate"] = "44100"
    write_csv(manifest, rows)
    summary = records(compare_tts_audio(manifest, tmp_path / "report")["tts_audio_summary"])
    mismatch, = [r for r in summary if r["target_sample_rate"] == "44100"]
    assert float(mismatch["sample_rate_compliance_rate"]) == 0
    evaluated = records(evaluate_audio(manifest, tmp_path / "relocated_eval")["audio_eval_summary"])
    assert evaluated[0]["sample_rate_compliant"] == "False"
    assert all(row["format_compliant"] == "True" for row in evaluated[1:])
    (unpacked / rows[0]["audio_path"]).unlink()
    failure, = records(compare_tts_audio(manifest, tmp_path / "report")["tts_failure_summary"])
    assert failure["stage"] == "validation" and failure["failure_reason"]


def test_historical_rate_override(tmp_path):
    path = tmp_path / "c.wav"
    wavfile.write(path, 22050, np.zeros(7, dtype=np.int16))
    manifest = write_csv(tmp_path / "old.csv", [dict(tts_adapter="espeak_ng", audio_path=str(path),
                                                       sample_rate=22050, synthesis_status="success")])
    def compliance(**kwargs):
        row, = records(compare_tts_audio(manifest, tmp_path / "report", **kwargs)["tts_audio_summary"])
        return float(row["format_compliance_rate"])
    assert compliance() == 0 and compliance(expected_sample_rate=22050) == 1


def test_invalid_sources_manifest_and_resume(tmp_path, monkeypatch):
    root, out = tmp_path / "run", tmp_path / "out"
    mock_run(root, count=7, adapters=["espeak_ng"])
    folder = root / "espeak_ng"
    files = sorted(folder.glob("*_raw.wav"))
    template = files[0].read_bytes()
    files[0].unlink()
    files[1].write_bytes(template[:-2])
    files[2].write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
    files[3].write_bytes(b"bad wav")
    wavfile.write(files[4], 22050, np.array([np.nan], dtype=np.float32))
    wavfile.write(files[5], 22050, np.array([], dtype=np.int16))
    orphan = folder / "unknown_raw.wav"
    orphan.write_bytes(template)
    result = export_audio_formats(root, out, [22050, 44100], make_zip=True)
    assert (result.converted, result.failed, result.archive) == (2, 14, None)
    rows = records(result.manifest)
    assert all(r["export_error"] for r in rows if r["export_status"] == "failed")
    assert "LFS pointer" in next(r["export_error"] for r in rows if r["candidate_id"] == "c2")
    calls = []
    def transcribe(path):
        calls.append(path)
        return "čuješ li"
    evaluate_audio(result.manifest, tmp_path / "eval", asr_adapter="mock", asr_transcriber=transcribe)
    assert len(calls) == 2
    monkeypatch.setattr(sys, "argv", ["pipeline", "--export-audio-formats", "--input-dir", str(root),
                                     "--output-dir", str(out), "--sample-rates", "22050"])
    with pytest.raises(SystemExit) as exit_status:
        main()
    assert exit_status.value.code == 1
    for path in files[:6]:
        path.write_bytes(template)
    orphan.unlink()
    repaired = export_audio_formats(root, out, [22050, 44100], make_zip=True)
    assert (repaired.failed, repaired.reused, repaired.converted) == (0, 2, 12)
    (out / "espeak_ng/22050Hz/c0.wav").write_bytes(b"tampered")
    assert export_audio_formats(root, out, [22050]).converted == 1
    wavfile.write(files[0], 16000, np.array([1, 2, 3], dtype=np.int16))
    assert export_audio_formats(root, out, [22050]).converted == 1
    with pytest.raises(ValueError, match="separate export directory"):
        export_audio_formats(root, out, [16000], resampling_method="legacy-nearest")
    with pytest.raises(ValueError, match="non-overlapping"):
        export_audio_formats(root, root / "espeak_ng", [16000])


def test_interrupted_export(tmp_path, monkeypatch):
    root, out = tmp_path / "run", tmp_path / "out"
    mock_run(root)
    original = audio_export.write_derivative
    def interrupt(native, dest, rate, method):
        if dest.parent.parent.name == "espeak_ng":
            raise KeyboardInterrupt
        return original(native, dest, rate, method)
    monkeypatch.setattr(audio_export, "write_derivative", interrupt)
    with pytest.raises(KeyboardInterrupt):
        export_audio_formats(root, out, [16000])
    monkeypatch.setattr(audio_export, "write_derivative", original)
    resumed = export_audio_formats(root, out, [16000], make_zip=True)
    assert resumed.failed == 0 and len(records(resumed.manifest)) == 3


def test_full_candidate_coverage_with_mocked_adapters(tmp_path, monkeypatch):
    csv_path = Path("outputs/reports/validated_hjp_candidates_task16_chatgpt_20260604_160319.csv")
    expected = {(a, r["candidate_id"]) for r in records(csv_path) for a in ADAPTERS}
    assert len(expected) == 1065
    def generate(row, config, path):
        wavfile.write(path, 16000, np.array([0, 431, -73], dtype=np.int16))
        return ""
    monkeypatch.setattr(tts, "_generate_native", generate)
    config = {"tts_comparison": {"adapters": [{"name": a, "enabled": True} for a in ADAPTERS]}}
    manifest = tts.synthesize_audio_comparison(csv_path, config, tmp_path / "run")
    assert {(r["tts_adapter"], r["candidate_id"]) for r in records(manifest)
            if r["synthesis_status"] == "success"} == expected
    result = export_audio_formats(tmp_path / "run", tmp_path / "out", [22050], make_zip=True)
    assert result.converted == 1065 and result.failed == 0
    with ZipFile(result.archive) as archive:
        assert len(archive.namelist()) == 1066



def test_explicit_external_decoder_leaves_rate_conversion_to_shared_converter(tmp_path, monkeypatch):
    from types import SimpleNamespace
    source, output = tmp_path / "external.wav", tmp_path / "derived.wav"
    source.write_bytes(b"external adapter encoding")
    def fake_decode(args, capture_output):
        assert "-ar" not in args and "-ac" not in args
        wavfile.write(args[-1], 22050, np.array([0, 0.5, -0.5], dtype=np.float32))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr("src.audio_formats.subprocess.run", fake_decode)
    tts.normalize_wav(source, output, allow_ffmpeg=True)
    assert wavfile.read(output)[0] == 16000
    assert source.read_bytes() == b"external adapter encoding"
    with pytest.raises(ValueError, match="separate files"):
        tts.normalize_wav(source, source, allow_ffmpeg=True)


@pytest.mark.parametrize("rates", [[], [0], [-16000], [384001]])
def test_invalid_target_fails_before_export(tmp_path, rates):
    with pytest.raises(ValueError, match="(rate|Hz)"):
        export_audio_formats(tmp_path / "run", tmp_path / "out", rates)
    assert not (tmp_path / "out").exists()
