from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import re
from sqlalchemy.orm import Session
from models import Entry


# Part-of-speech tags, including combined forms seen in real entries
# (e.g. "Achranggia, Acharia, v. & adj. Half ripe (of fruits).").
POS_PATTERN = (
    r"(?:v\.\s*&\s*n\.|n\.\s*&\s*adj\.|v\.\s*&\s*adj\.|pr\.\s*&\s*adj\.|"
    r"n\.|v\.|adj\.|adv\.|pr\.|conj\.|interj\.|pron\.|prep\.)"
)

# Matches "Headword(s), pos." as the start of a dictionary entry.
#``
# The headword group starts with either a capital letter (normal entries)
# or a hyphen (grammatical suffix entries like "-ba"). Its character class
# includes the middle-dot stress mark (\u00b7), hyphens, apostrophes,
# parentheses (pronunciation notes like "(a-ba-ku)"), spaces (multi-word
# headwords), and commas. Commas are essential inside the headword group,
# not optional -- real entries list multiple spelling variants separated
# by commas before the POS tag (e.g. "A\u00b7ni, A\u00b7ani, adj."), and without
# allowing commas here the regex cannot "see past" the first variant to
# find the real comma-before-POS, silently mis-splitting the entry.
ENTRY_START = re.compile(
    r"(?P<headword>(?:[A-Z]|-)[A-Za-z\u00b7\-'(), ]*?),\s*"
    r"(?P<pos>" + POS_PATTERN + r")\s+"
)



def rasterize_page(pdf_path: str, page_number: int, dpi: int = 300):
    """
    Convert a single PDF page into an image.

    Uses a higher-than-default DPI (300) because OCR accuracy — especially
    for small details like apostrophe stress marks — improves noticeably
    with higher resolution source images.

    Args:
        pdf_path: path to the source PDF file.
        page_number: which page to convert (1-indexed, matching how PDF
            viewers display page numbers).
        dpi: resolution to render at. Higher values improve OCR accuracy
            at the cost of processing time and memory.

    Returns:
        A single PIL Image object representing the rendered page.
    """

    pages = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=page_number,
        last_page=page_number
    )
    return pages[0]


def ocr_raw(image):
    """
    Run Tesseract OCR on an image and return the raw extracted text,
    with no cleanup or structuring applied.

    This is intentionally the simplest possible OCR call — no column
    splitting, no confidence filtering — used here specifically to see
    Tesseract's default, naive behavior before improving on it in the
    coming days.

    Args:
        image: a PIL Image object (e.g. from rasterize_page()).

    Returns:
        The raw OCR'd text as a single string.
    """
    return pytesseract.image_to_string(image)


def split_columns(image: Image.Image, split_fraction: float = 0.5):
    """
    Split a two-column page image into separate left and right column images.

    Splitting into columns before OCR (rather than relying on Tesseract's
    automatic layout detection) guarantees correct reading order regardless
    of print quality — automatic detection can fail unpredictably on
    degraded scans, as seen with the 1905 dictionary source.

    Args:
        image: a PIL Image of the full page.
        split_fraction: where to divide the page width, as a fraction from
            the left edge (0.5 = exact middle). Adjust per source if a
            page's columns aren't evenly split.

    Returns:
        A tuple of (left_column_image, right_column_image).
    """
    width, height = image.size
    split_x = int(width * split_fraction)
    left = image.crop((0, 0, split_x, height))
    right = image.crop((split_x, 0, width, height))
    return left, right


def ocr_page_by_columns(image: Image.Image) -> str:
    """
    OCR a two-column page correctly by splitting it into columns first,
    then running OCR on each column independently and concatenating the
    results in reading order (left column fully, then right column).

    Args:
        image: a PIL Image of the full page.

    Returns:
        The combined OCR text, left column followed by right column.
    """
    left, right = split_columns(image)
    left_text = pytesseract.image_to_string(left)
    right_text = pytesseract.image_to_string(right)
    return left_text + "\n" + right_text


def ocr_with_confidence(image: Image.Image) -> list[dict]:
    """
    Run OCR on an image and return each recognized word alongside its
    confidence score, rather than just a plain text string.

    Tesseract's image_to_data() returns word-level bounding boxes and
    confidence scores, unlike image_to_string() which only returns text.
    This richer output is what allows flagging specific low-confidence
    words for manual review, instead of trusting the whole page equally.

    Args:
        image: a PIL Image to run OCR on.

    Returns:
        A list of dicts, each with keys "word" and "confidence" (0-100,
        or -1 for entries with no actual recognized text, which Tesseract
        includes for internal layout reasons and should be filtered out).
    """
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    results = []
    for i, word in enumerate(data["text"]):
        word = word.strip()
        if not word:
            continue
        confidence = int(data["conf"][i])
        results.append({"word": word, "confidence": confidence})

    return results


def has_apostrophe(word: str) -> bool:
    """
    Check whether a word contains any apostrophe-like character.

    Garo stress marks are apostrophes in the 1905 dictionary source. This
    check exists to flag any word touching one for manual review, since
    OCR frequently mangles or drops these marks (e.g. "Ma'gapa" misread as
    "Margapa"). Never used to strip or normalize apostrophes away.

    Args:
        word: a single OCR'd word.

    Returns:
        True if the word contains a straight or curly apostrophe.
    """
    return any(char in word for char in ["'", "\u2019", "\u2018"])




SUSPICIOUS_HYPHEN_PATTERN = re.compile(r"^[A-Za-z]{1,2}-[a-z]")

def has_suspicious_hyphen(word: str) -> bool:
    """
    Check whether a word matches the pattern of a likely misread middle-dot
    diacritic (e.g. "A-we", misread from "A·we").

    This is a separate, unrelated check from has_apostrophe() — confirmed
    directly that a genuine middle-dot-to-hyphen misread returns
    HIGH OCR confidence.
    The pattern specifically targets a short (1-2 letter) prefix immediately
    followed by a hyphen and a lowercase letter — matching the shape of a
    stress-marked syllable break, while trying to avoid over-flagging
    ordinary English hyphenated compounds (which are rarer in headword
    position and tend to have longer prefixes).

    Args:
        word: a single OCR'd word.

    Returns:
        True if the word matches the suspicious short-prefix-hyphen shape.
    """
    return bool(SUSPICIOUS_HYPHEN_PATTERN.match(word))



def flag_word_for_review(word: str, confidence: int, low_confidence_threshold: int = 75) -> dict | None:
    """
    Decide whether an OCR'd word needs manual review, and why.

    Combines three independent signals: low OCR confidence (genuine visual
    uncertainty), apostrophe presence (Garo stress marks, easily mangled),
    and the suspicious-hyphen pattern (a confirmed high-confidence misread
    of a different diacritic). A word can trigger more than one reason;
    all applicable reasons are returned so nothing gets silently dropped.

    Args:
        word: the OCR'd word text.
        confidence: Tesseract's reported confidence for this word (0-100).
        low_confidence_threshold: confidence below this value is flagged.

    Returns:
        None if the word needs no review, otherwise a dict with the word,
        its confidence, and a list of every triggered reason.
    """
    reasons = []

    if confidence != -1 and confidence < low_confidence_threshold:
        reasons.append("low_confidence")
    if has_apostrophe(word):
        reasons.append("apostrophe_present")
    if has_suspicious_hyphen(word):
        reasons.append("suspicious_hyphen_pattern")

    if not reasons:
        return None

    return {"word": word, "confidence": confidence, "reasons": reasons}


EMBEDDED_SENSE_MARKER = re.compile(r"[.\u2014]\s*(?:" + POS_PATTERN + r")")


def has_embedded_sense_marker(definition: str) -> bool:
    """
    Check whether a definition contains an embedded secondary sense marker,
    e.g. "Red-hot; glowing.\u2014n. A glow of fire...\u2014v. To throbe..." -- a single
    entry covering multiple parts of speech within one definition block.

    These are parsed as one entry (not split) for now, but flagged so a
    reviewer can decide during Phase 4 whether splitting into separate
    entries makes sense for a given case.

    Args:
        definition: the parsed definition text for one entry.

    Returns:
        True if an embedded sense marker (e.g. "\u2014n." or "\u2014v.") is found
        anywhere after the first sentence.
    """
    return bool(EMBEDDED_SENSE_MARKER.search(definition))


def clean_ocr_text(raw_text: str) -> str:
    """
    Join hard-wrapped OCR lines into flowing text, without touching
    apostrophes, middle dots, or other meaningful punctuation -- only
    collapses line-wrap artifacts introduced by column width.

    Args:
        raw_text: OCR output, possibly with mid-entry line breaks.

    Returns:
        The text with single line breaks collapsed into spaces.
    """
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", raw_text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def parse_entries(raw_text: str, source_page: int, source_file: str) -> list[dict]:
    """
    Parse cleaned OCR text into a list of structured dictionary entries.

    Each entry is flagged for review by default (needs_review=True), with
    specific reasons recorded: apostrophe presence, the suspicious-hyphen
    misread pattern (checked on the headword only, per Day 24's scoping
    decision), and embedded multi-sense markers within the definition.

    Known limitation: entries lacking a part-of-speech tag entirely (e.g.
    bare grammatical particles like "-a, Ending of a verb...") are not
    detected by this parser and will be silently absorbed into the
    preceding entry's definition. This is a deliberate tradeoff -- this
    category is narrow enough that catching it during manual review (Phase
    4) is more reliable than the regex complexity needed to detect it
    automatically without false-matching on ordinary definition text.

    Args:
        raw_text: raw OCR output for one page (or one column).
        source_page: the page number this text came from, for traceability.
        source_file: the source PDF filename, for traceability.

    Returns:
        A list of entry dicts, each with headword, part_of_speech,
        definition, needs_review, and review_reasons (a list, since an
        entry can trigger more than one flag simultaneously).
    """
    text = clean_ocr_text(raw_text)
    matches = list(ENTRY_START.finditer(text))
    entries = []

    for i, m in enumerate(matches):
        headword = m.group("headword").strip()
        pos = m.group("pos").strip()
        def_start = m.end()
        def_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        definition = text[def_start:def_end].strip()

        reasons = []
        if has_apostrophe(headword):
            reasons.append("apostrophe_present")
        if has_suspicious_hyphen(headword):
            reasons.append("suspicious_hyphen_pattern")
        if has_embedded_sense_marker(definition):
            reasons.append("multi_sense_entry")

        entries.append({
            "headword": headword,
            "part_of_speech": pos,
            "definition": definition,
            "source_file": source_file,
            "source_page": source_page,
            "needs_review": True,
            "review_reasons": reasons,
        })

    return entries



def reasons_to_string(reasons: list[str]) -> str | None:
    """
    Convert a list of review-flag reasons into a single storable string.

    The database schema stores review_reason as one TEXT column,
    while the parser produces a list since an entry can trigger multiple
    flags simultaneously. Joining with a semicolon keeps this readable and
    reversible (split on ";" to get the list back) without needing a schema
    change or a separate join table for what is, in practice, a small,
    fixed set of possible reasons.

    Args:
        reasons: list of reason strings, possibly empty.

    Returns:
        A semicolon-joined string, or None if the list is empty.
    """
    return "; ".join(reasons) if reasons else None



def process_page(pdf_path: str, page_number: int, source_file_label: str) -> list[dict]:
    """
    Run the full pipeline for a single page: rasterize, split columns, OCR
    each column, and parse into structured entry dicts.

    Args:
        pdf_path: path to the source PDF.
        page_number: which page to process (1-indexed).
        source_file_label: a short label to store in each entry's
            source_file field (e.g. "the-school.pdf"), for traceability.

    Returns:
        A list of entry dicts, as produced by parse_entries(), each still
        needing to be saved to the database.
    """
    image = rasterize_page(pdf_path, page_number)
    left, right = split_columns(image)
    text = pytesseract.image_to_string(left) + "\n" + pytesseract.image_to_string(right)
    return parse_entries(text, source_page=page_number, source_file=source_file_label)



def extract_leading_continuation(raw_text: str) -> tuple[str, str]:
    """
    Split raw OCR text into (leading continuation text, remaining text).

    If a page's OCR text starts with content before the first recognizable
    entry boundary, that leading text is very likely the tail end of the
    previous page's last entry, wrapped across the page/column break (the
    exact pattern first observed in the user's Image 5 sample). This
    function isolates that leading fragment so it can be appended to the
    correct previous entry rather than silently discarded or misparsed.

    Args:
        raw_text: raw OCR text for one page (already column-combined).

    Returns:
        A tuple of (leading_text, remaining_text). leading_text is an
        empty string if the page starts cleanly with a real entry.
    """
    cleaned = clean_ocr_text(raw_text)
    first_match = ENTRY_START.search(cleaned)
    if first_match is None or first_match.start() == 0:
        return "", cleaned
    return cleaned[:first_match.start()].strip(), cleaned[first_match.start():]




def process_and_save_page_range(
    pdf_path: str,
    start_page: int,
    end_page: int,
    source_file_label: str,
    db: Session
) -> int:
    """
    Process a sequential range of pages and save all entries to the
    database, correctly stitching cross-page continuation text onto the
    previous page's last entry rather than losing it or misparsing it as
    a new entry.

    Args:
        pdf_path: path to the source PDF.
        start_page: first page to process (inclusive, 1-indexed).
        end_page: last page to process (inclusive).
        source_file_label: label stored in each entry's source_file field.
        db: database session.

    Returns:
        The total number of entries saved.
    """
    last_saved_entry = None
    total_saved = 0

    for page_number in range(start_page, end_page + 1):
        image = rasterize_page(pdf_path, page_number)
        left, right = split_columns(image)
        raw_text = pytesseract.image_to_string(left) + "\n" + pytesseract.image_to_string(right)

        leading_text, remaining_text = extract_leading_continuation(raw_text)

        if leading_text and last_saved_entry is not None:
            last_saved_entry.definition += " " + leading_text
            existing_reasons = last_saved_entry.review_reason.split("; ") if last_saved_entry.review_reason else []
            existing_reasons.append("cross_page_continuation")
            last_saved_entry.review_reason = reasons_to_string(existing_reasons)
            db.commit()

        entries = parse_entries(remaining_text, source_page=page_number, source_file=source_file_label)

        for entry_dict in entries:
            db_entry = Entry(
                headword=entry_dict["headword"],
                part_of_speech=entry_dict["part_of_speech"],
                definition=entry_dict["definition"],
                direction="garo_to_english",
                source_file=entry_dict["source_file"],
                source_page=entry_dict["source_page"],
                needs_review=True,
                review_reason=reasons_to_string(entry_dict["review_reasons"]),
            )
            db.add(db_entry)
            db.commit()
            db.refresh(db_entry)
            last_saved_entry = db_entry
            total_saved += 1

    return total_saved




if __name__ == "__main__":
    from database import SessionLocal
    db = SessionLocal()
    count = process_and_save_page_range(
        "sources/the-school.pdf",
        start_page=47,
        end_page=48,
        source_file_label="the-school.pdf",
        db=db
    )
    print(f"Saved {count} entries.")
    db.close()



#Main instances to check later

"""

if __name__ == "__main__":
    image = rasterize_page("sources/the-school.pdf", page_number=48)
    text = ocr_page_by_columns(image)
    entries = parse_entries(text, source_page=48, source_file="the-school.pdf")
    for e in entries:
        print(f"{e['headword']:30} {e['part_of_speech']:10} reasons={e['review_reasons']}")






if __name__ == "__main__":
    image = rasterize_page("sources/the-school.pdf", page_number=20)
    left, right = split_columns(image)
    word_data = ocr_with_confidence(left)

    print("Words flagged for review:")
    for entry in word_data:
        flag = flag_word_for_review(entry["word"], entry["confidence"])
        if flag:
            print(f"  {flag['word']:20} confidence={flag['confidence']:>3}  reasons={flag['reasons']}")


#This is a bug --- Need to fix it.
#Test Score of confidence with a test page
if __name__ == "__main__":
    image = rasterize_page("sources/the-school.pdf", page_number=20)
    left, right = split_columns(image)
    word_data = ocr_with_confidence(left)

    for entry in word_data[:50]:
        if entry['word'] == "A-we,":
            print("word found")
        print(f"{entry['confidence']:>4}  {entry['word']}")

    #Sort by lowest confidence
    sorted_by_confidence = sorted(word_data, key=lambda x: x["confidence"])
    print("Lowest confidence words:")
    for entry in sorted_by_confidence[:15]:
        print(f"{entry['confidence']:>4}  {entry['word']}")



if __name__ == "__main__":
    
    image = rasterize_page("./sources/dictionary-1905.pdf", page_number=100)
    #image.save("./scratch/test_dictionary1905_page_100.jpg")
    text = ocr_page_by_columns(image)
    with open("ocr_output_columns_1905p100.txt", "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
        
        
    image = rasterize_page("./sources/the-school.pdf", page_number=20)
    image.save("./scratch/test_page_20.jpg")
    text = ocr_raw(image)
    text = ocr_page_by_columns(image)
    with open("ocr_output_columns.txt", "w", encoding="utf-8") as f:
           f.write(text)
    with open("ocr_output_naive.txt", "w", encoding="utf-8") as f:
       f.write(text)
    print(text)
    print(f"Saved image: {image.size[0]}x{image.size[1]} pixels")
    

"""