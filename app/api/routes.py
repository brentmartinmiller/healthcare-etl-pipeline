"""
FastAPI routes – the main API surface.

Demonstrates:
- RESTful endpoint design
- Dependency injection (database session via Depends)
- Running the ETL pipeline via an HTTP trigger
- Returning structured responses with Pydantic models
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.etl.pipeline import build_patient_ingestion_pipeline
from app.models.database import get_db
from app.models.patient import (
    ClinicalRecord,
    ConsentRecord,
    Patient,
    PipelineRun,
)
from app.schemas.api import (
    HealthResponse,
    IngestionRequest,
    PatientResponse,
    PipelineResult,
    TaskSummary,
)
from app.services.audit import log_action

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Basic health endpoint – verifies DB connectivity."""
    try:
        db.execute("SELECT 1")  # type: ignore[arg-type]
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return HealthResponse(
        status="healthy",
        environment=settings.ENVIRONMENT,
        database=db_status,
    )


# ---------------------------------------------------------------------------
# ETL Pipeline trigger
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=PipelineResult)
def ingest_patients(request: IngestionRequest, db: Session = Depends(get_db)):
    """
    Accept a batch of patient records, run them through the ETL pipeline,
    and persist the results.
    """
    raw_records = [r.model_dump() for r in request.records]

    # Build and run the DAG
    pipeline = build_patient_ingestion_pipeline()
    result = pipeline.run(initial_context={"raw_records": raw_records})

    # Persist loaded records to the database
    loaded = []
    for task in pipeline.tasks.values():
        if task.name == "load" and task.result:
            loaded = task.result.get("loaded_records", [])

    persisted_count = 0
    for record in loaded:
        patient = Patient(
            mrn=record["mrn"],
            encrypted_name=record["encrypted_name"],
            encrypted_dob=record["encrypted_dob"],
            encrypted_ssn=record.get("encrypted_ssn"),
            gender=record.get("gender"),
        )
        db.add(patient)
        db.flush()

        # Store consent
        consent_data = record.get("fhir_resource", {}).get("consent", {})
        for consent_type, granted in consent_data.items():
            db.add(
                ConsentRecord(
                    patient_id=patient.id,
                    consent_type=consent_type,
                    granted=granted,
                    granted_at=datetime.now(datetime.timezone.utc) if granted else None,
                )
            )

        # Store FHIR resource
        db.add(
            ClinicalRecord(
                patient_id=patient.id,
                resource_type="Patient",
                fhir_resource=record["fhir_resource"],
            )
        )

        log_action(
            db,
            actor="etl_pipeline",
            action="create",
            resource_type="Patient",
            resource_id=patient.id,
            detail={"mrn": record["mrn"], "pipeline": pipeline.name},
        )
        persisted_count += 1

    # Record the pipeline run
    pipeline_run = PipelineRun(
        pipeline_name=pipeline.name,
        status=result["status"],
        started_at=datetime.now(datetime.timezone.utc),
        completed_at=datetime.now(datetime.timezone.utc),
        input_record_count=str(len(raw_records)),
        output_record_count=str(persisted_count),
        errors=result.get("tasks", {}),
        dag_definition=pipeline.to_dict(),
    )
    db.add(pipeline_run)
    db.commit()

    # Build response
    record_counts = {}
    for task_name, task in pipeline.tasks.items():
        for key, value in task.result.items():
            if key.endswith("_count"):
                record_counts[key] = value

    return PipelineResult(
        pipeline=result["pipeline"],
        status=result["status"],
        tasks={
            name: TaskSummary(**info) for name, info in result["tasks"].items()
        },
        record_counts=record_counts,
    )


# ---------------------------------------------------------------------------
# Patient lookup (consent-gated)
# ---------------------------------------------------------------------------

@router.get("/patients/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: UUID, db: Session = Depends(get_db)):
    """
    Retrieve a patient by ID.
    Only returns data if the patient has data_sharing consent.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    has_consent = any(
        c.consent_type == "data_sharing" and c.granted for c in patient.consents
    )
    if not has_consent:
        raise HTTPException(
            status_code=403,
            detail="Patient has not granted data sharing consent",
        )

    log_action(
        db,
        actor="api_user",
        action="read",
        resource_type="Patient",
        resource_id=patient.id,
    )
    db.commit()

    return PatientResponse(
        id=patient.id,
        mrn=patient.mrn,
        gender=patient.gender,
        created_at=patient.created_at,
        has_data_sharing_consent=True,
    )


@router.get("/patients", response_model=list[PatientResponse])
def list_patients(db: Session = Depends(get_db)):
    """List all patients who have granted data sharing consent."""
    patients = db.query(Patient).all()
    results = []
    for patient in patients:
        has_consent = any(
            c.consent_type == "data_sharing" and c.granted for c in patient.consents
        )
        if has_consent:
            results.append(
                PatientResponse(
                    id=patient.id,
                    mrn=patient.mrn,
                    gender=patient.gender,
                    created_at=patient.created_at,
                    has_data_sharing_consent=True,
                )
            )
    return results
