from pdf2image import convert_from_path


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


if __name__ == "__main__":
    image = rasterize_page("./sources/the-school.pdf", page_number=20)
    image.save("./scratch/test_page_20.jpg")
    print(f"Saved image: {image.size[0]}x{image.size[1]} pixels")