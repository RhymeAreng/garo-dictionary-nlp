from pdf2image import convert_from_path
import pytesseract
from PIL import Image

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

    """
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