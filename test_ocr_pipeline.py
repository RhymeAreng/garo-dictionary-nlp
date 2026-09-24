from ocr_pipeline import has_apostrophe, has_suspicious_hyphen, flag_word_for_review
from ocr_pipeline import parse_entries
from ocr_pipeline import extract_leading_continuation, reasons_to_string


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


def test_parses_multi_variant_headword():
    """Confirm multiple comma-separated headword variants stay grouped as one entry."""
    text = "A\u00b7ni, A\u00b7ani, adj. Earthen; earthly; pertaining to the earth."
    entries = parse_entries(text, source_page=1, source_file="test.pdf")
    assert len(entries) == 1
    assert entries[0]["headword"] == "A\u00b7ni, A\u00b7ani"

def test_parses_combined_pos_tag():
    """Confirm combined POS tags like 'v. & adj.' are captured correctly."""
    text = "Achranggia, Acharia, v. & adj. Half ripe (of fruits)."
    entries = parse_entries(text, source_page=1, source_file="test.pdf")
    assert entries[0]["part_of_speech"] == "v. & adj."

def test_flags_embedded_sense_marker():
    """Confirm a multi-sense entry is flagged, but still parsed as one entry."""
    text = "Giila, adj. Red-hot; glowing.\u2014n. A glow of fire.\u2014v. To throbe with pain."
    entries = parse_entries(text, source_page=1, source_file="test.pdf")
    assert len(entries) == 1
    assert "multi_sense_entry" in entries[0]["review_reasons"]

def test_pronunciation_parenthetical_does_not_false_flag_hyphen():
    """Confirm a pronunciation guide's internal hyphens don't trigger a false flag."""
    text = "A\u00b7baku (a-ba-ku), n. The position in a jhum-land up to which weeding is done."
    entries = parse_entries(text, source_page=1, source_file="test.pdf")
    assert "suspicious_hyphen_pattern" not in entries[0]["review_reasons"]


def test_extract_leading_continuation_detects_orphaned_text():
    """Confirm leading text before the first entry match is correctly isolated."""
    text = "continues from before.\nDai, n. My elder brother's wife."
    leading, remaining = extract_leading_continuation(text)
    assert "continues from before" in leading
    assert remaining.startswith("Dai")

def test_extract_leading_continuation_empty_when_page_starts_clean():
    """Confirm a page starting directly with a valid entry has no leading text."""
    text = "Dai, n. My elder brother's wife."
    leading, remaining = extract_leading_continuation(text)
    assert leading == ""

def test_reasons_to_string_joins_and_handles_empty():
    """Confirm reason-list-to-string conversion works both ways."""
    assert reasons_to_string(["apostrophe_present", "multi_sense_entry"]) == "apostrophe_present; multi_sense_entry"
    assert reasons_to_string([]) is None