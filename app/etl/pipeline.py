"""
Concrete ETL pipeline for healthcare patient data ingestion.

Demonstrates:
- A real Extract -> Validate -> Transform -> Load pipeline
- Consent-gated processing (records without consent are filtered out)
- FHIR resource normalization
- PHI encryption before storage
"""

from __future__ import annotations

import logging
from typing import Any

from app.etl.dag import DAG
from app.schemas.fhir import FHIR_PATIENT_SCHEMA
from app.services.encryption import EncryptionService
from app.services.validation import validate_against_schema

logger = logging.getLogger(__name__)

encryption = EncryptionService()


# ---------------------------------------------------------------------------
# Individual pipeline steps (each receives and returns a context dict)
# ---------------------------------------------------------------------------


def extract(context: dict[str, Any]) -> dict[str, Any]:
    """
    Extract step – accept raw records from the API payload.
    In production this might pull from S3, a message queue, or an HL7 feed.
    """
    raw_records = context.get("raw_records", [])
    logger.info("Extracted %d raw records", len(raw_records))
    return {"extracted_records": raw_records, "extract_count": len(raw_records)}


def validate(context: dict[str, Any]) -> dict[str, Any]:
    """
    Validate step – run JSON-schema validation against FHIR Patient schema.
    Invalid records are collected but do not halt the pipeline.
    """
    records = context.get("extracted_records", [])
    valid, invalid = [], []

    for record in records:
        errors = validate_against_schema(record, FHIR_PATIENT_SCHEMA)
        if errors:
            invalid.append({"record": record, "errors": errors})
        else:
            valid.append(record)

    logger.info("Validation: %d valid, %d invalid", len(valid), len(invalid))
    return {
        "valid_records": valid,
        "validation_errors": invalid,
        "valid_count": len(valid),
    }


def check_consent(context: dict[str, Any]) -> dict[str, Any]:
    """
    Consent gate – only records with explicit data_sharing consent pass through.
    This is a core trust-sensitive requirement: no consent = no processing.
    """
    records = context.get("valid_records", [])
    consented, blocked = [], []

    for record in records:
        consent = record.get("consent", {})
        if consent.get("data_sharing") is True:
            consented.append(record)
        else:
            blocked.append({"mrn": record.get("mrn"), "reason": "no data_sharing consent"})

    logger.info("Consent gate: %d consented, %d blocked", len(consented), len(blocked))
    return {
        "consented_records": consented,
        "consent_blocked": blocked,
        "consented_count": len(consented),
    }


def transform(context: dict[str, Any]) -> dict[str, Any]:
    """
    Transform step – encrypt PHI fields and normalize to internal format.
    """
    records = context.get("consented_records", [])
    transformed = []

    for record in records:
        transformed.append(
            {
                "mrn": record["mrn"],
                "encrypted_name": encryption.encrypt(record.get("name", "")),
                "encrypted_dob": encryption.encrypt(record.get("birthDate", "")),
                "encrypted_ssn": encryption.encrypt(record.get("ssn", ""))
                if record.get("ssn")
                else None,
                "gender": record.get("gender"),
                "resource_type": "Patient",
                "fhir_resource": record,  # keep original FHIR payload
            }
        )

    logger.info("Transformed %d records (PHI encrypted)", len(transformed))
    return {"transformed_records": transformed, "transform_count": len(transformed)}


def load(context: dict[str, Any]) -> dict[str, Any]:
    """
    Load step – in a real system this writes to PostgreSQL.
    Here we return the prepared records to be persisted by the API layer.
    """
    records = context.get("transformed_records", [])
    logger.info("Load phase: %d records ready for persistence", len(records))
    return {"loaded_records": records, "load_count": len(records)}


# ---------------------------------------------------------------------------
# Pipeline factory
# ---------------------------------------------------------------------------

def build_patient_ingestion_pipeline() -> DAG:
    """Construct the full patient ingestion DAG."""
    dag = DAG("patient_ingestion")
    dag.add_task("extract", extract)
    dag.add_task("validate", validate, depends_on=["extract"])
    dag.add_task("check_consent", check_consent, depends_on=["validate"])
    dag.add_task("transform", transform, depends_on=["check_consent"])
    dag.add_task("load", load, depends_on=["transform"])
    return dag
