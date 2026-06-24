from src.metrics import (
    duplicate_rate,
    pcd_paper_style,
    pcd_vector_style,
    phoneme_class_distribution,
    phoneme_frequency,
    unique_candidate_rate,
)


ROWS = [
    {"normalized_text": "panj", "phonemes": "p a nj"},
    {"normalized_text": "panj", "phonemes": "p a nj"},
    {"normalized_text": "džep", "phonemes": "dž e p"},
]


def test_unique_and_duplicate_rates():
    assert unique_candidate_rate(ROWS) == 2 / 3
    assert round(duplicate_rate(ROWS), 4) == round(1 / 3, 4)


def test_phoneme_frequency():
    counts = phoneme_frequency(ROWS)
    assert counts["p"] == 3
    assert counts["nj"] == 2
    assert counts["dž"] == 1


def test_phoneme_class_distribution():
    distribution = phoneme_class_distribution(ROWS)
    assert distribution["N"] == 5
    assert distribution["S"] == 3
    assert distribution["SV"] == 1


def test_pcd_paper_style():
    assert pcd_paper_style(["p", "a", "nj"], ["p", "a", "nj"]) == 0.0
    assert round(pcd_paper_style(["p", "a", "nj"], ["dž", "e", "p"]), 4) == round(2 / 3, 4)


def test_pcd_vector_style():
    assert pcd_vector_style(["p", "a", "nj"], ["p", "a", "nj"]) == 0.0
    assert 0.0 < pcd_vector_style(["p", "a", "nj"], ["dž", "e", "p"]) <= 1.0

