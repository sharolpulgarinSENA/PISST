# app/routers/auditoria_router.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.auditoria import (
    AuditoriaCreate,
    AuditoriaResponse,
    HallazgoCreate,
    HallazgoResponse,
    NoConformidadCreate,
    NoConformidadResponse,
    NoConformidadUpdate,
)
from app.services import auditoria_service

router = APIRouter(prefix="/auditorias", tags=["Auditorías Internas"])


# ── Auditorías ────────────────────────────────────────────────────


@router.get("/", response_model=List[AuditoriaResponse])
def listar_auditorias(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    return auditoria_service.get_all_auditorias(
        db, current_user.empresa_id, skip, limit
    )


@router.post("/", response_model=AuditoriaResponse, status_code=201)
def crear_auditoria(
    datos: AuditoriaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Planifica una nueva auditoría interna. Solo el Encargado SST."""
    return auditoria_service.create_auditoria(db, datos, current_user.empresa_id)


@router.patch("/{auditoria_id}/estado", response_model=AuditoriaResponse)
def cambiar_estado_auditoria(
    auditoria_id: UUID,
    estado: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Cambia el estado de la auditoría: planificada → en_ejecucion → completada."""
    return auditoria_service.cambiar_estado_auditoria(
        db, auditoria_id, current_user.empresa_id, estado
    )


@router.get("/{auditoria_id}/progreso")
def progreso_auditoria(
    auditoria_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    """Retorna el % de no conformidades cerradas."""
    return auditoria_service.get_progreso_auditoria(
        db, auditoria_id, current_user.empresa_id
    )


# ── Hallazgos ─────────────────────────────────────────────────────


@router.post(
    "/{auditoria_id}/hallazgos", response_model=HallazgoResponse, status_code=201
)
def crear_hallazgo(
    auditoria_id: UUID,
    datos: HallazgoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Registra un hallazgo durante la ejecución de la auditoría."""
    return auditoria_service.create_hallazgo(
        db, auditoria_id, current_user.empresa_id, datos
    )


@router.get("/{auditoria_id}/hallazgos", response_model=List[HallazgoResponse])
def listar_hallazgos(
    auditoria_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    """Lista todos los hallazgos de una auditoría."""
    return auditoria_service.get_hallazgos_by_auditoria(
        db, auditoria_id, current_user.empresa_id
    )


# ── No Conformidades ──────────────────────────────────────────────


@router.post(
    "/hallazgos/{hallazgo_id}/nc", response_model=NoConformidadResponse, status_code=201
)
def crear_no_conformidad(
    hallazgo_id: UUID,
    datos: NoConformidadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Crea una no conformidad a partir de un hallazgo."""
    return auditoria_service.create_no_conformidad(db, hallazgo_id, datos)


@router.patch("/nc/{nc_id}", response_model=NoConformidadResponse)
def actualizar_no_conformidad(
    nc_id: UUID,
    datos: NoConformidadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Actualiza el estado de una NC. No cierra sin evidencia."""
    return auditoria_service.update_no_conformidad(db, nc_id, datos)
