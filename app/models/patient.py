"""
Data models for trust-sensitive healthcare domain.

Demonstrates:
- PostgreSQL data modeling with proper normalization
- PHI/PII column separation (encrypted vs. non-sensitive)
- Consent-gated data access patterns
- Audit trail for compliance
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.models.database import Base


# ---------------------------------------------------------------------------
# Patient – core identity (contains PHI)
# ---------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # PHI fields – stored encrypted at rest via pgcrypto or app-layer encryption
    encrypted_name = Column(Text, nullable=False, comment="AES-encrypted full name")
    encrypted_dob = Column(Text, nullable=False, comment="AES-encrypted date of birth")
    encrypted_ssn = Column(Text, nullable=True, comment="AES-encrypted SSN")

    # Non-sensitive operational fields
    mrn = Column(String(64), unique=True, nullable=False, comment="Medical Record Number")
    gender = Column(String(16))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    consents = relationship("ConsentRecord", back_populates="patient", lazy="selectin")
    records = relationship("ClinicalRecord", back_populates="patient", lazy="selectin")

    __table_args__ = (Index("ix_patients_mrn", "mrn"),)


# ---------------------------------------------------------------------------
# Consent – tracks what data a patient has agreed to share
# ---------------------------------------------------------------------------
class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    consent_type = Column(
        Enum("data_sharing", "research", "treatment", name="consent_type_enum"),
        nullable=False,
    )
    granted = Column(Boolean, default=False, nullable=False)
    granted_at = Column(DateTime)
    revoked_at = Column(DateTime, nullable=True)
    source_document = Column(Text, comment="Reference to signed consent form")

    patient = relationship("Patient", back_populates="consents")

    __table_args__ = (
        UniqueConstraint("patient_id", "consent_type", name="uq_patient_consent"),
    )


# ---------------------------------------------------------------------------
# Clinical Record – FHIR-inspired resource storage
# ---------------------------------------------------------------------------
class ClinicalRecord(Base):
    __tablename__ = "clinical_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    resource_type = Column(
        String(64), nullable=False, comment="FHIR resource type, e.g. Observation"
    )
    fhir_resource = Column(JSONB, nullable=False, comment="Full FHIR JSON payload")
    status = Column(String(32), default="active")
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="records")

    __table_args__ = (
        Index("ix_clinical_resource_type", "resource_type"),
        Index("ix_clinical_patient", "patient_id"),
    )


# ---------------------------------------------------------------------------
# Audit Log – immutable compliance trail
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(String(128), nullable=False, comment="User or service identity")
    action = Column(String(64), nullable=False, comment="create | read | update | delete")
    resource_type = Column(String(64), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=False)
    detail = Column(JSONB, comment="Diff or context for the action")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (Index("ix_audit_timestamp", "timestamp"),)


# ---------------------------------------------------------------------------
# ETL Pipeline Run – tracks pipeline execution history
# ---------------------------------------------------------------------------
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_name = Column(String(128), nullable=False)
    status = Column(
        Enum("pending", "running", "completed", "failed", name="pipeline_status_enum"),
        default="pending",
    )
    started_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    input_record_count = Column(String(16))
    output_record_count = Column(String(16))
    errors = Column(JSONB, default=list)
    dag_definition = Column(JSONB, comment="Snapshot of the DAG that was executed")
