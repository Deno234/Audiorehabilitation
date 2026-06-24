import csv

from src.metrics import candidate_summary
from src.pipeline import run_pipeline


def test_pipeline_generates_utf8_reports(tmp_path):
    config = tmp_path / "config.yaml"
    input_csv = tmp_path / "manual.csv"
    config.write_text(
        """
validation:
  dictionary:
    mode: none
  sentence:
    min_words: 3
    max_words: 5
metrics:
  pcd_version: pcd_paper_style
outputs:
  raw_generations_dir: {raw}
  validated_dir: {validated}
  reports_dir: {reports}
""".format(
            raw=tmp_path / "raw",
            validated=tmp_path / "validated",
            reports=tmp_path / "reports",
        ),
        encoding="utf-8",
    )
    input_csv.write_text(
        "candidate,model,prompt_strategy,target_class,saturation_level,text_type\n"
        "panj,manual,test,N,50,word\n"
        "džep,manual,test,S,50,word\n",
        encoding="utf-8",
    )

    result = run_pipeline(config, "manual_csv", input_csv)
    all_candidates = result["report_paths"]["all_candidates"]
    assert result["run_id"] in all_candidates.name
    assert all_candidates.exists()

    with all_candidates.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["run_id"] == result["run_id"]
    assert "failure_reasons" in rows[0]
    assert rows[1]["candidate"] == "džep"


def test_notes_are_preserved_but_do_not_decide_validity(tmp_path):
    config = tmp_path / "config.yaml"
    input_csv = tmp_path / "manual.csv"
    config.write_text(
        """
validation:
  dictionary:
    mode: none
  sentence:
    min_words: 3
    max_words: 5
metrics:
  pcd_version: pcd_paper_style
outputs:
  raw_generations_dir: {raw}
  validated_dir: {validated}
  reports_dir: {reports}
""".format(
            raw=tmp_path / "raw",
            validated=tmp_path / "validated",
            reports=tmp_path / "reports",
        ),
        encoding="utf-8",
    )
    input_csv.write_text(
        "candidate,model,prompt_strategy,target_class,saturation_level,text_type,notes\n"
        "panj,manual,test,N,50,word,demo_failed_saturation\n",
        encoding="utf-8",
    )

    result = run_pipeline(config, "manual_csv", input_csv)
    all_candidates = result["report_paths"]["all_candidates"]
    markdown_report = result["report_paths"]["markdown_report"]

    with all_candidates.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["notes"] == "demo_failed_saturation"
    assert rows[0]["is_valid"] == "True"
    assert "How to interpret results" in markdown_report.read_text(encoding="utf-8")


def test_summary_groups_by_prompt_strategy():
    rows = [
        {
            "run_id": "run",
            "model": "manual",
            "prompt_strategy": "baseline_prompt",
            "target_class": "N",
            "saturation_level": 50.0,
            "text_type": "word",
            "normalized_text": "panj",
            "phonemes": "p a nj",
            "is_valid": True,
            "passes_saturation": True,
            "saturation_percentage": 66.67,
            "failure_reasons": "",
        },
        {
            "run_id": "run",
            "model": "manual",
            "prompt_strategy": "few_shot_prompt",
            "target_class": "N",
            "saturation_level": 50.0,
            "text_type": "word",
            "normalized_text": "puna",
            "phonemes": "p u n a",
            "is_valid": True,
            "passes_saturation": True,
            "saturation_percentage": 75.0,
            "failure_reasons": "",
        },
    ]

    summaries = candidate_summary(rows, "pcd_paper_style")
    assert {row["prompt_strategy"] for row in summaries} == {
        "baseline_prompt",
        "few_shot_prompt",
    }
    assert len(summaries) == 2
