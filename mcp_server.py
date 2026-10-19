import json

from fastmcp import FastMCP
import database as db


mcp = FastMCP("ClinicalDemoTools")


@mcp.tool()
def find_patient(patient_id: str) -> dict:
    """Find a synthetic patient by ID."""
    return db.get("Patients", patient_id) or {}


@mcp.tool()
def create_patient(name: str, age: int | None = None) -> dict:
    """Create a synthetic patient profile."""
    return db.create_patient(name, age)


@mcp.tool()
def save_reviewed_consultation(
    patient_id: str,
    extracted_json: str,
    transcript: str,
    approved_by: str,
) -> dict:
    """Save a consultation after clinician review."""
    if not approved_by.strip():
        raise ValueError("Clinician approval required")

    extracted = json.loads(extracted_json)

    if not isinstance(extracted, dict):
        raise ValueError("Report must be a JSON object")

    return db.save_consultation(
        patient_id,
        extracted,
        transcript,
        approved_by,
    )


@mcp.tool()
def update_patient_record(
    patient_id: str,
    name: str,
    age: int | None = None,
) -> dict:
    """Update an existing patient profile."""
    return db.update_patient(patient_id, name, age)


@mcp.tool()
def update_reviewed_consultation(
    consultation_id: str,
    extracted_json: str,
    approved_by: str,
) -> dict:
    """Save clinician-reviewed corrections."""
    extracted = json.loads(extracted_json)

    if not isinstance(extracted, dict):
        raise ValueError("Report must be a JSON object")

    return db.update_consultation(
        consultation_id,
        extracted,
        approved_by,
    )


@mcp.tool()
def book_confirmed_appointment(
    patient_id: str,
    appointment_at: str,
    clinician: str,
    approved_by: str,
) -> dict:
    """Book an appointment after explicit human confirmation."""
    return db.book_appointment(
        patient_id,
        appointment_at,
        clinician,
        approved_by,
    )


if __name__ == "__main__":
    mcp.run()