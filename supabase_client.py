import os
from supabase import create_client, Client
from dotenv import load_dotenv
from models import PrescriptionData
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Get Supabase credentials from environment variables
supabase_url: str = os.environ.get("SUPABASE_URL")
supabase_key: str = os.environ.get("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        # Depending on the desired behavior, you might want to exit or handle this differently
else:
    logger.warning("Supabase URL or Key not found in environment variables. Supabase client not initialized.")

# Define the table name in Supabase
TABLE_NAME = "prescriptions"

async def save_prescription_data(data: PrescriptionData) -> tuple[dict | None, str | None]:
    """
    Saves the extracted prescription data to the Supabase 'prescriptions' table.

    Args:
        data (PrescriptionData): The Pydantic model containing the data to save.

    Returns:
        tuple[dict | None, str | None]: A tuple containing the saved data record (dict)
                                         or None, and an error message (str) or None.
    """
    if not supabase:
        error_msg = "Supabase client is not initialized. Cannot save data."
        logger.error(error_msg)
        return None, error_msg

    try:
        # Convert Pydantic model to dictionary, handling potential date conversion
        data_dict = data.dict()
        if data_dict.get('visit_date'):
             data_dict['visit_date'] = str(data_dict['visit_date']) # Ensure date is string for Supabase

        logger.info(f"Attempting to insert data into Supabase table '{TABLE_NAME}': {data_dict}")

        # Insert data into the table
        response = supabase.table(TABLE_NAME).insert(data_dict).execute()

        logger.info(f"Supabase insert response: {response}")

        # Check if the insert was successful (Supabase API v2 returns data in response.data)
        if response.data and len(response.data) > 0:
            saved_record = response.data[0]
            logger.info(f"Data successfully saved to Supabase with patient_id: {saved_record.get('patient_id')}")
            return saved_record, None
        else:
            # Log the full response if data is empty or missing
            error_msg = f"Supabase insert failed or returned no data. Response: {response}"
            logger.error(error_msg)
            # Attempt to extract more specific error details if available
            if hasattr(response, 'error') and response.error:
                 error_msg = f"Supabase insert error: {response.error.message}"
                 logger.error(error_msg)
            elif hasattr(response, 'status_code') and response.status_code >= 400:
                 error_msg = f"Supabase insert failed with status code: {response.status_code}"
                 logger.error(error_msg)

            return None, error_msg

    except Exception as e:
        error_msg = f"An unexpected error occurred while saving data to Supabase: {e}"
        logger.exception(error_msg) # Use exception to include traceback
        return None, error_msg

async def get_patient_data_from_db(patient_id: str) -> tuple[dict | None, str | None]:
    """
    Retrieves patient data from the Supabase 'prescriptions' table by patient_id.

    Args:
        patient_id (str): The unique identifier for the patient visit.

    Returns:
        tuple[dict | None, str | None]: A tuple containing the patient data record (dict)
                                         or None if not found, and an error message (str) or None.
    """
    if not supabase:
        error_msg = "Supabase client is not initialized. Cannot retrieve data."
        logger.error(error_msg)
        return None, error_msg

    try:
        logger.info(f"Attempting to retrieve data from Supabase table '{TABLE_NAME}' for patient_id: {patient_id}")
        response = supabase.table(TABLE_NAME).select("*").eq("patient_id", patient_id).execute()
        logger.info(f"Supabase select response: {response}")

        if response.data and len(response.data) > 0:
            patient_record = response.data[0]
            logger.info(f"Data successfully retrieved for patient_id: {patient_id}")
            return patient_record, None
        elif not response.data:
             logger.warning(f"No data found for patient_id: {patient_id}")
             return None, None # No error, just not found
        else:
            error_msg = f"Supabase select failed or returned unexpected data. Response: {response}"
            logger.error(error_msg)
            if hasattr(response, 'error') and response.error:
                 error_msg = f"Supabase select error: {response.error.message}"
                 logger.error(error_msg)
            return None, error_msg

    except Exception as e:
        error_msg = f"An unexpected error occurred while retrieving data from Supabase: {e}"
        logger.exception(error_msg)
        return None, error_msg