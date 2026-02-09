"""Tests for the patient ingestion pipeline – no database required."""

from app.etl.pipeline import build_patient_ingestion_pipeline


def _make_patient(mrn="MRN-001", consent_sharing=True, name="Jane Doe"):
    return {
        "resourceType": "Patient",
        "mrn": mrn,
        "name": name,
        "birthDate": "1990-01-15",
        "gender": "female",
        "consent": {"data_sharing": consent_sharing, "research": False},
    }


def test_full_pipeline_happy_path():
    """Valid, consented records flow through all five stages."""
    pipeline = build_patient_ingestion_pipeline()
    result = pipeline.run({"raw_records": [_make_patient()]})

    assert result["status"] == "completed"
    assert pipeline.tasks["load"].result["load_count"] == 1

    # PHI should be encrypted (not plaintext)
    loaded = pipeline.tasks["load"].result["loaded_records"][0]
    assert loaded["encrypted_name"] != "Jane Doe"
    assert loaded["mrn"] == "MRN-001"


def test_invalid_record_rejected():
    """A record missing required 'name' field fails validation."""
    bad_record = {"resourceType": "Patient", "mrn": "MRN-BAD"}
    pipeline = build_patient_ingestion_pipeline()
    result = pipeline.run({"raw_records": [bad_record]})

    assert result["status"] == "completed"
    assert pipeline.tasks["validate"].result["valid_count"] == 0
    assert len(pipeline.tasks["validate"].result["validation_errors"]) == 1


def test_no_consent_blocks_processing():
    """Records without data_sharing consent are blocked at the consent gate."""
    pipeline = build_patient_ingestion_pipeline()
    result = pipeline.run({"raw_records": [_make_patient(consent_sharing=False)]})

    assert result["status"] == "completed"
    assert pipeline.tasks["check_consent"].result["consented_count"] == 0
    assert len(pipeline.tasks["check_consent"].result["consent_blocked"]) == 1


def test_mixed_batch():
    """Pipeline correctly splits a batch of valid, invalid, and non-consented records."""
    records = [
        _make_patient(mrn="MRN-1", consent_sharing=True),
        _make_patient(mrn="MRN-2", consent_sharing=False),
        {"resourceType": "Patient", "mrn": "MRN-3"},  # missing 'name'
    ]
    pipeline = build_patient_ingestion_pipeline()
    result = pipeline.run({"raw_records": records})

    assert result["status"] == "completed"
    assert pipeline.tasks["validate"].result["valid_count"] == 2
    assert pipeline.tasks["check_consent"].result["consented_count"] == 1
    assert pipeline.tasks["load"].result["load_count"] == 1
