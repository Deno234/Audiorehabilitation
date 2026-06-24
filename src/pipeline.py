"""End-to-end first-milestone pipeline."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
from typing import Any

from .audio_eval import evaluate_audio
from .comparison import compare_runs
from .final_report import build_final_report
from .generators import (
    build_planned_requests,
    export_chatgpt_prompts,
    generate_with_ollama,
    import_chatgpt_responses,
    load_manual_csv,
    save_generated_csv,
    save_raw_generation,
)
from .manifest import write_manifest
from .lexical_review import export_lexical_review_queue
from .manual_review import (
    apply_hjp_word_review,
    apply_manual_review,
    export_hjp_word_review,
    export_manual_review,
)
from .report import generate_reports, write_csv
from .tts import synthesize_audio, synthesize_audio_comparison
from .tts_comparison import compare_tts_audio, export_listening_review_sample
from .tts_subset import export_tts_candidate_subset
from .validators import DictionaryValidator, validate_candidates


def make_run_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_config(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except Exception as exc:
        raise RuntimeError("PyYAML is required to load experiments/config.yaml") from exc
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def snapshot_config(config_path: str | Path, output_dir: str | Path, run_id: str) -> Path:
    destination = Path(output_dir) / f"config_snapshot_{run_id}.yaml"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(config_path, destination)
    return destination


def run_pipeline(
    config_path: str | Path,
    adapter: str,
    input_path: str | Path | None = None,
    output_path: str | Path | None = None,
    dry_run: bool = False,
    export_chatgpt_prompts_flag: bool = False,
    import_chatgpt_responses_dir: str | Path | None = None,
    prompt_index_path: str | Path | None = None,
) -> dict[str, Any]:
    config = load_config(config_path)
    run_id = make_run_id()

    output_config = config.get("outputs", {})
    raw_dir = Path(output_config.get("raw_generations_dir", "outputs/raw_generations"))
    validated_dir = Path(output_config.get("validated_dir", "outputs/validated"))
    reports_dir = Path(output_config.get("reports_dir", "outputs/reports"))
    manifests_dir = Path(output_config.get("manifests_dir", "outputs/manifests"))

    if export_chatgpt_prompts_flag:
        export_root = output_config.get("chatgpt_prompts_dir", "outputs/chatgpt_prompts")
        export_result = export_chatgpt_prompts(config, run_id, export_root)
        manifest_path = write_manifest(
            run_id,
            manifests_dir,
            config_path=config_path,
            adapter="manual_chatgpt_plus",
            config=config,
            operation="export_chatgpt_prompts",
            output_reports={"prompt_index": export_result["index_path"]},
        )
        export_result["manifest_path"] = manifest_path
        return {"run_id": run_id, "chatgpt_prompt_export": export_result}

    if import_chatgpt_responses_dir is not None:
        if prompt_index_path is None:
            raise ValueError("--prompt-index is required with --import-chatgpt-responses.")
        if output_path is None:
            raise ValueError("--output is required with --import-chatgpt-responses.")
        import_summary = import_chatgpt_responses(
            import_chatgpt_responses_dir,
            prompt_index_path,
            output_path,
            run_id,
        )
        import_summary["manifest_path"] = write_manifest(
            import_summary["run_id"],
            manifests_dir,
            config_path=config_path,
            adapter="manual_chatgpt_plus",
            config=config,
            operation="import_chatgpt_responses",
            input_csvs=[str(prompt_index_path), str(import_chatgpt_responses_dir)],
            output_reports={"output_csv": import_summary["output_csv_path"]},
        )
        return {"run_id": run_id, "chatgpt_import_summary": import_summary}

    if dry_run:
        if adapter != "ollama":
            raise ValueError("--dry-run is currently supported for the ollama adapter.")
        planned_requests = build_planned_requests(config)
        return {"run_id": run_id, "dry_run": True, "planned_requests": planned_requests}

    generated_csv_path: Path | None = None
    if adapter == "manual_csv":
        if input_path is None:
            raise ValueError("--input is required when --adapter manual_csv.")
        generation_run = load_manual_csv(input_path, run_id)
        raw_path = save_raw_generation(
            generation_run,
            raw_dir,
            metadata={"config_path": str(config_path), "input_path": str(input_path)},
        )
    elif adapter == "ollama":
        if output_path is None:
            raise ValueError("--output is required when --adapter ollama unless --dry-run is used.")
        generation_run, raw_path = generate_with_ollama(config, run_id, raw_dir)
        for row in generation_run.rows:
            row["source_file"] = str(output_path)
        generated_csv_path = save_generated_csv(output_path, generation_run.rows)
    else:
        raise ValueError(f"Unsupported adapter: {adapter}")

    validation_config = config.get("validation", {})
    dictionary_config = validation_config.get("dictionary", {})
    dictionary = DictionaryValidator(
        mode=dictionary_config.get("mode", "none"),
        local_wordlist_path=dictionary_config.get("local_wordlist_path"),
        manual_review_csv_path=dictionary_config.get("manual_review_csv_path"),
        hunspell_executable=dictionary_config.get("hunspell_executable", "hunspell"),
        hunspell_dictionary=dictionary_config.get("hunspell_dictionary", "hr_HR"),
    )
    sentence_config = validation_config.get("sentence", {})
    validated_rows = validate_candidates(
        generation_run.rows,
        dictionary=dictionary,
        sentence_min_words=int(sentence_config.get("min_words", 3)),
        sentence_max_words=int(sentence_config.get("max_words", 5)),
    )

    validated_dir.mkdir(parents=True, exist_ok=True)
    validated_path = write_csv(
        validated_dir / f"validated_pipeline_rows_{run_id}.csv",
        validated_rows,
    )

    pcd_version = config.get("metrics", {}).get("pcd_version", "pcd_paper_style")
    report_paths = generate_reports(validated_rows, reports_dir, run_id, pcd_version)
    raw_config_snapshot = snapshot_config(config_path, raw_dir, run_id)
    report_config_snapshot = snapshot_config(config_path, reports_dir, run_id)
    manifest_path = write_manifest(
        run_id,
        manifests_dir,
        config_path=config_path,
        config_snapshot_path=report_config_snapshot,
        adapter=adapter,
        model=config.get("ollama", {}).get("model", "") if adapter == "ollama" else "",
        config=config,
        raw_generation_files=[str(raw_path)],
        input_csvs=[str(input_path)] if input_path else ([str(output_path)] if output_path else []),
        output_reports=report_paths,
    )

    return {
        "run_id": run_id,
        "raw_generation_path": raw_path,
        "generated_csv_path": generated_csv_path,
        "validated_path": validated_path,
        "report_paths": report_paths,
        "raw_config_snapshot": raw_config_snapshot,
        "report_config_snapshot": report_config_snapshot,
        "manifest_path": manifest_path,
        "validated_rows": validated_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the text/audio research pipeline.")
    parser.add_argument("--config", default="experiments/config.yaml", help="Path to experiments/config.yaml")
    parser.add_argument("--adapter", choices=["manual_csv", "ollama", "espeak_ng", "external_command"], help="Generation or TTS adapter")
    parser.add_argument("--input", help="Input file for manual_csv")
    parser.add_argument("--output", help="Generated CSV path for ollama")
    parser.add_argument("--output-dir", help="Output directory for comparison/audio/final operations")
    parser.add_argument("--prompt-index", help="Prompt index CSV for ChatGPT Plus response import")
    parser.add_argument("--inputs", nargs="+", help="Input candidate CSVs for comparison")
    parser.add_argument("--compare-runs", action="store_true", help="Compare already validated all_candidates CSVs")
    parser.add_argument("--export-hjp-word-review", action="store_true", help="Export unique words for HJP review")
    parser.add_argument("--apply-hjp-word-review", action="store_true", help="Apply word-level HJP review")
    parser.add_argument("--export-lexical-review-queue", action="store_true", help="Export prioritized lexical review queue")
    parser.add_argument("--word-review", help="HJP word review CSV")
    parser.add_argument("--export-manual-review", action="store_true", help="Export candidate-level semantic/clinical review CSV")
    parser.add_argument("--apply-manual-review", action="store_true", help="Apply candidate-level semantic/clinical review CSV")
    parser.add_argument("--review", help="Candidate-level review CSV")
    parser.add_argument("--synthesize-audio", action="store_true", help="Synthesize audio from validated candidates")
    parser.add_argument("--synthesize-audio-comparison", action="store_true", help="Synthesize validated candidates with every enabled TTS adapter")
    parser.add_argument("--compare-tts-audio", action="store_true", help="Summarize a TTS comparison manifest")
    parser.add_argument("--export-listening-review-sample", action="store_true", help="Export balanced human listening review sample")
    parser.add_argument("--export-tts-candidate-subset", action="store_true", help="Export a balanced candidate subset for TTS comparison")
    parser.add_argument("--limit", type=int, help="Limit audio synthesis rows")
    parser.add_argument("--per-adapter", type=int, default=10, help="Rows per TTS adapter for listening review sample")
    parser.add_argument("--per-group", type=int, default=5, help="Rows per class/saturation/text-type group for TTS subset export")
    parser.add_argument("--evaluate-audio", action="store_true", help="Evaluate audio manifest technically and optionally with ASR/manual transcription")
    parser.add_argument("--audio-manifest", help="Audio manifest CSV")
    parser.add_argument("--asr-adapter", help="Optional local ASR adapter name")
    parser.add_argument("--asr-profile", help="Named ASR profile from config audio_eval.asr_profiles")
    parser.add_argument("--manual-transcriptions", help="Optional manual transcription CSV")
    parser.add_argument("--build-final-report", action="store_true", help="Build final scientific report")
    parser.add_argument("--comparison-dir", help="Comparison directory for final report")
    parser.add_argument("--audio-eval-dir", help="Audio evaluation directory for final report")
    parser.add_argument(
        "--import-chatgpt-responses",
        help="Folder containing ChatGPT Plus response files named exactly like prompt files",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned Ollama requests without HTTP calls")
    parser.add_argument(
        "--export-chatgpt-prompts",
        action="store_true",
        help="Export manual ChatGPT Plus prompts from the experiment grid",
    )
    args = parser.parse_args()
    if args.compare_runs:
        paths = compare_runs(args.inputs or [], args.output_dir or "outputs/comparisons/comparison")
        print("comparison_outputs:")
        for key, value in paths.items():
            print(f"  {key}={value}")
        return
    if args.export_hjp_word_review:
        path = export_hjp_word_review(args.input, args.output)
        print(f"hjp_word_review={path}")
        return
    if args.apply_hjp_word_review:
        path = apply_hjp_word_review(args.input, args.word_review, args.output)
        print(f"hjp_reviewed_candidates={path}")
        return
    if args.export_lexical_review_queue:
        path = export_lexical_review_queue(args.input, args.output)
        print(f"lexical_review_queue={path}")
        return
    if args.export_manual_review:
        path = export_manual_review(args.input, args.output)
        print(f"manual_review={path}")
        return
    if args.apply_manual_review:
        path = apply_manual_review(args.input, args.review, args.output)
        print(f"manual_reviewed_candidates={path}")
        return
    if args.synthesize_audio:
        config = load_config(args.config)
        path = synthesize_audio(
            args.input,
            args.adapter or "espeak_ng",
            args.output_dir,
            args.limit,
            tts_config=config.get("tts", {}),
        )
        print(f"audio_manifest={path}")
        return
    if args.synthesize_audio_comparison:
        config = load_config(args.config)
        path = synthesize_audio_comparison(args.input, config, args.output_dir, args.limit)
        print(f"tts_comparison_manifest={path}")
        return
    if args.compare_tts_audio:
        paths = compare_tts_audio(args.audio_manifest, args.output_dir or args.output or "outputs/audio_comparison/report")
        print("tts_comparison_outputs:")
        for key, value in paths.items():
            print(f"  {key}={value}")
        return
    if args.export_listening_review_sample:
        path = export_listening_review_sample(args.audio_manifest, args.output, args.per_adapter)
        print(f"listening_review_sample={path}")
        return
    if args.export_tts_candidate_subset:
        summary = export_tts_candidate_subset(args.input, args.output, args.per_group)
        print("tts_candidate_subset:")
        print(f"  requested_groups={summary['requested_groups']}")
        print(f"  filled_groups={summary['filled_groups']}")
        print(f"  missing_or_underfilled_groups={len(summary['missing_or_underfilled_groups'])}")
        for group in summary["missing_or_underfilled_groups"]:
            print(
                "  underfilled="
                f"{group['target_class']},{group['saturation_level']},{group['text_type']} "
                f"selected={group['selected']} available={group['available']}"
            )
        print(f"  selected_candidates={summary['selected_candidates']}")
        print(f"  output_path={summary['output_path']}")
        return
    if args.evaluate_audio:
        config = load_config(args.config)
        paths = evaluate_audio(
            args.audio_manifest,
            args.output or args.output_dir or "outputs/audio_eval",
            asr_adapter=args.asr_adapter,
            asr_profile=args.asr_profile or "",
            asr_config=config.get("audio_eval", {}),
            manual_transcriptions=args.manual_transcriptions,
        )
        print("audio_eval_outputs:")
        for key, value in paths.items():
            print(f"  {key}={value}")
        return
    if args.build_final_report:
        path = build_final_report(args.comparison_dir, args.audio_eval_dir, args.output)
        print(f"final_report={path}")
        return

    if not args.export_chatgpt_prompts and not args.import_chatgpt_responses and not args.adapter:
        parser.error("--adapter is required unless exporting prompts or importing ChatGPT responses")

    result = run_pipeline(
        args.config,
        args.adapter or "manual_csv",
        args.input,
        args.output,
        args.dry_run,
        args.export_chatgpt_prompts,
        args.import_chatgpt_responses,
        args.prompt_index,
    )
    if result.get("chatgpt_prompt_export"):
        export = result["chatgpt_prompt_export"]
        print(f"run_id={result['run_id']}")
        print(f"chatgpt_prompt_dir={export['export_dir']}")
        print(f"prompt_index={export['index_path']}")
        print(f"responses_dir={export['responses_dir']}")
        print(f"prompt_count={len(export['rows'])}")
        return
    if result.get("chatgpt_import_summary"):
        summary = result["chatgpt_import_summary"]
        print(f"run_id={summary['run_id']}")
        print("chatgpt_import_summary:")
        print(f"  expected_response_files={summary['expected_response_files']}")
        print(f"  found_response_files={summary['found_response_files']}")
        print(f"  missing_response_files={summary['missing_response_files']}")
        print(f"  total_parsed_candidates={summary['total_parsed_candidates']}")
        print(f"  output_csv_path={summary['output_csv_path']}")
        for warning in summary["warnings"]:
            print(f"  warning={warning}")
        return
    if result.get("dry_run"):
        print(f"run_id={result['run_id']}")
        print("dry_run=True")
        print("planned_requests:")
        for index, planned in enumerate(result["planned_requests"], start=1):
            print(
                f"  {index}. adapter={planned.adapter} model={planned.model} "
                f"base_url={planned.base_url} target_class={planned.target_class} "
                f"saturation_level={planned.saturation_level:g} text_type={planned.text_type} "
                f"prompt_strategy={planned.prompt_strategy} "
                f"requested_count={planned.requested_count} selected_count={planned.selected_count}"
            )
        return

    print(f"run_id={result['run_id']}")
    print(f"raw_generation_path={result['raw_generation_path']}")
    if result.get("generated_csv_path"):
        print(f"generated_csv_path={result['generated_csv_path']}")
    print(f"validated_path={result['validated_path']}")
    print(f"manifest_path={result['manifest_path']}")
    print("reports:")
    for name, path in result["report_paths"].items():
        print(f"  {name}={path}")


if __name__ == "__main__":
    main()
