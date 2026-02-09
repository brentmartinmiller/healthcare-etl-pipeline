# Healthcare ETL Pipeline API

A production-style sample project demonstrating backend engineering skills for a healthcare-focused role.

## Quick Start

```bash
docker-compose up --build
```

API available at `http://localhost:8000/docs` (Swagger UI).

### Run Tests (no Docker needed)

```bash
pip install -r requirements.txt
pytest tests/ -v
```

### Example: Ingest Patient Records

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "records": [
      {
        "resourceType": "Patient",
        "mrn": "MRN-001",
        "name": "Jane Doe",
        "birthDate": "1990-01-15",
        "gender": "female",
        "ssn": "123-45-6789",
        "consent": {"data_sharing": true, "research": false}
      }
    ]
  }'
```

---

## How This Maps to the Job Requirements

| Requirement | Where It's Demonstrated |
|---|---|
| **Python (FastAPI)** | `app/main.py`, `app/api/routes.py` – full REST API with dependency injection, Pydantic models, and structured error handling |
| **PostgreSQL & data modeling** | `app/models/patient.py` – 5 normalized tables (Patient, ConsentRecord, ClinicalRecord, AuditLog, PipelineRun) with indexes, constraints, and JSONB columns |
| **ETL pipelines & custom DAGs** | `app/etl/dag.py` – a from-scratch DAG engine with topological sort, dependency tracking, error propagation, and timing. `app/etl/pipeline.py` – a concrete 5-stage pipeline (extract, validate, consent-check, transform, load) |
| **Event-driven architecture** | The DAG engine chains tasks via context passing; each stage emits results consumed by downstream stages. The pipeline is triggered via an HTTP event (POST /ingest) |
| **Containerized infrastructure** | `Dockerfile` (Python 3.12-slim), `docker-compose.yml` (API + PostgreSQL with health checks, volumes) |
| **PHI/PII handling** | `app/services/encryption.py` – AES symmetric encryption (Fernet) for name, DOB, SSN. Key sourced from environment, never hardcoded. PHI columns stored as ciphertext in the DB |
| **Consented data flows** | `app/etl/pipeline.py:check_consent()` – records without explicit `data_sharing` consent are blocked before transformation. `app/api/routes.py:get_patient()` – API refuses to return patient data without consent |
| **Audit trail** | `app/models/patient.py:AuditLog` + `app/services/audit.py` – immutable log of every create/read action with actor, timestamp, and context |
| **FHIR familiarity** | `app/schemas/fhir.py` – JSON schemas modeled after FHIR R4 Patient and Observation resources |
| **JSON-schema validation** | `app/services/validation.py` – Draft-7 validation with full error collection. Used in the ETL validate stage |
| **Testing** | `tests/` – 15 tests covering the DAG engine (cycle detection, failure propagation, diamond DAGs), the full pipeline (happy path, validation rejection, consent blocking, mixed batches), encryption roundtrips, and schema validation |

## Project Structure

```
.
├── app/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── config.py                # Environment-based configuration
│   ├── api/
│   │   └── routes.py            # REST endpoints
│   ├── etl/
│   │   ├── dag.py               # Custom DAG engine
│   │   └── pipeline.py          # Patient ingestion pipeline
│   ├── models/
│   │   ├── database.py          # SQLAlchemy engine & session
│   │   └── patient.py           # All database models
│   ├── schemas/
│   │   ├── api.py               # Pydantic request/response models
│   │   └── fhir.py              # FHIR JSON schemas
│   └── services/
│       ├── audit.py             # Compliance audit logging
│       ├── encryption.py        # PHI/PII encryption
│       └── validation.py        # JSON schema validator
├── tests/
│   ├── test_dag.py              # DAG engine tests
│   ├── test_pipeline.py         # End-to-end pipeline tests
│   ├── test_encryption.py       # Encryption roundtrip tests
│   └── test_validation.py       # Schema validation tests
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```
