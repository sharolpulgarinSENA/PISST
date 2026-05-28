# app/services/audit_service.py
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.models.audit_log import AuditLog


def registrar_auditoria(
    db: Session,
    accion: str,
    entidad: str,
    user_id: Optional[UUID] = None,
    entidad_id: Optional[str] = None,
    detalle: Optional[str] = None,
):
    log = AuditLog(
        user_id=user_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
    )
    db.add(log)
