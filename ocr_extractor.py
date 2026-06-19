"""OCR and invoice-field extraction helpers.

This module keeps OCR and parsing separate so the parser can be tested without
running EasyOCR every time.
"""

from __future__ import annotations

import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

import easyocr
from pdf2image import convert_from_path


def _first_match(patterns: list[str], text: str, default: str = "UNKNOWN") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip(" :-\t")
    return default


def _parse_amount(value: str) -> float:
    cleaned = value.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_invoice_text(text: str) -> dict[str, Any]:
    """Parse structured invoice fields from OCR text."""
    compact_text = " ".join(text.split())

    invoice_id = _first_match(
        [
            r"(?:invoice|inv|bill)\s*(?:number|no\.?|#|id)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{2,})",
            r"\b([A-Z]{2,5}-\d{4}-\d{2,6})\b",
        ],
        compact_text,
    )

    customer_name = _first_match(
        [
            r"(?:billed\s*to|bill\s*to|customer|client)\s*:?\s*([A-Za-z0-9&.,'()\- ]{2,80}?)(?=\s+(?:invoice|inv|bill|date|due|total|amount|balance)\b|$)",
            r"(?:to)\s*:?\s*([A-Za-z0-9&.,'()\- ]{2,80}?)(?=\s+(?:invoice|date|due|total|amount|balance)\b|$)",
        ],
        compact_text,
    )

    amount_raw = _first_match(
        [
            r"(?:total\s*amount\s*due|amount\s*due|balance\s*due|total|balance|amount)\s*:?\s*(?:[$₹]|USD|INR)?\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
            r"(?:[$₹]|USD|INR)\s*([0-9][0-9,]*(?:\.\d{1,2})?)",
        ],
        compact_text,
        default="0",
    )
    amount_due = _parse_amount(amount_raw)

    due_date = _first_match(
        [
            r"due\s*date\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
            r"due\s*date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"payment\s*due\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})",
        ],
        compact_text,
    )

    return {
        "invoice_id": invoice_id,
        "customer_name": customer_name,
        "amount_due": amount_due,
        "due_date": due_date,
    }


@lru_cache(maxsize=1)
def get_reader() -> easyocr.Reader:
    """Create the EasyOCR reader once; model loading is expensive."""
    return easyocr.Reader(["en"], gpu=False)


def extract_text_from_pdf(pdf_path: str | os.PathLike[str]) -> str:
    """Convert the first page of a PDF to an image and return OCR text."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"Invoice file not found: {path}")

    try:
        images = convert_from_path(str(path), first_page=1, last_page=1)
    except Exception as exc:
        raise RuntimeError(
            "PDF-to-image conversion failed. Install Poppler and ensure it is on PATH."
        ) from exc

    if not images:
        raise ValueError(f"Could not convert any pages from {path}")

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        temp_img_path = Path(tmp.name)

    try:
        images[0].save(temp_img_path, "JPEG")
        lines = get_reader().readtext(str(temp_img_path), detail=0, paragraph=False)
    finally:
        temp_img_path.unlink(missing_ok=True)

    return "\n".join(str(line) for line in lines)


def extract_invoice_data(pdf_path: str | os.PathLike[str]) -> dict[str, Any]:
    """Run OCR on an invoice PDF and parse invoice fields."""
    text = extract_text_from_pdf(pdf_path)
    extracted = parse_invoice_text(text)

    print("\n--- Raw OCR Extracted Text ---")
    print(text)
    print("------------------------------")
    print("\n--- Extracted Structured Fields ---")
    for key, value in extracted.items():
        print(f"{key}: {value}")
    print("-----------------------------------\n")

    return extracted


if __name__ == "__main__":
    test_pdf = Path("invoice_sample.pdf")
    if test_pdf.exists():
        extract_invoice_data(test_pdf)
    else:
        print(f"Place an invoice PDF named {test_pdf!s} in this folder to test OCR.")
