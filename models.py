from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
import uuid

class PrescriptionData(BaseModel):
    """
    Pydantic model representing the structured data extracted from a prescription.
    """
    patient_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the patient visit")
    name: Optional[str] = Field(None, description="Patient's Name")
    age: Optional[str] = Field(None, description="Patient's Age") # Using str to accommodate variations like '6 months'
    gender: Optional[str] = Field(None, description="Patient's Gender")
    visit_date: Optional[date] = Field(None, description="Date of the prescription/visit")
    doctor_notes: Optional[str] = Field(None, description="Extracted Doctor's Notes/Diagnosis/Medication")
    raw_ocr_text: Optional[str] = Field(None, description="The full raw text extracted by OCR for reference")

    class Config:
        from_attributes = True # Replaces orm_mode in Pydantic v2
        json_schema_extra = { # Replaces schema_extra in Pydantic v2
            "example": {
                "patient_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John Doe",
                "age": "35",
                "gender": "Male",
                "visit_date": "2025-04-01",
                "doctor_notes": "Prescribed Paracetamol 500mg twice daily for fever.",
                "raw_ocr_text": "Patient Name: John Doe Age: 35 Sex: M Date: 01/04/2025 Rx Paracetamol 500mg..."
            }
        }

class PrescriptionUploadResponse(BaseModel):
    """
    Response model after successfully uploading and processing a prescription.
    """
    message: str
    patient_id: str
    extracted_data: PrescriptionData

class PatientDataResponse(BaseModel):
    """
    Response model for retrieving patient data.
    """
    patient_id: str
    name: Optional[str]
    age: Optional[str]
    gender: Optional[str]
    visit_date: Optional[date]
    doctor_notes: Optional[str]