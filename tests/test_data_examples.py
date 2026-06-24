import csv
from pathlib import Path


def test_extended_manual_example_shape():
    path = Path("data/manual_candidates_extended_example.csv")
    assert path.exists()

    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) >= 50
    assert set(rows[0]) >= {
        "candidate",
        "model",
        "prompt_strategy",
        "target_class",
        "saturation_level",
        "text_type",
        "notes",
    }
    assert {row["text_type"] for row in rows} >= {"word", "sentence"}
    assert {"N", "SN", "S", "SV", "V"} <= {row["target_class"] for row in rows}
    assert {"40", "50", "60", "70", "80"} <= {row["saturation_level"] for row in rows}
    assert {
        "demo_valid_candidate",
        "demo_duplicate",
        "demo_wrong_word_count",
        "demo_foreign_letters",
        "demo_digits",
        "demo_repeated_words",
        "demo_failed_saturation",
    } <= {row["notes"] for row in rows}
