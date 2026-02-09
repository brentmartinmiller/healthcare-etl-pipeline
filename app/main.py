"""
FastAPI application entrypoint.

Run locally:  uvicorn app.main:app --reload
Run in Docker: see docker-compose.yml
"""

import logging

from fastapi import FastAPI

from app.api.routes import router
from app.models.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")

app = FastAPI(
    title="Healthcare ETL Pipeline API",
    description=(
        "Demonstrates backend engineering skills: FastAPI, PostgreSQL, "
        "custom DAG ETL pipelines, PHI/PII encryption, consent-gated access, "
        "and FHIR-compatible data modeling."
    ),
    version="1.0.0",
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
