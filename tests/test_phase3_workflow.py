import csv
from pathlib import Path
import struct
import sys
import types
import wave

import pytest

from src.audio_eval import evaluate_audio, normalize_audio_eval_text, resolve_asr_profile, wav_technical_validation
from src.asr_eval import FasterWhisperTranscriber
from src.comparison import compare_runs
from src.final_report import REQUIRED_SECTIONS, build_final_report
from src.generators import build_planned_requests, export_chatgpt_prompts
from src.lexical_review import export_lexical_review_queue
from src.manual_review import apply_hjp_word_review, export_hjp_word_review
from src.manifest import write_manifest
from src.pipeline import load_config
from src.tts import (
    TTS_COMPARISON_MANIFEST_FIELDS,
    build_coqui_command,
    build_espeak_command,
    build_external_tts_command,
    normalize_wav,
    require_croatian_voice,
    synthesize_audio,
    synthesize_audio_comparison,
)
from src.tts_comparison import compare_tts_audio, export_listening_review_sample
from src.tts_subset import export_tts_candidate_subset
from src.validators import DictionaryValidator, build_hunspell_command, validate_candidate


def write_csv(path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = list(rows[0])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def candidate_rows():
    return [
        {
            "run_id": "run1",
            "candidate_id": "c1",
            "candidate": "panj",
            "model": "ChatGPT Plus",
            "source_adapter": "manual_chatgpt_plus",
            "prompt_strategy": "paper_style",
            "target_class": "N",
            "saturation_level": "50",
            "text_type": "word",
            "normalized_text": "panj",
            "phonemes": "p a nj",
            "saturation_percentage": "66.7",
            "passes_saturation": "True",
            "is_valid": "True",
            "failure_reasons": "",
        },
        {
            "run_id": "run1",
            "candidate_id": "c2",
            "candidate": "puno more",
            "model": "Ollama",
            "source_adapter": "ollama",
            "prompt_strategy": "strict_plain_list",
            "target_class": "N",
            "saturation_level": "70",
            "text_type": "sentence",
            "normalized_text": "puno more",
            "phonemes": "p u n o m o r e",
            "saturation_percentage": "37.5",
            "passes_saturation": "False",
            "is_valid": "False",
            "failure_reasons": "failed_saturation",
        },
    ]


def test_block_style_configs_load_and_plan():
    paper = load_config("experiments/paper_reproduction_config.yaml")
    task = load_config("experiments/task16_full_config.yaml")
    paper_plan = build_planned_requests(paper)
    task_plan = build_planned_requests(task)
    assert len(paper_plan) == 35
    assert len(task_plan) == 40
    assert {request.prompt_strategy for request in paper_plan} == {"paper_style"}
    assert {request.prompt_strategy for request in task_plan} == {"paper_style", "strict_plain_list"}


def test_manifest_creation(tmp_path):
    path = write_manifest("run", tmp_path, config_path="config.yaml", adapter="manual_csv")
    assert path.exists()
    assert "manual_csv" in path.read_text(encoding="utf-8")


def test_compare_runs_outputs(tmp_path):
    input_path = tmp_path / "all.csv"
    write_csv(input_path, candidate_rows())
    paths = compare_runs([input_path], tmp_path / "comparison")
    assert paths["comparison_summary"].exists()
    assert paths["failure_reason_summary"].exists()
    assert paths["phoneme_usage_comparison"].exists()
    assert paths["comparison_report"].exists()


def test_hjp_word_review_export_and_apply(tmp_path):
    input_path = tmp_path / "all.csv"
    review_path = tmp_path / "hjp.csv"
    output_path = tmp_path / "reviewed.csv"
    write_csv(input_path, candidate_rows())
    export_hjp_word_review(input_path, review_path)
    with review_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["hjp_valid"] = "yes" if row["word"] in {"panj", "puno"} else "no"
    write_csv(review_path, rows)
    apply_hjp_word_review(input_path, review_path, output_path)
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reviewed = list(csv.DictReader(handle))
    assert reviewed[0]["candidate_hjp_valid"] == "yes"
    assert reviewed[1]["candidate_hjp_valid"] == "no"
    assert "more" in reviewed[1]["hjp_invalid_words"]


def test_hunspell_command_and_mocked_word_status(monkeypatch):
    assert build_hunspell_command("hunspell", "hr_HR") == ["hunspell", "-d", "hr_HR", "-l"]
    monkeypatch.setattr("src.validators.shutil.which", lambda executable: f"/usr/bin/{executable}")

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        if cmd == ["hunspell", "-D"]:
            Result.stdout = "AVAILABLE DICTIONARIES:\nhr_HR\n"
        elif kwargs.get("input") == "krivo\n":
            Result.stdout = "krivo\n"
        return Result()

    monkeypatch.setattr("src.validators.subprocess.run", fake_run)
    dictionary = DictionaryValidator(mode="hunspell_cli")
    assert dictionary.check_candidate("čamac")["dictionary_word_validity"] == "yes"
    status = dictionary.check_candidate("krivo")
    assert status["dictionary_word_validity"] == "no"
    assert status["dictionary_invalid_words"] == "krivo"


def test_hunspell_candidate_status_for_word_and_sentence(monkeypatch):
    monkeypatch.setattr("src.validators.shutil.which", lambda executable: f"/usr/bin/{executable}")

    def fake_run(cmd, **kwargs):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        if cmd == ["hunspell", "-D"]:
            Result.stdout = "hr_HR\n"
        elif kwargs.get("input") == "more\n":
            Result.stdout = "more\n"
        return Result()

    monkeypatch.setattr("src.validators.subprocess.run", fake_run)
    dictionary = DictionaryValidator(mode="hunspell_cli")
    word = validate_candidate("panj", "N", 10, "word", dictionary=dictionary)
    sentence = validate_candidate("puno more sada", "N", 10, "sentence", dictionary=dictionary)
    assert word.dictionary_word_validity == "yes"
    assert sentence.dictionary_word_validity == "no"
    assert "more" in sentence.dictionary_invalid_words


def test_hunspell_missing_executable_and_dictionary(monkeypatch):
    monkeypatch.setattr("src.validators.shutil.which", lambda _executable: None)
    with pytest.raises(RuntimeError, match="Hunspell executable"):
        DictionaryValidator(mode="hunspell_cli")

    monkeypatch.setattr("src.validators.shutil.which", lambda executable: f"/usr/bin/{executable}")

    class Result:
        returncode = 0
        stdout = "en_US\n"
        stderr = ""

    monkeypatch.setattr("src.validators.subprocess.run", lambda *args, **kwargs: Result())
    with pytest.raises(RuntimeError, match="hr_HR"):
        DictionaryValidator(mode="hunspell_cli")


def test_hunspell_config_loads():
    config = load_config("experiments/hunspell_validation_config.yaml")
    assert config["validation"]["dictionary"]["mode"] == "hunspell_cli"
    assert config["validation"]["dictionary"]["hunspell_dictionary"] == "hr_HR"


def test_lexical_review_queue_priorities(tmp_path):
    input_path = tmp_path / "all.csv"
    output_path = tmp_path / "queue.csv"
    rows = candidate_rows()
    rows[0]["dictionary_backend"] = "hunspell_cli"
    rows[0]["dictionary_word_validity"] = "yes"
    rows[1]["dictionary_backend"] = "hunspell_cli"
    rows[1]["dictionary_word_validity"] = "no"
    rows[1]["dictionary_invalid_words"] = "more"
    rows[1]["failure_reasons"] = "dictionary_failed"
    write_csv(input_path, rows, fieldnames=list(rows[0]) + ["dictionary_backend", "dictionary_word_validity", "dictionary_invalid_words"])
    export_lexical_review_queue(input_path, output_path)
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        queue = {row["word"]: row for row in csv.DictReader(handle)}
    assert queue["panj"]["priority"] == "high"
    assert queue["panj"]["review_reason"] == "rare_phoneme_word"
    assert queue["more"]["priority"] == "high"
    assert "hunspell_invalid" in queue["more"]["review_reason"]


def test_espeak_command_and_croatian_voice(monkeypatch):
    assert build_espeak_command("espeak-ng", "panj", "out.wav") == [
        "espeak-ng",
        "-v",
        "hr",
        "-w",
        "out.wav",
        "panj",
    ]

    class Result:
        stdout = " 5  hr             M  hr              croatian\n"

    monkeypatch.setattr("src.tts.espeak_ng_available", lambda executable="espeak-ng": True)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())
    assert require_croatian_voice() == "hr"


def test_espeak_missing_croatian_voice(monkeypatch):
    class Result:
        stdout = " 5  en             M  en              english\n"

    monkeypatch.setattr("src.tts.espeak_ng_available", lambda executable="espeak-ng": True)
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: Result())
    with pytest.raises(RuntimeError, match="Croatian"):
        require_croatian_voice()


def create_wav(path):
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        frames = b"".join(struct.pack("<h", sample) for sample in [0, 1000, -1000, 0])
        handle.writeframes(frames)


def test_tts_manifest_writing_with_mocked_subprocess(tmp_path, monkeypatch):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    monkeypatch.setattr("src.tts.require_croatian_voice", lambda executable="espeak-ng": "hr")

    def fake_run(cmd, check, capture_output, text):
        create_wav(Path(cmd[4]))

    monkeypatch.setattr("subprocess.run", fake_run)
    manifest = synthesize_audio(input_path, "espeak_ng", tmp_path / "audio")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "success"
    assert rows[0]["tts_voice"] == "hr"


def test_tts_comparison_config_loads():
    config = load_config("experiments/tts_comparison_config.yaml")
    adapters = config["tts_comparison"]["adapters"]
    assert adapters[0]["name"] == "espeak_ng"
    assert adapters[0]["enabled"] is True
    assert config["audio"]["target_sample_rate"] == 16000


def test_tts_comparison_manifest_schema_and_mocked_espeak(tmp_path, monkeypatch):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    monkeypatch.setattr("src.tts.require_croatian_voice", lambda executable="espeak-ng": "hr")

    def fake_run(cmd, check, capture_output, text):
        create_wav(Path(cmd[cmd.index("-w") + 1]))

    monkeypatch.setattr("subprocess.run", fake_run)
    config = load_config("experiments/tts_comparison_config.yaml")
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "comparison", limit=1)
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        assert handle
    assert set(TTS_COMPARISON_MANIFEST_FIELDS).issuperset(rows[0].keys())
    assert rows[0]["tts_adapter"] == "espeak_ng"
    assert rows[0]["tts_model_or_voice"] == "hr"
    assert rows[0]["sample_rate"] == "16000"


def test_coqui_command_and_missing_cli(tmp_path):
    assert build_coqui_command("tts", "panj", "tts_models/hr/cv/vits", "raw.wav") == [
        "tts",
        "--text",
        "panj",
        "--model_name",
        "tts_models/hr/cv/vits",
        "--out_path",
        "raw.wav",
    ]
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "coqui_vits_hr",
                    "enabled": True,
                    "command": "definitely-missing-tts",
                    "model_name": "tts_models/hr/cv/vits",
                    "croatian_voice_or_model_confirmed": True,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "coqui")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "failed"
    assert "Coqui TTS CLI is missing" in rows[0]["error"]


def test_speecht5_missing_model_path_error(tmp_path):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_id": "nikolab/speecht5_tts_hr",
                    "model_path": "",
                    "local_files_only": True,
                    "croatian_voice_or_model_confirmed": True,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "failed"
    assert "model_path" in rows[0]["error"]


def test_speecht5_missing_vocoder_path_error(tmp_path):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    model_path = tmp_path / "model"
    model_path.mkdir()
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_path": str(model_path),
                    "vocoder_path": "",
                    "local_files_only": True,
                    "croatian_voice_or_model_confirmed": True,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5_vocoder")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "failed"
    assert "vocoder_path" in rows[0]["error"]


def test_speecht5_missing_dependencies_error(tmp_path, monkeypatch):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    model_path = tmp_path / "model"
    model_path.mkdir()
    vocoder_path = tmp_path / "vocoder"
    vocoder_path.mkdir()
    speaker_path = tmp_path / "speaker.npy"
    speaker_path.write_bytes(b"placeholder")
    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name in {"torch", "transformers", "soundfile", "numpy"}:
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_path": str(model_path),
                    "vocoder_path": str(vocoder_path),
                    "local_files_only": True,
                    "croatian_voice_or_model_confirmed": True,
                    "speaker_embedding_path": str(speaker_path),
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5_deps")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert "dependencies are missing" in rows[0]["error"]


def test_speecht5_requires_speaker_embedding_unless_fallback_enabled(tmp_path):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    model_path = tmp_path / "model"
    vocoder_path = tmp_path / "vocoder"
    model_path.mkdir()
    vocoder_path.mkdir()
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_path": str(model_path),
                    "vocoder_path": str(vocoder_path),
                    "local_files_only": True,
                    "croatian_voice_or_model_confirmed": True,
                    "allow_default_zero_speaker_embedding": False,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5_speaker")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "failed"
    assert "speaker_embedding_path" in rows[0]["error"]


def test_mocked_speecht5_synthesis_and_local_only(tmp_path, monkeypatch):
    import numpy as np

    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    model_path = tmp_path / "model"
    vocoder_path = tmp_path / "vocoder"
    model_path.mkdir()
    vocoder_path.mkdir()
    speaker_path = tmp_path / "speaker.npy"
    np.save(speaker_path, np.zeros((512,), dtype="float32"))
    calls = []

    class FakeTensor:
        def __init__(self, value=None):
            self.value = value

        def to(self, _device):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return np.array([0.0, 0.2, -0.2, 0.0], dtype="float32")

    class FakeTorch:
        @staticmethod
        def tensor(value):
            return FakeTensor(value)

    class FakeProcessor:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            calls.append(("processor", path, local_files_only))
            return cls()

        def __call__(self, text, return_tensors):
            return {"input_ids": FakeTensor(text)}

    class FakeModel:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            calls.append(("model", path, local_files_only))
            return cls()

        def to(self, _device):
            return self

        def generate_speech(self, input_ids, speaker_embeddings, vocoder):
            calls.append(("generate", speaker_embeddings.value.shape, vocoder.__class__.__name__))
            return FakeTensor()

    class FakeVocoder:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            calls.append(("vocoder", path, local_files_only))
            return cls()

        def to(self, _device):
            return self

    def fake_write(path, data, samplerate):
        create_wav(Path(path))

    monkeypatch.setitem(sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=fake_write))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            SpeechT5Processor=FakeProcessor,
            SpeechT5ForTextToSpeech=FakeModel,
            SpeechT5HifiGan=FakeVocoder,
        ),
    )
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_path": str(model_path),
                    "vocoder_path": str(vocoder_path),
                    "local_files_only": True,
                    "device": "cpu",
                    "croatian_voice_or_model_confirmed": True,
                    "speaker_embedding_path": str(speaker_path),
                    "speaker_embedding_dim": 512,
                    "allow_default_zero_speaker_embedding": False,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5_success")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "success"
    assert rows[0]["tts_adapter"] == "speecht5_hr"
    assert rows[0]["speaker_embedding_source"] == str(speaker_path)
    assert ("processor", str(model_path), True) in calls
    assert ("model", str(model_path), True) in calls
    assert ("vocoder", str(vocoder_path), True) in calls
    assert any(call[0] == "generate" and call[1] == (1, 512) for call in calls)


def test_speecht5_zero_fallback_records_manifest_source(tmp_path, monkeypatch):
    import numpy as np

    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    model_path = tmp_path / "model"
    vocoder_path = tmp_path / "vocoder"
    model_path.mkdir()
    vocoder_path.mkdir()

    class FakeTensor:
        def __init__(self, value=None):
            self.value = value

        def to(self, _device):
            return self

        def detach(self):
            return self

        def cpu(self):
            return self

        def numpy(self):
            return np.array([0.0, 0.1, 0.0], dtype="float32")

    class FakeTorch:
        @staticmethod
        def tensor(value):
            return FakeTensor(value)

    class FakeLoader:
        @classmethod
        def from_pretrained(cls, path, local_files_only):
            return cls()

        def to(self, _device):
            return self

        def __call__(self, text, return_tensors):
            return {"input_ids": FakeTensor(text)}

        def generate_speech(self, input_ids, speaker_embeddings, vocoder):
            return FakeTensor()

    monkeypatch.setitem(sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(sys.modules, "soundfile", types.SimpleNamespace(write=lambda path, data, samplerate: create_wav(Path(path))))
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        types.SimpleNamespace(
            SpeechT5Processor=FakeLoader,
            SpeechT5ForTextToSpeech=FakeLoader,
            SpeechT5HifiGan=FakeLoader,
        ),
    )
    config = {
        "tts_comparison": {
            "adapters": [
                {
                    "name": "speecht5_hr",
                    "enabled": True,
                    "model_path": str(model_path),
                    "vocoder_path": str(vocoder_path),
                    "local_files_only": True,
                    "device": "cpu",
                    "croatian_voice_or_model_confirmed": True,
                    "speaker_embedding_dim": 512,
                    "allow_default_zero_speaker_embedding": True,
                }
            ]
        },
        "audio": {"target_sample_rate": 16000, "target_channels": 1, "target_sample_width_bits": 16},
    }
    manifest = synthesize_audio_comparison(input_path, config, tmp_path / "speecht5_zero")
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["synthesis_status"] == "success"
    assert rows[0]["speaker_embedding_source"] == "default_zero_experimental"


def test_normalize_wav_resamples_tiny_wav(tmp_path):
    source = tmp_path / "source.wav"
    output = tmp_path / "normalized.wav"
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        frames = b"".join(struct.pack("<h", sample) for sample in [0, 0, 1000, 1000, -1000, -1000, 0, 0])
        handle.writeframes(frames)
    normalize_wav(source, output)
    with wave.open(str(output), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 16000


def test_tts_comparison_report_and_listening_sample(tmp_path):
    wav_path = tmp_path / "audio.wav"
    create_wav(wav_path)
    manifest = tmp_path / "tts_comparison_manifest.csv"
    row = {
        **candidate_rows()[0],
        "tts_adapter": "espeak_ng",
        "tts_model_or_voice": "hr",
        "croatian_voice_or_model_confirmed": "yes",
        "audio_path": str(wav_path),
        "sample_rate": "16000",
        "channels": "1",
        "sample_width_bits": "16",
        "duration_seconds": "0.1",
        "synthesis_status": "success",
        "error": "",
        "suitable_for_audio_eval": "yes",
    }
    write_csv(manifest, [row])
    paths = compare_tts_audio(manifest, tmp_path / "tts_report")
    assert paths["tts_audio_summary"].exists()
    with paths["tts_audio_summary"].open("r", encoding="utf-8", newline="") as handle:
        summary = list(csv.DictReader(handle))
    assert summary[0]["tts_adapter"] == "espeak_ng"
    sample_path = export_listening_review_sample(manifest, tmp_path / "listening.csv", per_adapter=1)
    with sample_path.open("r", encoding="utf-8", newline="") as handle:
        sample = list(csv.DictReader(handle))
    assert sample[0]["human_intelligibility_score"] == ""


def test_export_tts_candidate_subset_balances_groups_and_preserves_review_columns(tmp_path):
    input_path = tmp_path / "all_candidates.csv"
    output_path = tmp_path / "tts_subset.csv"
    rows = [
        {
            **candidate_rows()[0],
            "candidate_id": "n1",
            "normalized_text": "panj",
            "target_class": "N",
            "saturation_level": "50.0",
            "text_type": "word",
            "dictionary_word_validity": "yes",
            "candidate_hjp_valid": "yes",
            "hjp_review_complete": "yes",
        },
        {
            **candidate_rows()[0],
            "candidate_id": "n2",
            "candidate": "puna",
            "normalized_text": "puna",
            "target_class": "N",
            "saturation_level": "50.0",
            "text_type": "word",
            "dictionary_word_validity": "yes",
            "candidate_hjp_valid": "yes",
            "hjp_review_complete": "yes",
        },
        {
            **candidate_rows()[0],
            "candidate_id": "n3",
            "candidate": "panj",
            "normalized_text": "panj",
            "target_class": "N",
            "saturation_level": "50.0",
            "text_type": "word",
            "dictionary_word_validity": "yes",
            "candidate_hjp_valid": "yes",
            "hjp_review_complete": "yes",
            "failure_reasons": "duplicate",
        },
        {
            **candidate_rows()[0],
            "candidate_id": "s1",
            "candidate": "siva riba skače",
            "normalized_text": "siva riba skače",
            "target_class": "S",
            "saturation_level": "70.0",
            "text_type": "sentence",
            "dictionary_word_validity": "yes",
            "candidate_hjp_valid": "yes",
            "hjp_review_complete": "yes",
        },
    ]
    write_csv(input_path, rows)
    summary = export_tts_candidate_subset(input_path, output_path, per_group=2)
    assert summary["requested_groups"] == 2
    assert summary["filled_groups"] == 1
    assert summary["selected_candidates"] == 3
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        selected = list(csv.DictReader(handle))
    assert {row["normalized_text"] for row in selected} == {
        "panj",
        "puna",
        "siva riba skače",
    }
    assert "candidate_hjp_valid" in selected[0]


def test_external_command_tts_command_and_manifest(tmp_path, monkeypatch):
    assert build_external_tts_command("tts --out {output_path}", "panj", "x.wav", text_argument="--text {text}") == [
        "tts",
        "--out",
        "x.wav",
        "--text",
        "panj",
    ]
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])

    def fake_run(cmd, check, capture_output, text):
        create_wav(Path(cmd[cmd.index("--out") + 1]))

    monkeypatch.setattr("subprocess.run", fake_run)
    manifest = synthesize_audio(
        input_path,
        "external_command",
        tmp_path / "external_audio",
        tts_config={
            "external_command": {
                "command_template": "tts --out {output_path} --text {text}",
                "croatian_voice_or_model_confirmed": True,
            }
        },
    )
    with manifest.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["tts_adapter"] == "external_command"
    assert rows[0]["croatian_voice_or_model_confirmed"] == "yes"


def test_external_command_tts_requires_confirmation(tmp_path):
    input_path = tmp_path / "valid.csv"
    write_csv(input_path, [candidate_rows()[0]])
    with pytest.raises(RuntimeError, match="croatian_voice_or_model_confirmed"):
        synthesize_audio(
            input_path,
            "external_command",
            tmp_path / "audio",
            tts_config={"external_command": {"command_template": "tts {text} {output_path}"}},
        )


def test_wav_validation_and_text_normalization(tmp_path):
    wav_path = tmp_path / "x.wav"
    create_wav(wav_path)
    meta = wav_technical_validation(wav_path)
    assert meta["audio_readable"] is True
    assert meta["sample_rate"] == 16000
    assert normalize_audio_eval_text("Čuš, DŽEP!  ") == "čuš džep"


def test_audio_eval_with_mocked_asr_and_manual_fallback(tmp_path):
    wav_path = tmp_path / "x.wav"
    create_wav(wav_path)
    manifest = tmp_path / "audio_manifest.csv"
    write_csv(
        manifest,
        [
            {
                "run_id": "run",
                "candidate_id": "c1",
                "candidate": "Čuš džep",
                "normalized_text": "čuš džep",
                "audio_path": str(wav_path),
                "tts_adapter": "espeak_ng",
                "tts_model_or_voice": "hr",
                "target_class": "SV",
                "saturation_level": "70",
                "text_type": "sentence",
            }
        ],
    )
    paths = evaluate_audio(
        manifest,
        tmp_path / "eval",
        asr_adapter="faster_whisper",
        asr_model="mock",
        asr_transcriber=lambda _path: "čuš đep",
    )
    with paths["audio_eval_summary"].open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["normalized_asr_transcription"] == "čuš đep"
    assert rows[0]["tts_adapter"] == "espeak_ng"
    assert rows[0]["asr_model_name"] == "mock"
    assert paths["audio_eval_tts_summary"].exists()
    assert float(rows[0]["wer"]) > 0

    manual = tmp_path / "manual.csv"
    write_csv(manual, [{"candidate_id": "c1", "transcription": "čuš džep", "listener_notes": "ok"}])
    paths = evaluate_audio(manifest, tmp_path / "manual_eval", manual_transcriptions=manual)
    assert paths["audio_eval_report"].exists()


def test_missing_asr_adapter_message(tmp_path):
    manifest = tmp_path / "audio_manifest.csv"
    write_csv(manifest, [{"candidate_id": "c1", "audio_path": "missing.wav", "normalized_text": "panj"}])
    with pytest.raises(RuntimeError, match="model_path"):
        evaluate_audio(manifest, tmp_path / "eval", asr_adapter="faster_whisper")


def test_asr_profiles_load_and_resolve():
    config = load_config("experiments/tts_comparison_config.yaml")
    fast = config["audio_eval"]["asr_profiles"]["fast"]
    assert fast["adapter"] == "faster_whisper"
    assert fast["model_name"] == "large-v3-turbo"
    resolved = resolve_asr_profile("fast", None, "", config["audio_eval"])
    assert resolved["adapter"] == "faster_whisper"
    assert resolved["model_name"] == "large-v3-turbo"
    assert resolved["language"] == "hr"
    assert resolved["device"] == "cpu"
    assert resolved["compute_type"] == "int8"


def test_asr_profile_missing_model_path_clear_error(tmp_path):
    manifest = tmp_path / "audio_manifest.csv"
    write_csv(manifest, [{"candidate_id": "c1", "audio_path": "missing.wav", "normalized_text": "panj"}])
    config = load_config("experiments/tts_comparison_config.yaml")
    config["audio_eval"]["asr_profiles"]["fast"]["model_path"] = ""
    with pytest.raises(RuntimeError, match="local_files_only: true"):
        evaluate_audio(manifest, tmp_path / "eval", asr_profile="fast", asr_config=config["audio_eval"])


def test_audio_eval_profile_metadata_and_grouping(tmp_path):
    wav_path = tmp_path / "x.wav"
    create_wav(wav_path)
    manifest = tmp_path / "audio_manifest.csv"
    write_csv(
        manifest,
        [
            {
                "run_id": "run",
                "candidate_id": "c1",
                "candidate": "Čuš džep",
                "normalized_text": "čuš džep",
                "audio_path": str(wav_path),
                "tts_adapter": "coqui_vits_hr",
                "tts_model_or_voice": "tts_models/hr/cv/vits",
                "target_class": "SV",
                "saturation_level": "70",
                "text_type": "sentence",
            }
        ],
    )
    config = load_config("experiments/tts_comparison_config.yaml")
    config["audio_eval"]["asr_profiles"]["fast"]["model_path"] = str(tmp_path / "mock_model")
    paths = evaluate_audio(
        manifest,
        tmp_path / "profile_eval",
        asr_profile="fast",
        asr_config=config["audio_eval"],
        asr_transcriber=lambda _path: "čuš džep",
    )
    with paths["audio_eval_summary"].open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["asr_profile"] == "fast"
    assert rows[0]["asr_model_name"] == "large-v3-turbo"
    assert rows[0]["asr_model"] == "large-v3-turbo"
    assert rows[0]["asr_language"] == "hr"
    assert rows[0]["tts_adapter"] == "coqui_vits_hr"
    with paths["audio_eval_tts_summary"].open("r", encoding="utf-8", newline="") as handle:
        summary = list(csv.DictReader(handle))
    assert summary[0]["asr_profile"] == "fast"
    assert summary[0]["asr_model_name"] == "large-v3-turbo"
    assert summary[0]["tts_adapter"] == "coqui_vits_hr"


def test_faster_whisper_mocked_and_missing_dependency(tmp_path, monkeypatch):
    model_path = tmp_path / "model"
    model_path.mkdir()

    class Segment:
        text = " čuš džep "

    class FakeModel:
        def __init__(self, model_path, device, compute_type):
            self.model_path = model_path

        def transcribe(self, audio_path, language):
            return [Segment()], None

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    transcriber = FasterWhisperTranscriber(str(model_path), language="hr")
    assert transcriber.transcribe("audio.wav") == "čuš džep"

    monkeypatch.delitem(sys.modules, "faster_whisper")

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    original_import = __import__
    monkeypatch.setattr("builtins.__import__", fake_import)
    with pytest.raises(RuntimeError, match="faster-whisper is not installed"):
        FasterWhisperTranscriber(str(model_path))


def test_final_report_sections(tmp_path):
    output = build_final_report(None, None, tmp_path / "final.md")
    text = output.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert f"## {section}" in text
    assert "not yet evaluated" in text
    assert "Hunspell" in text


def test_final_report_mentions_asr_profile(tmp_path):
    audio_dir = tmp_path / "audio_eval"
    write_csv(
        audio_dir / "audio_eval_summary.csv",
        [
            {
                "asr_profile": "fast",
                "asr_model_name": "large-v3-turbo",
            }
        ],
    )
    output = build_final_report(None, audio_dir, tmp_path / "final_with_asr.md")
    text = output.read_text(encoding="utf-8")
    assert "ASR profile(s): fast" in text
    assert "large-v3-turbo" in text


def test_readme_hunspell_caveat():
    text = Path("README.md").read_text(encoding="utf-8")
    assert "Hunspell may reject valid inflected Croatian words" in text
    assert "not HJP validation" in text
    assert "ASR WER/CER is a proxy" in text
    assert "use one fixed ASR profile" in text


def test_no_openai_api_code_paths():
    checked = ["src/generators.py", "src/pipeline.py", "src/asr_eval.py", "src/audio_eval.py"]
    for path in checked:
        assert "openai" not in Path(path).read_text(encoding="utf-8").lower()
