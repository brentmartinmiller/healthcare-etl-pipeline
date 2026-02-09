"""Audit logging service for compliance tracking."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.patient import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    *,
    actor: str,
    action: str,
    resource_type: str,
    resource_id: UUID,
    detail: dict[str, Any] | None = None,
) -> None:
    """Write an immutable audit log entry."""
    entry = AuditLog(
        actor=actor,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
    )
    db.add(entry)
    db.flush()
    logger.info("AUDIT: %s %s %s/%s", actor, action, resource_type, resource_id)
