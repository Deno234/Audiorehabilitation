import csv
from pathlib import Path
from urllib import error

import pytest

from src import generators
from src.generators import (
    ExperimentCondition,
    OllamaSettings,
    build_prompt,
    build_ollama_prompt,
    build_planned_requests,
    ensure_ollama_model_available,
    export_chatgpt_prompts,
    import_chatgpt_responses,
    parse_llm_candidate_lines,
    save_generated_csv,
)
from src.pipeline import run_pipeline


def small_config(tmp_path):
    return {
        "generation": {
            "candidate_count_per_condition": 5,
            "request_extra_factor": 2,
            "sleep_seconds_between_requests": 1,
        },
        "ollama": {
            "model": "llama3.1:8b",
            "base_url": "http://localhost:11434",
            "temperature": 0.8,
            "max_retries": 3,
        },
        "experiment_grid": {
            "target_classes": ["N"],
            "saturation_levels": [50],
            "text_types": ["word", "sentence"],
            "prompt_strategies": ["paper_style", "strict_plain_list"],
        },
        "outputs": {
            "raw_generations_dir": str(tmp_path / "raw"),
            "validated_dir": str(tmp_path / "validated"),
            "reports_dir": str(tmp_path / "reports"),
        },
    }


def write_config(tmp_path, config_text):
    path = tmp_path / "config.yaml"
    path.write_text(config_text, encoding="utf-8")
    return path


def test_build_ollama_prompt_fills_placeholders():
    prompt = build_ollama_prompt(ExperimentCondition("N", 50, "word", "strict_plain_list"), 10)
    assert "{target_class}" not in prompt
    assert "{saturation_level}" not in prompt
    assert "{candidate_count}" not in prompt
    assert "Generate 10 Croatian words" in prompt
    assert "Target phoneme class: N" in prompt
    assert "Required target-class saturation level: at least 50%" in prompt
    assert "N / Niski: m, n, nj, b, p, u" in prompt


def test_paper_style_prompt_contains_hjp_and_class_table():
    prompt = build_prompt("paper_style", "word", "SV", 70, 5)
    assert "https://hjp.znanje.hr/" in prompt
    assert "Odaberi i napiši 5 postojećih riječi" in prompt
    assert "minimalno 70% fonema" in prompt
    assert "klasi SV" in prompt
    assert "SV / Srednjevisoki: č, e, š, t, đ, j" in prompt
    assert "{target_class}" not in prompt
    assert "{saturation_level}" not in prompt
    assert "{candidate_count}" not in prompt


def test_paper_style_sentence_prompt_contains_hjp():
    prompt = build_prompt("paper_style", "sentence", "N", 50, 5)
    assert "Napiši 5 rečenica od 3 do 5 riječi" in prompt
    assert "https://hjp.znanje.hr/" in prompt
    assert "N / Niski: m, n, nj, b, p, u" in prompt


def test_strict_plain_list_prompt_contains_rules_and_class_table():
    prompt = build_prompt("strict_plain_list", "sentence", "V", 50, 5)
    assert "Generate Croatian only" in prompt
    assert "Preserve Croatian letters: č, ć, đ, š, ž" in prompt
    assert "Avoid foreign words" in prompt
    assert "Avoid digits and symbols" in prompt
    assert "Do not count phonemes" in prompt
    assert "Python validation will decide final acceptance" in prompt
    assert "V / Visoki: ć, i, c, z, s" in prompt
    assert "{target_class}" not in prompt


def test_parse_llm_candidate_lines_cleans_common_formats():
    raw = """
    Here are candidates:
    1. "panj"
    2) puna
    - puno banana
    * "džep"
    Napomena: provjerite ručno
    Ovdje je objašnjenje

    sit zec s ceste
    """
    assert parse_llm_candidate_lines(raw) == [
        "panj",
        "puna",
        "puno banana",
        "džep",
        "sit zec s ceste",
    ]


def test_dry_run_builds_requests_without_http(tmp_path, monkeypatch):
    def fail_http(*_args, **_kwargs):
        raise AssertionError("dry-run must not call Ollama")

    monkeypatch.setattr(generators, "_json_request", fail_http)
    config_path = write_config(
        tmp_path,
        """
generation:
  candidate_count_per_condition: 5
  request_extra_factor: 2
  sleep_seconds_between_requests: 1
ollama:
  model: llama3.1:8b
  base_url: http://localhost:11434
  temperature: 0.8
  max_retries: 3
experiment_grid:
  target_classes: [N]
  saturation_levels: [50]
  text_types: [word, sentence]
  prompt_strategies: [paper_style, strict_plain_list]
outputs:
  raw_generations_dir: {raw}
  validated_dir: {validated}
  reports_dir: {reports}
""".format(
            raw=tmp_path / "raw",
            validated=tmp_path / "validated",
            reports=tmp_path / "reports",
        ),
    )

    result = run_pipeline(config_path, "ollama", dry_run=True)
    assert result["dry_run"] is True
    assert len(result["planned_requests"]) == 4
    assert result["planned_requests"][0].requested_count == 10
    assert result["planned_requests"][0].selected_count == 5
    assert {request.prompt_strategy for request in result["planned_requests"]} == {
        "paper_style",
        "strict_plain_list",
    }


def test_generated_csv_schema(tmp_path):
    output_path = tmp_path / "generated.csv"
    save_generated_csv(
        output_path,
        [
            {
                "candidate": "panj",
                "model": "llama3.1:8b",
                "prompt_strategy": "ollama_manual_prompt_template",
                "target_class": "N",
                "saturation_level": 50,
                "text_type": "word",
                "source_adapter": "ollama",
                "run_id": "run",
                "candidate_id": "ignored_in_generated_csv",
            }
        ],
    )
    with output_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert reader.fieldnames == [
        "candidate",
        "model",
        "prompt_strategy",
        "target_class",
        "saturation_level",
        "text_type",
        "source_adapter",
        "run_id",
    ]
    assert rows[0]["candidate"] == "panj"


def test_unreachable_ollama_error_is_clear(monkeypatch):
    def unreachable(*_args, **_kwargs):
        raise error.URLError("connection refused")

    monkeypatch.setattr(generators, "_json_request", unreachable)
    with pytest.raises(RuntimeError, match="Ollama is not reachable"):
        ensure_ollama_model_available(OllamaSettings(model="llama3.1:8b"))


def test_unavailable_model_error_is_clear(monkeypatch):
    monkeypatch.setattr(
        generators,
        "_json_request",
        lambda *_args, **_kwargs: {"models": [{"name": "mistral"}]},
    )
    with pytest.raises(RuntimeError, match="is not available"):
        ensure_ollama_model_available(OllamaSettings(model="llama3.1:8b"))


def test_build_planned_requests_uses_config_counts(tmp_path):
    planned = build_planned_requests(small_config(tmp_path))
    assert len(planned) == 4
    assert all(request.requested_count == 10 for request in planned)
    assert {request.text_type for request in planned} == {"word", "sentence"}
    assert {request.prompt_strategy for request in planned} == {
        "paper_style",
        "strict_plain_list",
    }


def test_chatgpt_prompt_export_creates_files_and_index(tmp_path):
    result = export_chatgpt_prompts(small_config(tmp_path), "run", tmp_path / "exports")
    export_dir = result["export_dir"]
    responses_dir = result["responses_dir"]
    index_path = result["index_path"]
    assert export_dir.exists()
    assert responses_dir.exists()
    assert index_path.exists()
    assert len(result["rows"]) == 4
    example_path = export_dir / "chatgpt_paper_style_word_N_50.txt"
    assert example_path.exists()
    assert "https://hjp.znanje.hr/" in example_path.read_text(encoding="utf-8")
    with index_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0].keys() == {
        "prompt_file",
        "prompt_strategy",
        "text_type",
        "target_class",
        "saturation_level",
        "candidate_count",
    }


def test_default_config_dry_run_plans_40_requests():
    result = run_pipeline("experiments/config.yaml", "ollama", dry_run=True)
    assert len(result["planned_requests"]) == 40


def test_generation_code_does_not_use_openai_api():
    assert "openai" not in Path("src/generators.py").read_text(encoding="utf-8").lower()
    assert "openai" not in Path("src/pipeline.py").read_text(encoding="utf-8").lower()


def test_import_chatgpt_responses_parses_exact_matching_files(tmp_path):
    export = export_chatgpt_prompts(small_config(tmp_path), "run123", tmp_path / "exports")
    responses_dir = export["responses_dir"]
    response_path = responses_dir / "chatgpt_paper_style_word_N_50.txt"
    response_path.write_text(
        '1. "panj"\n- puna\n* "puno banana"\nHere are notes\n',
        encoding="utf-8",
    )
    output_path = tmp_path / "chatgpt.csv"

    summary = import_chatgpt_responses(
        responses_dir,
        export["index_path"],
        output_path,
        "fallback",
    )

    assert summary["run_id"] == "run123"
    assert summary["expected_response_files"] == 4
    assert summary["found_response_files"] == 1
    assert summary["missing_response_files"] == 3
    assert summary["total_parsed_candidates"] == 3
    assert summary["output_csv_path"] == output_path
    assert any("Missing response file" in warning for warning in summary["warnings"])
    assert any("yielded 3 candidates" in warning for warning in summary["warnings"])

    with output_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0] == {
        "candidate": "panj",
        "model": "ChatGPT Plus",
        "prompt_strategy": "paper_style",
        "target_class": "N",
        "saturation_level": "50",
        "text_type": "word",
        "source_adapter": "manual_chatgpt_plus",
        "run_id": "run123",
    }
    assert [row["candidate"] for row in rows] == ["panj", "puna", "puno banana"]


def test_import_chatgpt_responses_warns_on_empty_file(tmp_path):
    export = export_chatgpt_prompts(small_config(tmp_path), "run123", tmp_path / "exports")
    responses_dir = export["responses_dir"]
    (responses_dir / "chatgpt_paper_style_word_N_50.txt").write_text("", encoding="utf-8")

    summary = import_chatgpt_responses(
        responses_dir,
        export["index_path"],
        tmp_path / "chatgpt.csv",
        "fallback",
    )

    assert summary["found_response_files"] == 1
    assert summary["total_parsed_candidates"] == 0
    assert any("Empty response file" in warning for warning in summary["warnings"])
