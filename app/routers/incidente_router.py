# app/routers/incidente_router.py
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.incidente import (
    IncidenteCreate, IncidenteEstadoUpdate,
    InvestigacionCreate,
    AccionCorrectivaCreate, AccionCorrectivaUpdate
)
from app.services import incidente_service
from app.services import furat_service

router = APIRouter(prefix="/incidentes", tags=["Incidentes"])


# ── Incidentes ────────────────────────────────────────────────────

@router.get("/")
def listar_incidentes(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos los incidentes de la empresa con filtros opcionales."""
    return incidente_service.get_all_incidentes(
        db, current_user.empresa_id, estado, tipo
    )


@router.post("/", status_code=201)
def crear_incidente(
    datos: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un nuevo reporte de incidente. Accesible para SST y Empleados."""
    return incidente_service.create_incidente(
        db, datos, current_user.empresa_id, current_user.id
    )


@router.get("/{incidente_id}")
def obtener_incidente(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna el detalle completo de un incidente."""
    return incidente_service.get_incidente_by_id(
        db, incidente_id, current_user.empresa_id
    )


@router.patch("/{incidente_id}/estado")
def cambiar_estado(
    incidente_id: UUID,
    datos: IncidenteEstadoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Cambia el estado. No permite cerrar sin investigación documentada."""
    return incidente_service.update_estado_incidente(
        db, incidente_id, current_user.empresa_id, datos.estado
    )


@router.get("/{incidente_id}/progreso")
def progreso_incidente(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna el % de acciones correctivas completadas."""
    return incidente_service.get_progreso_incidente(
        db, incidente_id, current_user.empresa_id
    )


@router.get("/{incidente_id}/furat")
def descargar_furat(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Genera y descarga el FURAT en PDF. Solo el Encargado SST."""
    pdf_bytes = furat_service.generar_furat(
        db, incidente_id, current_user.empresa_id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FURAT_{incidente_id}.pdf"
        }
    )


# ── Investigación ─────────────────────────────────────────────────

@router.post("/{incidente_id}/investigacion", status_code=201)
def crear_investigacion(
    incidente_id: UUID,
    datos: InvestigacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    """Crea la investigación de causas. Solo el Encargado SST."""
    return incidente_service.create_investigacion(
        db, incidente_id, current_user.empresa_id, datos
    )


# ── Acciones Correctivas ──────────────────────────────────────────

@router.post("/{incidente_id}/acciones", status_code=201)
def crear_accion_correctiva(
    incidente_id: UUID,
    datos: AccionCorrectivaCreate,
    db: Session = Depends(get_db),
    current