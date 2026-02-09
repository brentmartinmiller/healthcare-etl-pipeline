"""
FHIR-inspired JSON schemas for data validation.

Demonstrates:
- Familiarity with FHIR data standards (Patient resource structure)
- JSON Schema validation as a contract for incoming data
- Pragmatic subset – real FHIR schemas are enormous; this captures the
  key structural elements an interviewer would expect you to know.
"""

FHIR_PATIENT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FHIR Patient (simplified)",
    "description": "Subset of the HL7 FHIR R4 Patient resource for ETL ingestion.",
    "type": "object",
    "required": ["resourceType", "mrn", "name"],
    "properties": {
        "resourceType": {
            "type": "string",
            "const": "Patient",
            "description": "Must be 'Patient' per FHIR spec.",
        },
        "mrn": {
            "type": "string",
            "minLength": 1,
            "description": "Medical Record Number – primary business identifier.",
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Simplified from FHIR HumanName for this demo.",
        },
        "birthDate": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$",
            "description": "ISO 8601 date (YYYY-MM-DD).",
        },
        "gender": {
            "type": "string",
            "enum": ["male", "female", "other", "unknown"],
            "description": "Administrative gender per FHIR value set.",
        },
        "ssn": {
            "type": "string",
            "pattern": "^\\d{3}-\\d{2}-\\d{4}$",
            "description": "Social Security Number (PII – will be encrypted).",
        },
        "consent": {
            "type": "object",
            "description": "Consent flags – must have data_sharing=true to proceed.",
            "properties": {
                "data_sharing": {"type": "boolean"},
                "research": {"type": "boolean"},
            },
        },
    },
    "additionalProperties": False,
}


FHIR_OBSERVATION_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "FHIR Observation (simplified)",
    "type": "object",
    "required": ["resourceType", "status", "code"],
    "properties": {
        "resourceType": {"type": "string", "const": "Observation"},
        "status": {
            "type": "string",
            "enum": ["registered", "preliminary", "final", "amended"],
        },
        "code": {
            "type": "object",
            "description": "LOINC or SNOMED coded value.",
            "required": ["coding"],
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["system", "code"],
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"},
                        },
                    },
                }
            },
        },
        "valueQuantity": {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "unit": {"type": "string"},
            },
        },
    },
    "additionalProperties": False,
}
