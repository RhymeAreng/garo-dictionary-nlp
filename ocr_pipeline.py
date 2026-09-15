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


if __name__ == "__main__":
    
    image = rasterize_page("./sources/dictionary-1905.pdf", page_number=100)
    #image.save("./scratch/test_dictionary1905_page_100.jpg")
    text = ocr_page_by_columns(image)
    with open("ocr_output_columns_1905p100.txt", "w", encoding="utf-8") as f:
            f.write(text)
    print(text)
        
        
  

    """
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