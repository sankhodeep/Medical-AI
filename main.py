import os
import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status, Path
# APIKey class is not directly used for type hinting with Depends, the dependency function handles it.
from dotenv import load_dotenv
import logging

# Import custom modules
from models import PrescriptionData, PrescriptionUploadResponse, PatientDataResponse
from ocr_processor import process_prescription_image
from supabase_client import save_prescription_data, get_patient_data_from_db, supabase # Import supabase client instance for check
from dependencies import get_api_key

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Medical AI Prescription Processor",
    description="API to upload OPD prescription images, extract data using OCR, and store it in Supabase.",
    version="0.1.0",
)

# --- Dependency Check ---
# Check if Supabase client is initialized on startup
@app.on_event("startup")
async def startup_event():
    if not supabase:
        logger.critical("Supabase client failed to initialize. Check SUPABASE_URL and SUPABASE_KEY environment variables.")
        # You might want to prevent the app from starting fully if Supabase is essential
        # For now, it will log a critical error. Endpoints requiring Supabase will fail.
    else:
        logger.info("FastAPI application started. Supabase client is initialized.")

# --- API Endpoints ---

@app.post("/upload_prescription",
          response_model=PrescriptionUploadResponse,
          summary="Upload Prescription Image",
          description="Uploads a prescription image, performs OCR, extracts data, and saves it to Supabase.",
          status_code=status.HTTP_201_CREATED,
          tags=["Prescriptions"])
async def upload_prescription(
    file: UploadFile = File(..., description="The prescription image file (e.g., PNG, JPG)."),
    api_key: str = Depends(get_api_key) # Enforce API key authentication, type hint as str
):
    """
    Endpoint to upload a prescription image.
    - Requires a valid API key in the 'X-API-KEY' header.
    - Processes the image using Tesseract OCR.
    - Attempts to extract key fields (Name, Age, Gender, Date, Notes).
    - Saves the extracted data (along with raw OCR text) to Supabase.
    """
    logger.info(f"Received file upload request for: {file.filename}")

    # Read image bytes
    try:
        image_bytes = await file.read()
        if not image_bytes:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file content received.")
        logger.info(f"Read {len(image_bytes)} bytes from uploaded file.")
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Error reading file: {e}")
    finally:
        await file.close() # Ensure file is closed

    # Process image with OCR
    try:
        logger.info("Calling OCR processor...")
        extracted_data: PrescriptionData = await process_prescription_image(image_bytes)
        logger.info(f"OCR processing complete. Extracted patient_id (generated): {extracted_data.patient_id}")
    except HTTPException as http_err:
        # Handle specific errors raised by OCR processor (like Tesseract not found)
        logger.error(f"HTTPException during OCR processing: {http_err.detail}")
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error during OCR processing: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing image: {e}")

    # Save data to Supabase
    try:
        logger.info(f"Calling Supabase client to save data for patient_id: {extracted_data.patient_id}")
        saved_record, db_error = await save_prescription_data(extracted_data)

        if db_error:
            logger.error(f"Error saving data to Supabase: {db_error}")
            # Return a 500 error but include the extracted data and patient ID for potential manual entry/retry
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Data extracted but failed to save to database: {db_error}. Patient ID: {extracted_data.patient_id}"
            )
        elif not saved_record:
             logger.error("Data extracted but Supabase returned no record and no error.")
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Data extracted but failed to save to database (unknown reason). Patient ID: {extracted_data.patient_id}"
            )

        logger.info(f"Data successfully saved to Supabase for patient_id: {saved_record.get('patient_id')}")
        # Ensure the patient_id from the DB response is used if it differs (shouldn't with UUID)
        final_patient_id = saved_record.get('patient_id', extracted_data.patient_id)

        return PrescriptionUploadResponse(
            message="Prescription uploaded and processed successfully.",
            patient_id=final_patient_id,
            extracted_data=PrescriptionData(**saved_record) # Use saved data for response consistency
        )

    except HTTPException as http_err:
        # Re-raise HTTPExceptions from the save operation
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error saving data to Supabase: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Data extracted but failed to save to database: {e}. Patient ID: {extracted_data.patient_id}"
        )


@app.get("/get_patient_data/{patient_id}",
         response_model=PatientDataResponse,
         summary="Get Patient Prescription Data",
         description="Retrieves stored prescription data for a given patient ID from Supabase.",
         tags=["Patients"])
async def get_patient_data(
    patient_id: str = Path(..., description="The unique patient ID (UUID format) generated during upload."),
    api_key: str = Depends(get_api_key) # Enforce API key authentication, type hint as str
):
    """
    Endpoint to retrieve patient data based on the unique ID generated during upload.
    - Requires a valid API key in the 'X-API-KEY' header.
    - Fetches the corresponding record from the Supabase 'prescriptions' table.
    """
    logger.info(f"Received request to get data for patient_id: {patient_id}")

    try:
        patient_record, db_error = await get_patient_data_from_db(patient_id)

        if db_error:
            logger.error(f"Error retrieving data from Supabase for patient_id {patient_id}: {db_error}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {db_error}")

        if not patient_record:
            logger.warning(f"Patient data not found for patient_id: {patient_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient data not found")

        logger.info(f"Successfully retrieved data for patient_id: {patient_id}")
        # Map the retrieved dictionary to the response model
        # Handle potential type mismatches or missing keys gracefully if needed
        return PatientDataResponse(**patient_record)

    except HTTPException as http_err:
        # Re-raise HTTPExceptions (like 404 Not Found)
        raise http_err
    except Exception as e:
        logger.error(f"Unexpected error retrieving data for patient_id {patient_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")


# --- Run the application (for local development) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000)) # Default to port 8000
    host = os.environ.get("HOST", "127.0.0.1") # Default to localhost
    logger.info(f"Starting Uvicorn server on {host}:{port}")
    # Ensure Tesseract is installed and configured before running.
    # Ensure .env file exists with SUPABASE_URL, SUPABASE_KEY, and API_KEY.
    uvicorn.run(app, host=host, port=port)