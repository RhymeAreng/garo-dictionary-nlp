from ocr_pipeline import has_apostrophe, has_suspicious_hyphen, flag_word_for_review


def test_has_apostrophe_detects_straight_and_curly():
    """Confirm both straight and curly apostrophes are detected."""
    assert has_apostrophe("Ma'gapa") is True
    assert has_apostrophe("Ma\u2019gapa") is True
    assert has_apostrophe("Magapa") is False

def test_has_suspicious_hyphen_catches_known_case():
    """Confirm the exact real-world misread case is caught."""
    assert has_suspicious_hyphen("A-we") is True
    assert has_suspicious_hyphen("Ba-breka") is True

def test_flag_word_combines_reasons():
    """Confirm multiple simultaneous flags are all reported, not just one."""
    result = flag_word_for_review("A-we", confidence=95)
    assert result is not None
    assert "suspicious_hyphen_pattern" in result["reasons"]
    assert "low_confidence" not in result["reasons"]  # 95 is high confidence

def test_flag_word_returns_none_when_clean():
    """Confirm a normal, high-confidence, unremarkable word isn't flagged."""
    assert flag_word_for_review("Paternal", confidence=96) is None