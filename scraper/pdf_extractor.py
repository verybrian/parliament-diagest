import io
import logging
import requests
from pdf2image import convert_from_bytes
import pytesseract

log = logging.getLogger(__name__)

SKIP_PAGES = 2
MAX_CONTENT_PAGES = 8
TESSERACT_CONFIG = "--psm 1 -l eng"
RASTERIZE_DPI = 300
DOWNLOAD_TIMEOUT = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://parliament.go.ke/",
}


def download_pdf(url: str) -> bytes:
    log.info("Downloading: %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=DOWNLOAD_TIMEOUT)
    resp.raise_for_status()
    size_kb = len(resp.content) / 1024
    if size_kb < 10:
        raise ValueError(f"Downloaded file is only {size_kb:.1f} KB.")
    log.info("Downloaded %.1f KB", size_kb)
    return resp.content


def ocr_page(image, page_num: int) -> str:
    log.info("OCR page %d...", page_num)
    text = pytesseract.image_to_string(image, config=TESSERACT_CONFIG).strip()
    return f"[Page {page_num}]\n{text}" if text else ""


def ocr_pdf(pdf_bytes: bytes, skip: int = SKIP_PAGES, max_pages: int = MAX_CONTENT_PAGES) -> dict:
    log.info("Rasterizing PDF at %d DPI...", RASTERIZE_DPI)
    images = convert_from_bytes(pdf_bytes, dpi=RASTERIZE_DPI)
    total_pages = len(images)
    log.info("PDF has %d page(s)", total_pages)

    content_images = images[skip: skip + max_pages]
    if not content_images:
        raise ValueError(f"PDF only has {total_pages} page(s); nothing left after skipping {skip}.")

    pages_text = []
    for i, img in enumerate(content_images, start=skip + 1):
        ocrd = ocr_page(img, i)
        if ocrd:
            pages_text.append(ocrd)
        else:
            log.warning("Page %d returned empty OCR output — may be blank or unreadable", i)

    if not pages_text:
        raise ValueError("OCR returned no text. The PDF may be too low quality or Tesseract is not installed.")

    last_page_idx = total_pages - 1
    content_window_end = skip + max_pages - 1
    last_page_text = ""

    if last_page_idx > content_window_end:
        log.info("Last page (%d) is outside content window — OCR'ing for endorser/date", total_pages)
        last_page_text = ocr_page(images[last_page_idx], total_pages)
        if last_page_text:
            pages_text.append(f"[Last page — endorser/date]\n{last_page_text.split(chr(10), 1)[-1]}")
    else:
        last_page_text = pages_text[-1]
        log.info("Last page already within content window — no extra OCR needed")

    pages_read = len(content_images) + (1 if last_page_idx > content_window_end else 0)
    log.info("OCR complete: %d page(s) read, ~%d characters extracted", pages_read, sum(len(t) for t in pages_text))

    return {
        "text": "\n\n".join(pages_text),
        "page_count": total_pages,
        "pages_read": pages_read,
        "skipped": skip,
        "last_page": last_page_text,
    }


def extract(url: str) -> dict:
    pdf_bytes = download_pdf(url)
    result = ocr_pdf(pdf_bytes)
    result["url"] = url
    return result