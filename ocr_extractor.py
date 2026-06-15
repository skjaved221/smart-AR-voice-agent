import easyocr
from pdf2image import convert_from_path
import re
import os

def extract_invoice_data(pdf_path):
    """
    Converts a PDF invoice to an image, runs OCR to extract text,
    and parses out key invoice fields using regular expressions.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Invoice file not found: {pdf_path}")

    print(f"[{pdf_path}] Converting PDF to image...")
    # Convert first page of PDF to an image (requires Poppler installed and on System PATH)
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1)
        if not images:
            raise ValueError("Could not convert PDF to image.")
        
        # Save temp image locally
        temp_img_path = "temp_invoice_page.jpg"
        images[0].save(temp_img_path, "JPEG")
    except Exception as e:
        print("\n[ERROR] PDF-to-Image conversion failed.")
        print("Please ensure Poppler is installed and added to your System PATH variables.")
        print("See README.md for installation instructions.\n")
        raise e

    print("Running OCR extraction...")
    # Initialize EasyOCR reader (downloads model files on first run, ~30MB)
    reader = easyocr.Reader(['en'], gpu=False)  # Run on CPU for compatibility
    result = reader.readtext(temp_img_path, detail=0)
    full_text = " ".join(result)

    # Clean up temp image
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)

    print("\n--- Raw OCR Extracted Text ---")
    print(full_text)
    print("------------------------------\n")

    # Parsing fields using regex
    # Target 1: Invoice ID (e.g., Invoice: INV-2026-001, Inv # 1234)
    inv_match = re.search(r"(?:Invoice|Inv|Bill)\s*#?\s*([A-Za-z0-9-]+)", full_text, re.IGNORECASE)
    invoice_id = inv_match.group(1) if inv_match else "UNKNOWN"

    # Target 2: Customer Name (Look for standard business tags or name prefixes)
    # This is a naive heuristic but works well for clean, standard invoices
    cust_match = re.search(r"Billed\s*To\s*:?\s*([^,.\n\t]+)", full_text, re.IGNORECASE)
    customer_name = cust_match.group(1).strip() if cust_match else "UNKNOWN"

    # Target 3: Amount Due (Look for currency symbols followed by decimals)
    amount_match = re.search(r"(?:Total|Due|Balance|Amount)\s*(?:Due|Owed)?\s*:?\s*[\$₹]?\s*([0-9,]+\.[0-9]{2})", full_text, re.IGNORECASE)
    amount_due = 0.0
    if amount_match:
        try:
            amount_due = float(amount_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Target 4: Due Date
    due_match = re.search(r"Due\s*Date\s*:?\s*([A-Za-z0-9\s,/-]+)", full_text, re.IGNORECASE)
    due_date = due_match.group(1).strip() if due_match else "UNKNOWN"

    extracted = {
        "invoice_id": invoice_id,
        "customer_name": customer_name,
        "amount_due": amount_due,
        "due_date": due_date
    }

    print("--- Extracted Structured Fields ---")
    for k, v in extracted.items():
        print(f"{k}: {v}")
    print("-----------------------------------\n")

    return extracted

if __name__ == "__main__":
    # Test OCR locally if a test PDF is present
    test_pdf = "invoice_sample.pdf"
    if os.path.exists(test_pdf):
        extract_invoice_data(test_pdf)
    else:
        print(f"To test OCR, place an invoice PDF named '{test_pdf}' in this folder and run this script.")
