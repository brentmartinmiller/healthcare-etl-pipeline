"""Tests for JSON schema validation."""

from app.schemas.fhir import FHIR_PATIENT_SCHEMA
from app.services.validation import validate_against_schema


def test_valid_patient():
    record = {
        "resourceType": "Patient",
        "mrn": "MRN-001",
        "name": "Jane Doe",
        "birthDate": "1990-01-15",
        "gender": "female",
    }
    errors = validate_against_schema(record, FHIR_PATIENT_SCHEMA)
    assert errors == []


def test_missing_required_fields():
    record = {"resourceType": "Patient"}
    errors = validate_against_schema(record, FHIR_PATIENT_SCHEMA)
    assert any("mrn" in e for e in errors)
    assert any("name" in e for e in errors)


def test_invalid_date_format():
    record = {
        "resourceType": "Patient",
        "mrn": "MRN-001",
        "name": "Jane",
        "birthDate": "01/15/1990",  # wrong format
    }
    errors = validate_against_schema(record, FHIR_PATIENT_SCHEMA)
    assert len(errors) > 0


def test_invalid_gender():
    record = {
        "resourceType": "Patient",
        "mrn": "MRN-001",
        "name": "Jane",
        "gender": "invalid_value",
    }
    errors = validate_against_schema(record, FHIR_PATIENT_SCHEMA)
    assert len(errors) > 0
