# Medical AI Prescription Processor Backend

## Overview

This project provides a backend API service built with FastAPI for processing Optical Prescriptions (OPD). It allows users (e.g., doctors, medical staff) to upload images of prescriptions. The backend then uses Tesseract OCR to extract key patient details and stores this structured information in a Supabase (PostgreSQL) database.

The system is designed with scalability and future AI integration in mind.

## Features

*   **Prescription Upload:** Accepts prescription images via a POST request.
*   **OCR Processing:** Uses Tesseract OCR to extract text from images.
*   **Data Extraction:** Attempts to identify and extract specific fields: Patient Name, Age, Gender, Visit Date, and Doctor's Notes.
*   **Database Storage:** Stores extracted data in a structured format in a Supabase PostgreSQL database.
*   **Data Retrieval:** Allows fetching stored patient prescription data by a unique ID.
*   **API Security:** Uses API Key authentication for endpoint access.
*   **Asynchronous:** Built with FastAPI for high performance.

## Tech Stack

*   **Backend Framework:** FastAPI
*   **Database:** Supabase (PostgreSQL)
*   **OCR Engine:** Tesseract OCR
*   **Web Server:** Uvicorn
*   **Language:** Python 3.8+
*   **Libraries:**
    *   `python-dotenv` (for environment variables)
    *   `supabase` (Supabase Python client)
    *   `pytesseract` (Tesseract wrapper)
    *   `Pillow` (Image manipulation)
    *   `python-multipart` (for file uploads in FastAPI)

## Project Structure

```
/workspaces/Medical-AI/
├── .env.example        # Example environment variable configuration
├── .env                # Actual environment variables (Create this file)
├── requirements.txt    # Python package dependencies
├── dependencies.py     # API Key authentication logic
├── models.py           # Pydantic models for data validation and structure
├── supabase_client.py  # Handles interaction with the Supabase database
├── ocr_processor.py    # Contains logic for OCR processing and data extraction
├── main.py             # Main FastAPI application, defines API endpoints
└── README.md           # This file
```

*   **`main.py`**: Entry point of the FastAPI application. Defines API routes (`/upload_prescription`, `/get_patient_data/{patient_id}`) and orchestrates the workflow.
*   **`ocr_processor.py`**: Handles receiving image bytes, performing OCR using `pytesseract`, and attempting to parse the raw OCR text to extract relevant fields.
*   **`supabase_client.py`**: Initializes the Supabase client using credentials from environment variables and provides functions to save (`save_prescription_data`) and retrieve (`get_patient_data_from_db`) data from the `prescriptions` table.
*   **`models.py`**: Defines Pydantic models (`PrescriptionData`, `PrescriptionUploadResponse`, `PatientDataResponse`) to ensure data consistency, validation, and clear API schema definition (used in Swagger UI).
*   **`dependencies.py`**: Contains the `get_api_key` dependency function used by FastAPI endpoints to require and validate the `X-API-KEY` header.
*   **`requirements.txt`**: Lists all necessary Python packages. Install using `pip install -r requirements.txt`.
*   **`.env.example`**: A template file showing the required environment variables. Copy this to `.env` and fill in your actual credentials.
*   **`.env`**: (You need to create this) Stores your actual sensitive credentials (Supabase URL, Supabase Key, API Key). This file is ignored by Git (if using version control).

## Setup and Installation

**1. Prerequisites:**

*   **Python:** Version 3.8 or higher installed.
*   **pip:** Python package installer.
*   **Tesseract OCR Engine:** You MUST install the Tesseract OCR engine itself on the system where the backend will run.
    *   **Ubuntu/Debian:** `sudo apt update && sudo apt install tesseract-ocr tesseract-ocr-eng` (Install English language pack)
    *   **macOS (using Homebrew):** `brew install tesseract tesseract-lang`
    *   **Windows:** Download installer from the [official Tesseract repository](https://github.com/UB-Mannheim/tesseract/wiki). During installation, make sure to include the necessary language packs (e.g., English).
    *   **Verify Installation:** Open your terminal/command prompt and run `tesseract --version`.
*   **Supabase Account:** A free or paid account on [Supabase](https://supabase.com/).

**2. Clone the Repository (if applicable):**

```bash
git clone <your-repository-url>
cd <repository-directory>
```

**3. Create a Virtual Environment (Recommended):**

```bash
python -m venv venv
# Activate the environment
# Linux/macOS:
source venv/bin/activate
# Windows (cmd):
venv\Scripts\activate.bat
# Windows (PowerShell):
venv\Scripts\Activate.ps1
```

**4. Install Dependencies:**

```bash
pip install -r requirements.txt
```

**5. Configure Tesseract Path (if needed):**

*   `pytesseract` usually finds Tesseract automatically if it's in your system's PATH.
*   If you encounter `TesseractNotFoundError`, you might need to explicitly set the path to the Tesseract executable within `ocr_processor.py`. Uncomment and modify the relevant line:
    ```python
    # In ocr_processor.py
    # Example for Windows:
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    ```

## Configuration

**1. Environment Variables (`.env` file):**

*   Copy the example file: `cp .env.example .env`
*   Edit the `.env` file and replace the placeholder values with your actual credentials:

    ```dotenv
    # Supabase Credentials - Get these from your Supabase project settings
    SUPABASE_URL="YOUR_SUPABASE_URL"
    SUPABASE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY" # IMPORTANT: Use the 'service_role' key for backend operations

    # API Security Key - Choose a strong, random key for securing your API
    API_KEY="YOUR_CHOSEN_SECURE_API_KEY"
    ```

    *   **`SUPABASE_URL`**: Found in your Supabase project settings (API -> Project URL).
    *   **`SUPABASE_KEY`**: Use the **`service_role`** key found in your Supabase project settings (API -> Project API Keys). **Keep this key secret!** It bypasses Row Level Security.
    *   **`API_KEY`**: Choose a strong, unpredictable string. This key must be sent by clients in the `X-API-KEY` header to access the API endpoints.

**2. Supabase Database Table:**

*   You need to create a table named `prescriptions` in your Supabase project's database.
*   Go to your Supabase project dashboard -> SQL Editor -> New Query.
*   Run the following SQL command:

    ```sql
    CREATE TABLE public.prescriptions (
        id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
        created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
        patient_id UUID DEFAULT gen_random_uuid() NOT NULL UNIQUE, -- Changed to UUID and made unique
        name TEXT NULL,
        age TEXT NULL, -- Using TEXT to allow variations like '6 months'
        gender TEXT NULL,
        visit_date DATE NULL,
        doctor_notes TEXT NULL,
        raw_ocr_text TEXT NULL -- Store the full OCR text for reference/debugging
    );

    -- Optional: Add indexes for faster lookups if needed, e.g., on patient_id
    -- CREATE INDEX idx_prescriptions_patient_id ON public.prescriptions(patient_id);

    -- Enable Row Level Security (Good Practice, though service_role key bypasses it)
    ALTER TABLE public.prescriptions ENABLE ROW LEVEL SECURITY;

    -- Define policies if you plan to access data with anon or authenticated keys later
    -- Example (Allow public read access - adjust as needed):
    -- CREATE POLICY "Allow public read access" ON public.prescriptions
    -- FOR SELECT USING (true);

    -- Example (Allow authenticated write access - adjust as needed):
    -- CREATE POLICY "Allow authenticated write access" ON public.prescriptions
    -- FOR INSERT WITH CHECK (auth.role() = 'authenticated');
    ```
    *   *Note:* The `patient_id` is now a `UUID` generated by the database by default and marked `UNIQUE`. The Python code also generates a UUID but relies on the database constraint.

## Running the Application

1.  Ensure your virtual environment is activated.
2.  Make sure the `.env` file is correctly configured.
3.  Run the FastAPI application using Uvicorn:

    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```

    *   `--reload`: Enables auto-reloading when code changes (useful for development).
    *   `--host 0.0.0.0`: Makes the server accessible on your local network (use `127.0.0.1` for localhost only).
    *   `--port 8000`: Specifies the port number.

4.  The API will be running at `http://<your-host-ip>:8000` (e.g., `http://127.0.0.1:8000`).
5.  Access the interactive API documentation (Swagger UI) at `http://<your-host-ip>:8000/docs`.

## API Usage

**Authentication:**

*   All endpoints require an API key passed in the `X-API-KEY` request header.
*   Use the value you set for `API_KEY` in your `.env` file.

**Endpoints:**

1.  **`POST /upload_prescription`**
    *   **Description:** Uploads a prescription image for processing.
    *   **Headers:**
        *   `X-API-KEY`: `YOUR_CHOSEN_SECURE_API_KEY`
    *   **Body:** `multipart/form-data` containing the image file.
        *   Key: `file`
        *   Value: The image file (e.g., `my_prescription.png`)
    *   **Example (`curl`):**
        ```bash
        curl -X POST "http://127.0.0.1:8000/upload_prescription" \
             -H "accept: application/json" \
             -H "X-API-KEY: YOUR_CHOSEN_SECURE_API_KEY" \
             -F "file=@/path/to/your/prescription.jpg"
        ```
    *   **Success Response (`201 Created`):**
        ```json
        {
          "message": "Prescription uploaded and processed successfully.",
          "patient_id": "generated-unique-uuid-string",
          "extracted_data": {
            "patient_id": "generated-unique-uuid-string",
            "name": "Extracted Name",
            "age": "Extracted Age",
            "gender": "Extracted Gender",
            "visit_date": "YYYY-MM-DD",
            "doctor_notes": "Extracted Notes...",
            "raw_ocr_text": "Full raw text from OCR..."
          }
        }
        ```
    *   **Error Responses:** `400` (Bad Request), `403` (Forbidden - Invalid API Key), `500` (Internal Server Error - OCR/DB issues).

2.  **`GET /get_patient_data/{patient_id}`**
    *   **Description:** Retrieves previously stored prescription data.
    *   **Headers:**
        *   `X-API-KEY`: `YOUR_CHOSEN_SECURE_API_KEY`
    *   **Path Parameter:**
        *   `patient_id`: The unique UUID generated during the upload process.
    *   **Example (`curl`):**
        ```bash
        curl -X GET "http://127.0.0.1:8000/get_patient_data/the-uuid-from-upload-response" \
             -H "accept: application/json" \
             -H "X-API-KEY: YOUR_CHOSEN_SECURE_API_KEY"
        ```
    *   **Success Response (`200 OK`):**
        ```json
        {
          "patient_id": "the-uuid-from-upload-response",
          "name": "Stored Name",
          "age": "Stored Age",
          "gender": "Stored Gender",
          "visit_date": "YYYY-MM-DD",
          "doctor_notes": "Stored Notes..."
        }
        ```
    *   **Error Responses:** `403` (Forbidden - Invalid API Key), `404` (Not Found), `500` (Internal Server Error).

## OCR Processing Notes

*   **Accuracy:** The current OCR extraction logic in `ocr_processor.py` is **basic**. It uses simple keyword searching and regular expressions. Its accuracy heavily depends on the clarity, layout, and consistency of the prescription images.
*   **Limitations:** It may fail to extract fields correctly if the keywords are different, the layout varies significantly, or the OCR quality is poor. Handwritten notes are particularly challenging for standard Tesseract.
*   **Potential Improvements:**
    *   **Fine-tuning Regex:** Adapt the regular expressions in `extract_field`, `extract_date`, etc., based on common patterns observed in your actual prescription images.
    *   **Layout Analysis:** Use Tesseract's Page Segmentation Modes (`--psm`) or libraries like `OpenCV` for pre-processing and layout detection.
    *   **Template Matching:** If prescriptions follow a few standard templates, identify the template first and then apply targeted extraction rules.
    *   **NLP Techniques:** Use Natural Language Processing libraries (like spaCy or NLTK) to understand the context and relationships between words after OCR.
    *   **Vision Language Models (VLMs):** Integrate models like OpenAI's GPT-4 Vision or other specialized document AI services for potentially much higher accuracy, especially with varied layouts and handwriting (would require API keys and potentially costs). The code can be adapted to call these services instead of Tesseract.

## Future Enhancements

*   Integrate a more advanced OCR/VLM solution.
*   Add more sophisticated data validation and cleaning.
*   Develop a frontend interface for uploading images and viewing data.
*   Implement user authentication (e.g., JWT) for different user roles.
*   Add AI models for analyzing doctor's notes (e.g., identifying medications, diagnoses).
*   Implement background task processing (e.g., using Celery) for long-running OCR tasks.
