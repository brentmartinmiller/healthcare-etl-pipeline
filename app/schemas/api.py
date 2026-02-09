"""Pydantic models for API request/response serialization."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pipeline ingestion
# ---------------------------------------------------------------------------

class PatientRecord(BaseModel):
    """Incoming patient record – matches the FHIR Patient schema."""
    resourceType: str = "Patient"
    mrn: str
    name: str
    birthDate: str | None = None
    gender: str | None = None
    ssn: str | None = None
    consent: dict[str, bool] | None = None


class IngestionRequest(BaseModel):
    """Batch of patient records to ingest through the ETL pipeline."""
    records: list[PatientRecord] = Field(..., min_length=1, max_length=1000)


class TaskSummary(BaseModel):
    status: str
    duration_ms: float | None = None
    error: str | None = None


class PipelineResult(BaseModel):
    pipeline: str
    status: str
    tasks: dict[str, TaskSummary]
    record_counts: dict[str, int] = {}


# ---------------------------------------------------------------------------
# Patient query
# ---------------------------------------------------------------------------

class PatientResponse(BaseModel):
    id: UUID
    mrn: str
    gender: str | None
    created_at: datetime
    has_data_sharing_consent: bool


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str = "healthy"
    environment: str
    database: str = "connected"
