# app/routers/auditoria_router.py
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_or_api_key, require_role
from app.models.user import User
from app.schemas.auditoria import (
    AuditoriaCreate,
    AuditoriaResponse,
    HallazgoCreate,
    HallazgoResponse,
    HallazgoUpdate,
    NoConformidadCreate,
    NoConformidadResponse,
    NoConformidadUpdate,
)
from app.services import auditoria_service, notificacion_service

router = APIRouter(prefix="/auditorias", tags=["Auditorías Internas"])


# ── Cron job: verificar auditorías y NC vencidas ──────────────────


@router.post("/verificar-vencidas")
def verificar_vencidas(
    db: Session = Depends(get_db),
    _=Depends(require_admin_or_api_key),
):
    """
    Endpoint para cron job diario. Detecta auditorías y NC vencidas.
    Acepta autenticación via Bearer JWT (role=admin) o header X-API-Key.
    """
    return auditoria_service.verificar_auditorias_vencidas(db)


# ── Auditorías ────────────────────────────────────────────────────


@router.get("/", response_model=List[AuditoriaResponse])
def listar_auditorias(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
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
    auditoria = auditoria_service.create_auditoria(db, datos, current_user.empresa_id)
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="auditoria_nueva",
        titulo="Nueva auditoría planificada",
        descripcion=f"Auditoría programada para el {datos.fecha_programada.strftime('%d/%m/%Y')}",
        modulo="auditorias",
        url_destino=f"/auditorias?auditoria={auditoria.id}",
    )
    db.commit()
    return auditoria


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
    hallazgo = auditoria_service.create_hallazgo(
        db, auditoria_id, current_user.empresa_id, datos
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="hallazgo_nuevo",
        titulo="Nuevo hallazgo registrado",
        descripcion=f"Hallazgo ({datos.clasificacion}): {datos.descripcion[:80]}",
        modulo="auditorias",
        url_destino=f"/auditorias?auditoria={auditoria_id}&hallazgo=1",
    )
    db.commit()
    return hallazgo


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


@router.patch("/hallazgos/{hallazgo_id}", response_model=HallazgoResponse)
def actualizar_hallazgo(
    hallazgo_id: UUID,
    datos: HallazgoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Edita un hallazgo (ej. corregir clasificación o descripción)."""
    return auditoria_service.update_hallazgo(
        db, hallazgo_id, current_user.empresa_id, datos
    )


@router.delete("/hallazgos/{hallazgo_id}", status_code=204)
def eliminar_hallazgo(
    hallazgo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Elimina un hallazgo. No permitido si tiene No Conformidades asociadas."""
    auditoria_service.delete_hallazgo(db, hallazgo_id, current_user.empresa_id)


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
    return auditoria_service.create_no_conformidad(
        db, hallazgo_id, datos, current_user.empresa_id
    )


@router.patch("/nc/{nc_id}", response_model=NoConformidadResponse)
def actualizar_no_conformidad(
    nc_id: UUID,
    datos: NoConformidadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Actualiza el estado de una NC. No cierra sin evidencia."""
    return auditoria_service.update_no_conformidad(
        db, nc_id, datos, current_user.empresa_id
    )
