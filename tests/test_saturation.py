from src.validators import calculate_saturation


def test_saturation_calculation_passes():
    result = calculate_saturation("panj", "N", 50)
    assert result.total_phonemes == 3
    assert result.target_count == 2
    assert round(result.saturation_percentage, 2) == 66.67
    assert result.passes_saturation is True


def test_saturation_calculation_fails():
    result = calculate_saturation("džep", "V", 50)
    assert result.total_phonemes == 3
    assert result.target_count == 0
    assert result.passes_saturation is False

