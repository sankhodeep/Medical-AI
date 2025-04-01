import pytesseract
from PIL import Image
import io
import re
from datetime import datetime
from typing import Union
import logging
from models import PrescriptionData

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Set the path to the Tesseract executable if it's not in your PATH
# Example for Linux/macOS (if installed via package manager): often not needed
# Example for Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# If running in a container or specific environment, ensure Tesseract is installed and accessible.
# You might need to install language packs as well (e.g., `sudo apt-get install tesseract-ocr-eng`)

# --- Helper Functions for Extraction ---

def extract_field(text: str, keywords: list[str], pattern: str = r":\s*(.*)") -> Union[str, None]:
    """Generic function to find a keyword and extract the value after it."""
    for keyword in keywords:
        # Case-insensitive search for the keyword
        match = re.search(f"{keyword}{pattern}", text, re.IGNORECASE)
        if match:
            # Clean up the extracted value
            value = match.group(1).strip()
            # Remove potential trailing keywords from the same line
            value = re.split(r'\s{2,}|[A-Z][a-z]+:', value)[0].strip()
            if value:
                return value
    return None

def extract_date(text: str) -> Union[datetime.date, None]:
    """Attempts to find and parse a date from the text."""
    # Common date patterns (add more as needed)
    patterns = [
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', # DD/MM/YYYY, DD-MM-YYYY, etc.
        r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}', # DD Month YYYY
        r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}' # Month DD, YYYY
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(0)
            # Try parsing with common formats
            for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y",
                        "%d %b %Y", "%d %B %Y", "%b %d %Y", "%B %d %Y",
                        "%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                 try:
                     return datetime.strptime(date_str, fmt).date()
                 except ValueError:
                     continue
    logger.warning("Could not extract or parse date from OCR text.")
    return None

def extract_notes(text: str) -> Union[str, None]:
    """Attempts to extract doctor's notes (often follows keywords like Rx, Diagnosis, Notes)."""
    # Simple approach: Look for sections starting with common keywords
    keywords = ["Rx", "Diagnosis", "Notes", "Advice", "Medication", "Prescription"]
    best_guess = None
    start_index = -1

    for keyword in keywords:
        # Use raw string (r"...") or escape backslash (\\s) for regex patterns
        match = re.search(rf"({keyword}[\s:]+)", text, re.IGNORECASE)
        if match:
            current_start = match.end()
            # If this keyword appears later in the text, it might be a better starting point
            if current_start > start_index:
                start_index = current_start
                # Take a reasonable chunk of text after the keyword
                # This is a heuristic and might need significant improvement
                potential_notes = text[start_index:].strip()
                # Try to limit the notes section (e.g., stop at next major section or signature)
                potential_notes = re.split(r'\n\s*\n|Signature:|Doctor:', potential_notes, 1)[0].strip()
                best_guess = potential_notes

    if best_guess:
        return best_guess
    else:
        # Fallback: return a portion of the text if no keywords found? Risky.
        logger.warning("Could not clearly identify doctor's notes section.")
        return None # Or potentially return a large chunk of the lower part of the text

# --- Main Processing Function ---

async def process_prescription_image(image_bytes: bytes) -> PrescriptionData:
    """
    Processes prescription image bytes using Tesseract OCR and extracts structured data.

    Args:
        image_bytes: The prescription image file in bytes.

    Returns:
        A PrescriptionData object containing the extracted information.
    """
    logger.info("Starting prescription image processing...")
    extracted_data = PrescriptionData() # Initialize with defaults

    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))

        # Perform OCR
        # Consider adding '--psm' options (e.g., 6 for assuming a single uniform block of text)
        # Consider adding '-l eng' for English language explicitly
        logger.info("Performing OCR using Tesseract...")
        ocr_text = pytesseract.image_to_string(image)
        logger.info(f"OCR Raw Text (first 500 chars): {ocr_text[:500]}...")
        extracted_data.raw_ocr_text = ocr_text

        # --- Extract Fields (Basic Implementation) ---
        # These extractions are basic and may require significant tuning based on actual prescription formats
        logger.info("Attempting to extract structured fields...")

        extracted_data.name = extract_field(ocr_text, ["Patient Name", "Name"])
        extracted_data.age = extract_field(ocr_text, ["Age"])
        extracted_data.gender = extract_field(ocr_text, ["Gender", "Sex"])
        extracted_data.visit_date = extract_date(ocr_text)
        extracted_data.doctor_notes = extract_notes(ocr_text)

        # Log extracted fields
        logger.info(f"Extraction Results: Name='{extracted_data.name}', Age='{extracted_data.age}', "
                    f"Gender='{extracted_data.gender}', Date='{extracted_data.visit_date}', "
                    f"Notes='{extracted_data.doctor_notes[:100] if extracted_data.doctor_notes else None}...'")

    except pytesseract.TesseractNotFoundError:
        logger.error("Tesseract is not installed or not in your PATH. Please install Tesseract.")
        # Re-raise or handle appropriately depending on desired API behavior
        raise HTTPException(status_code=500, detail="OCR processing failed: Tesseract not found.")
    except Exception as e:
        logger.error(f"Error processing image or extracting data: {e}")
        # Include raw text in the response even if extraction fails partially
        extracted_data.raw_ocr_text = extracted_data.raw_ocr_text or "Error during OCR processing."
        # Optionally re-raise or return partial data with error indication in API response

    logger.info("Prescription image processing finished.")
    return extracted_data

# Example usage (for testing purposes)
if __name__ == '__main__':
    # This part runs only when the script is executed directly
    # Replace 'path/to/your/test_prescription.png' with an actual image file
    try:
        with open('path/to/your/test_prescription.png', 'rb') as f:
            test_image_bytes = f.read()

        import asyncio
        # Need to import HTTPException for the main block if testing error cases
        from fastapi import HTTPException

        async def run_test():
            try:
                result = await process_prescription_image(test_image_bytes)
                print("\n--- Extraction Result ---")
                print(result.json(indent=2))
            except FileNotFoundError:
                print("Test image not found. Please update the path in the script.")
            except HTTPException as http_err:
                 print(f"Caught expected HTTP Exception: {http_err.detail}")
            except Exception as err:
                print(f"An unexpected error occurred during testing: {err}")

        asyncio.run(run_test())

    except FileNotFoundError:
         print("Test image file not found. Skipping example run.")
    except ImportError:
         print("FastAPI not installed, skipping HTTPException import for test.")
         # Define a dummy HTTPException if needed for basic testing without fastapi installed
         class HTTPException(Exception):
             def __init__(self, status_code, detail):
                 self.status_code = status_code
                 self.detail = detail
                 super().__init__(detail)
         # Rerun the test definition and execution
         async def run_test():
            try:
                result = await process_prescription_image(test_image_bytes)
                print("\n--- Extraction Result ---")
                print(result.json(indent=2))
            except FileNotFoundError:
                print("Test image not found. Please update the path in the script.")
            except HTTPException as http_err:
                 print(f"Caught expected HTTP Exception: {http_err.detail}")
            except Exception as err:
                print(f"An unexpected error occurred during testing: {err}")
         asyncio.run(run_test())