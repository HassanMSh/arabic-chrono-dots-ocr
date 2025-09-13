from pdf2image import convert_from_path
from PIL import Image
from pathlib import Path
from typing import Generator
from typing import Optional

def pdf_to_pages(
    pdf_path: str, 
    dpi: int = 300,
    from_page: int = 1,
    to_page: Optional[int] = None
    ) -> Generator[Image.Image, None, None]:
    """
    Convert a PDF into pages as PIL images.
    Yields one page at a time to enable streaming.
    """
    page_number = from_page
    while True:
        if to_page is not None and page_number > to_page:
            break
        
        try:
            pages = convert_from_path(
                pdf_path, dpi=dpi,
                first_page=page_number,
                last_page=page_number
            )
            if not pages:
                break
            yield pages[0]
            page_number += 1
        except Exception:
            break
        
def slice_page(page_img: Image.Image, order: str = "right_first"):
    """
    Slice a page into two halves and yield them in the desired order.
    """
    w, h = page_img.size
    left = page_img.crop((0, 0, w // 2, h))
    right = page_img.crop((w // 2, 0, w, h))

    if order == "right_first":
        yield right
        yield left
    else:
        yield left
        yield right


def pdf_to_slices(
    pdf_path: str,
    dpi: int = 300,
    order: str = "right_first",
    from_page: int = 1,
    to_page: Optional[int] = None
) -> Generator[Image.Image, None, None]:
    """
    Full pipeline: PDF -> pages -> slices.
    Yields slice images one at a time.
    Supports optional page range.
    """
    for page in pdf_to_pages(pdf_path, dpi=dpi, from_page=from_page, to_page=to_page):
        for half in slice_page(page, order=order):
            yield half