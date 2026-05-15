# app/routers/riesgo_router.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.riesgo import (
    PeligroCreate, PeligroResponse,
    EvaluacionRiesgoCreate, EvaluacionRiesgoResponse,
    MedidaControlCreate, MedidaControlUpdate, MedidaControlResponse
)
from app.services import riesgo_service

router = APIRouter(prefix="/riesgos", tags=["Evaluación de Riesgos"])


# ── Peligros ──────────────────────────────────────────────────────

@router.get("/peligros")
def listar_peligros(
    tipo: Optional[str] = None,
    area_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos los peligros identificados con filtros opcionales."""
    return riesgo_service.get_all_peligros(
        db, current_user.empresa_id, tipo, area_id
    )


@router.post("/peligros", status_code=201)
def crear_peligro(
    datos: PeligroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Crea una nueva ficha de peligro. Solo el Encargado SST."""
    return riesgo_service.create_peligro(
        db, datos, current_user.empresa_id
    )


@router.get("/peligros/{peligro_id}")
def obtener_peligro(
    peligro_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna el detalle de un peligro con sus evaluaciones."""
    return riesgo_service.get_peligro_by_id(
        db, peligro_id, current_user.empresa_id
    )


# ── Evaluaciones de Riesgo ────────────────────────────────────────

@router.post("/peligros/{peligro_id}/evaluar", status_code=201)
def evaluar_riesgo(
    peligro_id: UUID,
    datos: EvaluacionRiesgoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """
    Evalúa el nivel de riesgo de un peligro.
    El nivel se calcula automáticamente: probabilidad x severidad.
    """
    return riesgo_service.create_evaluacion_riesgo(
        db, peligro_id, current_user.empresa_id, datos
    )


@router.get("/matriz")
def obtener_matriz_riesgos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia"))
):
    """
    Retorna los datos de la matriz de riesgos agrupados por nivel.
    Bajo / Medio / Alto / Crítico.
    """
    return riesgo_service.get_matriz_riesgos(
        db, current_user.empresa_id
    )


# ── Medidas de Control ────────────────────────────────────────────

@router.post("/peligros/{peligro_id}/controles", status_code=201)
def crear_medida_control(
    peligro_id: UUID,
    datos: MedidaControlCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Crea una medida de control para un peligro."""
    return riesgo_service.create_medida_control(
        db, peligro_id, current_user.empresa_id, datos
    )


@router.patch("/controles/{medida_id}")
def actualizar_medida_control(
    medida_id: UUID,
    datos: MedidaControlUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Actualiza el estado de una medida de control. No cierra sin evidencia."""
    return riesgo_service.update_medida_control(db, medida_id, datos)