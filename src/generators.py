"""Generation adapters for candidate text."""

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
import re
from pathlib import Path
from datetime import datetime
from itertools import product
import time
from typing import Any
from urllib import error, request

from .phoneme_classes import normalize_class_name


REQUIRED_MANUAL_COLUMNS = {
    "candidate",
    "model",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
}

RESERVED_INPUT_COLUMNS = REQUIRED_MANUAL_COLUMNS | {
    "run_id",
    "candidate_id",
    "source_adapter",
    "source_file",
    "original_text",
    "normalized_text",
    "phonemes",
    "total_phonemes",
    "target_count",
    "saturation_percentage",
    "passes_saturation",
    "is_valid",
    "failure_reasons",
    "word_count",
    "dictionary_mode",
}

GENERATED_CSV_FIELDS = [
    "candidate",
    "model",
    "prompt_strategy",
    "target_class",
    "saturation_level",
    "text_type",
    "source_adapter",
    "run_id",
]

EXPLANATION_MARKERS = ("here are", "explanation", "napomena", "evo", "ovdje")
PROMPT_STRATEGIES = ("paper_style", "strict_plain_list")
PHONEME_CLASS_TABLE = """N / Niski: m, n, nj, b, p, u
SN / Srednjeniski: v, g, o, h, l, lj
S / Srednji: a, k, r, d, dž, f, ž
SV / Srednjevisoki: č, e, š, t, đ, j
V / Visoki: ć, i, c, z, s"""


@dataclass(frozen=True)
class GenerationRun:
    run_id: str
    adapter: str
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class OllamaSettings:
    model: str
    base_url: str = "http://localhost:11434"
    temperature: float = 0.8
    max_retries: int = 3
    request_timeout_seconds: int = 300


@dataclass(frozen=True)
class GenerationSettings:
    candidate_count_per_condition: int = 5
    request_extra_factor: int = 2
    sleep_seconds_between_requests: float = 1.0


@dataclass(frozen=True)
class ExperimentCondition:
    target_class: str
    saturation_level: float
    text_type: str
    prompt_strategy: str
    candidate_count_per_condition: int | None = None


@dataclass(frozen=True)
class PlannedRequest:
    adapter: str
    model: str
    base_url: str
    prompt_strategy: str
    target_class: str
    saturation_level: float
    text_type: str
    requested_count: int
    selected_count: int
    prompt: str


def load_manual_csv(path: str | Path, run_id: str) -> GenerationRun:
    """Load manually prepared candidate rows from a UTF-8 CSV file."""
    csv_path = Path(path)
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_MANUAL_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manual CSV is missing columns: {', '.join(sorted(missing))}")
        rows: list[dict[str, Any]] = []
        extra_columns = [
            column for column in (reader.fieldnames or []) if column not in RESERVED_INPUT_COLUMNS
        ]
        for index, row in enumerate(reader):
            candidate_row = {
                "run_id": run_id,
                "candidate_id": f"{run_id}_{index:05d}",
                "candidate": row["candidate"].strip(),
                "model": row["model"].strip() or "manual",
                "prompt_strategy": row["prompt_strategy"].strip() or "manual_csv",
                "target_class": normalize_class_name(row["target_class"]),
                "saturation_level": float(row["saturation_level"]),
                "text_type": row["text_type"].strip().lower(),
                "source_adapter": "manual_csv",
                "source_file": str(csv_path),
            }
            for column in extra_columns:
                candidate_row[column] = (row.get(column) or "").strip()
            rows.append(candidate_row)
    return GenerationRun(run_id=run_id, adapter="manual_csv", rows=rows)


def save_raw_generation(
    generation_run: GenerationRun,
    output_dir: str | Path,
    metadata: dict[str, Any] | None = None,
) -> Path:
    """Save raw generation rows and metadata as UTF-8 JSON."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    raw_path = output_path / f"raw_generations_{generation_run.run_id}.json"
    payload = {
        "run_id": generation_run.run_id,
        "adapter": generation_run.adapter,
        "metadata": metadata or {},
        "rows": generation_run.rows,
    }
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return raw_path


def generation_settings_from_config(config: dict[str, Any]) -> GenerationSettings:
    generation_config = config.get("generation", {})
    return GenerationSettings(
        candidate_count_per_condition=int(
            generation_config.get("candidate_count_per_condition", 5)
        ),
        request_extra_factor=int(generation_config.get("request_extra_factor", 2)),
        sleep_seconds_between_requests=float(
            generation_config.get("sleep_seconds_between_requests", 1)
        ),
    )


def ollama_settings_from_config(config: dict[str, Any]) -> OllamaSettings:
    ollama_config = config.get("ollama", {})
    model = str(ollama_config.get("model") or "").strip()
    if not model:
        raise ValueError("Ollama model is missing. Set ollama.model in experiments/config.yaml.")
    return OllamaSettings(
        model=model,
        base_url=str(ollama_config.get("base_url") or "http://localhost:11434").rstrip("/"),
        temperature=float(ollama_config.get("temperature", 0.8)),
        max_retries=int(ollama_config.get("max_retries", 3)),
        request_timeout_seconds=int(ollama_config.get("request_timeout_seconds", 300)),
    )


def experiment_conditions_from_config(config: dict[str, Any]) -> list[ExperimentCondition]:
    if config.get("experiment_blocks"):
        conditions: list[ExperimentCondition] = []
        for block in config["experiment_blocks"]:
            text_type = str(block["text_type"]).strip().lower()
            target_classes = block.get("target_classes", ["N", "SN", "S", "SV", "V"])
            saturation_levels = block.get("saturation_levels", [50, 70])
            prompt_strategies = block.get("prompt_strategies", ["paper_style"])
            count = int(
                block.get(
                    "candidate_count_per_condition",
                    config.get("generation", {}).get("candidate_count_per_condition", 5),
                )
            )
            for target_class, saturation_level, prompt_strategy in product(
                target_classes, saturation_levels, prompt_strategies
            ):
                conditions.append(
                    ExperimentCondition(
                        target_class=normalize_class_name(str(target_class)),
                        saturation_level=float(saturation_level),
                        text_type=text_type,
                        prompt_strategy=str(prompt_strategy).strip(),
                        candidate_count_per_condition=count,
                    )
                )
        for condition in conditions:
            if condition.text_type not in {"word", "sentence"}:
                raise ValueError(f"Unsupported text_type in experiment_blocks: {condition.text_type}")
            if condition.prompt_strategy not in PROMPT_STRATEGIES:
                raise ValueError(
                    f"Unsupported prompt_strategy in experiment_blocks: {condition.prompt_strategy}"
                )
        return conditions

    grid = config.get("experiment_grid", {})
    target_classes = grid.get("target_classes", ["N", "SN", "S", "SV", "V"])
    saturation_levels = grid.get("saturation_levels", [50, 70])
    text_types = grid.get("text_types", ["word", "sentence"])
    prompt_strategies = grid.get("prompt_strategies", list(PROMPT_STRATEGIES))
    conditions = [
        ExperimentCondition(
            target_class=normalize_class_name(str(target_class)),
            saturation_level=float(saturation_level),
            text_type=str(text_type).strip().lower(),
            prompt_strategy=str(prompt_strategy).strip(),
        )
        for target_class, saturation_level, text_type, prompt_strategy in product(
            target_classes, saturation_levels, text_types, prompt_strategies
        )
    ]
    for condition in conditions:
        if condition.text_type not in {"word", "sentence"}:
            raise ValueError(f"Unsupported text_type in experiment_grid: {condition.text_type}")
        if condition.prompt_strategy not in PROMPT_STRATEGIES:
            raise ValueError(
                f"Unsupported prompt_strategy in experiment_grid: {condition.prompt_strategy}"
            )
    return conditions


def _format_level(saturation_level: float) -> int | float:
    level = float(saturation_level)
    return int(level) if level.is_integer() else level


def _class_table_section(target_class: str) -> str:
    return (
        f"Oznaka {target_class} odnosi se na jednu od ovih klasa fonema:\n"
        f"{PHONEME_CLASS_TABLE}"
    )


def build_prompt(
    prompt_strategy: str,
    text_type: str,
    target_class: str,
    saturation_level: float,
    candidate_count: int,
) -> str:
    canonical_class = normalize_class_name(target_class)
    normalized_text_type = text_type.strip().lower()
    if prompt_strategy == "paper_style":
        if normalized_text_type == "word":
            body = (
                "Odaberi i napiši {candidate_count} postojećih riječi iz hrvatskog standardnog jezika "
                "koje sadrže minimalno {saturation_level}% fonema koji pripadaju klasi {target_class}, "
                "a preostali fonemi mogu biti iz drugih klasa fonema.\n\n"
                "Svaka riječ mora biti iz hrvatskog standardnog jezika. Provjeri, ako imaš pristup mreži, "
                "postoji li svaka riječ na mrežnoj stranici https://hjp.znanje.hr/.\n\n"
                "{class_table}\n\n"
                "Vrati samo popis riječi, jednu riječ po retku, bez objašnjenja."
            )
        elif normalized_text_type == "sentence":
            body = (
                "Napiši {candidate_count} rečenica od 3 do 5 riječi koje sadrže minimalno "
                "{saturation_level}% fonema koji pripadaju klasi {target_class}, a preostali fonemi "
                "mogu biti iz drugih klasa fonema.\n\n"
                "Rečenice moraju poštivati pravila hrvatskog standardnog jezika. Sve korištene riječi "
                "moraju postojati na mrežnoj stranici https://hjp.znanje.hr/, ako imaš pristup provjeri.\n\n"
                "{class_table}\n\n"
                "Vrati samo popis rečenica, jednu rečenicu po retku, bez objašnjenja."
            )
        else:
            raise ValueError(f"Unsupported text_type: {text_type}")
    elif prompt_strategy == "strict_plain_list":
        if normalized_text_type == "word":
            intro = "Generate {candidate_count} Croatian words for auditory rehabilitation research."
        elif normalized_text_type == "sentence":
            intro = (
                "Generate {candidate_count} Croatian sentences for auditory rehabilitation research.\n\n"
                "Each sentence must contain 3 to 5 words."
            )
        else:
            raise ValueError(f"Unsupported text_type: {text_type}")
        body = (
            f"{intro}\n\n"
            "Target phoneme class: {target_class}\n"
            "Required target-class saturation level: at least {saturation_level}%\n\n"
            "The selected target class refers to one of these Croatian phoneme classes:\n"
            f"{PHONEME_CLASS_TABLE}\n\n"
            "Rules:\n"
            "- Generate Croatian only.\n"
            "- Preserve Croatian letters: č, ć, đ, š, ž.\n"
            "- Avoid foreign words.\n"
            "- Avoid digits and symbols.\n"
            "- Output only a plain list, one candidate per line.\n"
            "- Do not number the lines.\n"
            "- Do not explain.\n"
            "- Do not count phonemes in the answer.\n"
            "- Python validation will decide final acceptance."
        )
    else:
        raise ValueError(f"Unsupported prompt_strategy: {prompt_strategy}")

    return body.format(
        candidate_count=candidate_count,
        saturation_level=_format_level(saturation_level),
        target_class=canonical_class,
        class_table=_class_table_section(canonical_class),
    )


def build_ollama_prompt(condition: ExperimentCondition, requested_count: int) -> str:
    return build_prompt(
        condition.prompt_strategy,
        condition.text_type,
        condition.target_class,
        condition.saturation_level,
        requested_count,
    )


def chatgpt_prompt_filename(condition: ExperimentCondition) -> str:
    return (
        f"chatgpt_{condition.prompt_strategy}_{condition.text_type}_"
        f"{condition.target_class}_{_format_level(condition.saturation_level)}.txt"
    )


def export_chatgpt_prompts(
    config: dict[str, Any],
    run_id: str,
    output_root: str | Path = "outputs/chatgpt_prompts",
) -> dict[str, Any]:
    generation_settings = generation_settings_from_config(config)
    export_dir = Path(output_root) / run_id
    export_dir.mkdir(parents=True, exist_ok=True)
    responses_dir = export_dir / "responses"
    responses_dir.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, Any]] = []
    for condition in experiment_conditions_from_config(config):
        candidate_count = (
            condition.candidate_count_per_condition
            or generation_settings.candidate_count_per_condition
        )
        prompt = build_prompt(
            condition.prompt_strategy,
            condition.text_type,
            condition.target_class,
            condition.saturation_level,
            candidate_count,
        )
        prompt_path = export_dir / chatgpt_prompt_filename(condition)
        prompt_path.write_text(prompt + "\n", encoding="utf-8")
        index_rows.append(
            {
                "prompt_file": prompt_path.name,
                "prompt_strategy": condition.prompt_strategy,
                "text_type": condition.text_type,
                "target_class": condition.target_class,
                "saturation_level": _format_level(condition.saturation_level),
                "candidate_count": candidate_count,
            }
        )
    index_path = export_dir / "prompt_index.csv"
    with index_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "prompt_file",
                "prompt_strategy",
                "text_type",
                "target_class",
                "saturation_level",
                "candidate_count",
            ],
        )
        writer.writeheader()
        writer.writerows(index_rows)
    return {
        "run_id": run_id,
        "export_dir": export_dir,
        "responses_dir": responses_dir,
        "index_path": index_path,
        "rows": index_rows,
    }


def _run_id_from_prompt_index(prompt_index_path: Path, fallback_run_id: str) -> str:
    parent = prompt_index_path.parent
    if parent.name:
        return parent.name
    return fallback_run_id


def import_chatgpt_responses(
    responses_dir: str | Path,
    prompt_index_path: str | Path,
    output_path: str | Path,
    fallback_run_id: str,
) -> dict[str, Any]:
    responses_path = Path(responses_dir)
    index_path = Path(prompt_index_path)
    output_csv_path = Path(output_path)
    import_run_id = _run_id_from_prompt_index(index_path, fallback_run_id)
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    expected_files: list[str] = []
    found_files: list[str] = []
    missing_files: list[str] = []

    with index_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index_row in reader:
            prompt_file = index_row["prompt_file"]
            expected_files.append(prompt_file)
            response_path = responses_path / prompt_file
            expected_count = int(float(index_row.get("candidate_count") or 0))
            if not response_path.exists():
                missing_files.append(prompt_file)
                warnings.append(f"Missing response file: {response_path}")
                continue
            found_files.append(prompt_file)
            raw_response = response_path.read_text(encoding="utf-8")
            if not raw_response.strip():
                warnings.append(f"Empty response file: {response_path}")
                continue
            parsed_candidates = parse_llm_candidate_lines(raw_response)
            if len(parsed_candidates) < expected_count:
                warnings.append(
                    f"Response file {response_path} yielded {len(parsed_candidates)} "
                    f"candidates; expected at least {expected_count}."
                )
            for candidate in parsed_candidates:
                rows.append(
                    {
                        "candidate": candidate,
                        "model": "ChatGPT Plus",
                        "prompt_strategy": index_row["prompt_strategy"],
                        "target_class": normalize_class_name(index_row["target_class"]),
                        "saturation_level": index_row["saturation_level"],
                        "text_type": index_row["text_type"],
                        "source_adapter": "manual_chatgpt_plus",
                        "run_id": import_run_id,
                    }
                )

    save_generated_csv(output_csv_path, rows)
    return {
        "run_id": import_run_id,
        "expected_response_files": len(expected_files),
        "found_response_files": len(found_files),
        "missing_response_files": len(missing_files),
        "missing_files": missing_files,
        "total_parsed_candidates": len(rows),
        "output_csv_path": output_csv_path,
        "warnings": warnings,
    }


def prompt_template_path(text_type: str) -> Path:
    if text_type == "word":
        return Path("experiments/prompts/manual_word_generation_prompt.txt")
    if text_type == "sentence":
        return Path("experiments/prompts/manual_sentence_generation_prompt.txt")
    raise ValueError(f"Unsupported text_type: {text_type}")


def build_planned_requests(config: dict[str, Any]) -> list[PlannedRequest]:
    generation_settings = generation_settings_from_config(config)
    ollama_settings = ollama_settings_from_config(config)
    requested_count = (
        generation_settings.candidate_count_per_condition
        * generation_settings.request_extra_factor
    )
    planned: list[PlannedRequest] = []
    for condition in experiment_conditions_from_config(config):
        selected_count = (
            condition.candidate_count_per_condition
            or generation_settings.candidate_count_per_condition
        )
        requested_count = selected_count * generation_settings.request_extra_factor
        planned.append(PlannedRequest(
            adapter="ollama",
            model=ollama_settings.model,
            base_url=ollama_settings.base_url,
            prompt_strategy=condition.prompt_strategy,
            target_class=condition.target_class,
            saturation_level=condition.saturation_level,
            text_type=condition.text_type,
            requested_count=requested_count,
            selected_count=selected_count,
            prompt=build_ollama_prompt(condition, requested_count),
        ))
    return planned


def parse_llm_candidate_lines(raw_text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^\s*(?:[-*•]+|\d+[\.)])\s*", "", line).strip()
        line = line.strip("\"'“”„”")
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            continue
        lowered = line.lower()
        if any(marker in lowered for marker in EXPLANATION_MARKERS):
            continue
        candidates.append(line)
    return candidates


def first_unique_candidates(candidates: list[str], limit: int) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        selected.append(candidate)
        if len(selected) >= limit:
            break
    return selected


def _json_request(
    url: str,
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
    http_request = request.Request(url, data=data, headers=headers, method=method)
    with request.urlopen(http_request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_ollama_model_available(settings: OllamaSettings) -> None:
    try:
        payload = _json_request(
            f"{settings.base_url}/api/tags",
            timeout_seconds=settings.request_timeout_seconds,
        )
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Ollama is not reachable at {settings.base_url}. Start Ollama and try again."
        ) from exc
    models = {model.get("name") for model in payload.get("models", [])}
    if settings.model not in models:
        available = ", ".join(sorted(model for model in models if model)) or "none"
        raise RuntimeError(
            f"Ollama model {settings.model!r} is not available. "
            f"Run `ollama pull {settings.model}`. Available models: {available}"
        )


def call_ollama(settings: OllamaSettings, prompt: str) -> str:
    payload = {
        "model": settings.model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": settings.temperature},
    }
    try:
        response_payload = _json_request(
            f"{settings.base_url}/api/generate",
            payload,
            timeout_seconds=settings.request_timeout_seconds,
        )
    except (error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Ollama generation failed because {settings.base_url} is unreachable."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned invalid JSON.") from exc
    if "error" in response_payload:
        raise RuntimeError(f"Ollama generation failed: {response_payload['error']}")
    return str(response_payload.get("response", ""))


def append_ollama_raw_record(path: str | Path, record: dict[str, Any]) -> None:
    jsonl_path = Path(path)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("a", encoding="utf-8", newline="") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_generated_csv(path: str | Path, rows: list[dict[str, Any]]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=GENERATED_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def generate_with_ollama(
    config: dict[str, Any],
    run_id: str,
    raw_dir: str | Path,
) -> tuple[GenerationRun, Path]:
    settings = ollama_settings_from_config(config)
    generation_settings = generation_settings_from_config(config)
    planned_requests = build_planned_requests(config)
    raw_path = Path(raw_dir) / f"raw_ollama_generations_{run_id}.jsonl"
    ensure_ollama_model_available(settings)

    rows: list[dict[str, Any]] = []
    candidate_index = 0
    for request_index, planned in enumerate(planned_requests):
        error_message = ""
        raw_response = ""
        parsed_candidates: list[str] = []
        selected_candidates: list[str] = []
        for attempt in range(1, settings.max_retries + 1):
            try:
                raw_response = call_ollama(settings, planned.prompt)
                parsed_candidates = parse_llm_candidate_lines(raw_response)
                selected_candidates = first_unique_candidates(
                    parsed_candidates, planned.selected_count
                )
                error_message = ""
                break
            except RuntimeError as exc:
                error_message = str(exc)
                if attempt >= settings.max_retries:
                    break
        record = {
            "run_id": run_id,
            "adapter": "ollama",
            "model": settings.model,
            "base_url": settings.base_url,
            "target_class": planned.target_class,
            "saturation_level": planned.saturation_level,
            "text_type": planned.text_type,
            "prompt_strategy": planned.prompt_strategy,
            "prompt": planned.prompt,
            "raw_response": raw_response,
            "parsed_candidates": parsed_candidates,
            "selected_candidates": selected_candidates,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "error": error_message,
        }
        append_ollama_raw_record(raw_path, record)
        if error_message:
            raise RuntimeError(error_message)
        for candidate in selected_candidates:
            rows.append(
                {
                    "run_id": run_id,
                    "candidate_id": f"{run_id}_{candidate_index:05d}",
                    "candidate": candidate,
                    "model": settings.model,
                    "prompt_strategy": planned.prompt_strategy,
                    "target_class": planned.target_class,
                    "saturation_level": planned.saturation_level,
                    "text_type": planned.text_type,
                    "source_adapter": "ollama",
                }
            )
            candidate_index += 1
        if request_index < len(planned_requests) - 1:
            time.sleep(generation_settings.sleep_seconds_between_requests)

    return GenerationRun(run_id=run_id, adapter="ollama", rows=rows), raw_path
