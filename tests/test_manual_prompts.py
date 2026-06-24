from pathlib import Path


PROMPT_FILES = [
    Path("experiments/prompts/manual_word_generation_prompt.txt"),
    Path("experiments/prompts/manual_sentence_generation_prompt.txt"),
    Path("experiments/prompts/manual_repair_prompt.txt"),
]

REQUIRED_SNIPPETS = [
    "{target_class}",
    "{saturation_level}",
    "{candidate_count}",
    "Generate Croatian only",
    "Preserve Croatian letters: č, ć, đ, š, ž",
    "Avoid foreign words",
    "Avoid digits and symbols",
    "Output only a plain list, one candidate per line",
    "Do not explain",
    "Do not count phonemes in the answer",
    "Python validation will decide final acceptance",
    "N / Niski: m, n, nj, b, p, u",
    "SN / Srednjeniski: v, g, o, h, l, lj",
    "S / Srednji: a, k, r, d, dž, f, ž",
    "SV / Srednjevisoki: č, e, š, t, đ, j",
    "V / Visoki: ć, i, c, z, s",
    "The placeholder {target_class} refers to one of these Croatian phoneme classes",
]


def test_manual_prompt_files_contain_required_instructions():
    for path in PROMPT_FILES:
        assert path.exists()
        text = path.read_text(encoding="utf-8")
        for snippet in REQUIRED_SNIPPETS:
            assert snippet in text


def test_repair_prompt_contains_failed_candidates_placeholder():
    text = Path("experiments/prompts/manual_repair_prompt.txt").read_text(encoding="utf-8")
    assert "{failed_candidates}" in text
