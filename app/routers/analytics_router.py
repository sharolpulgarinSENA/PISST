# app/routers/analytics_router.py
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/incidentes")
def analytics_incidentes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
    limit: int = Query(default=1000, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
):
    """Distribución de incidentes por tipo y severidad. Tasa mensual y tendencia."""
    return analytics_service.analizar_incidentes(
        db,
        current_user.empresa_id,
        limit=limit,
        offset=offset,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get("/riesgos")
def analytics_riesgos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
    limit: int = Query(default=1000, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Distribución de peligros por nivel de riesgo. % con medidas implementadas."""
    return analytics_service.analizar_riesgos(
        db, current_user.empresa_id, limit=limit, offset=offset
    )


@router.get("/capacitaciones")
def analytics_capacitaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
    limit: int = Query(default=1000, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    fecha_desde: Optional[date] = Query(default=None),
    fecha_hasta: Optional[date] = Query(default=None),
):
    """Tasa de aprobación, asistencia promedio y alertas de empleados < 80%."""
    return analytics_service.analizar_capacitaciones(
        db,
        current_user.empresa_id,
        limit=limit,
        offset=offset,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
    )


@router.get("/cumplimiento")
def analytics_cumplimiento(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    """Score SG-SST (0–100) y desglose por módulo."""
    return analytics_service.calcular_cumplimiento(db, current_user.empresa_id)
