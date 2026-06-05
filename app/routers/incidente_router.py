# app/routers/incidente_router.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.incidente import (
    AccionCorrectivaCreate,
    AccionCorrectivaResponse,
    AccionCorrectivaUpdate,
    IncidenteCreate,
    IncidenteEstadoUpdate,
    IncidenteResponse,
    InvestigacionCreate,
    InvestigacionResponse,
    InvestigacionUpdate,
)
from app.services import furat_service, incidente_service

router = APIRouter(prefix="/incidentes", tags=["Incidentes"])


# ── Incidentes ────────────────────────────────────────────────────


@router.get("/", response_model=List[IncidenteResponse])
def listar_incidentes(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return incidente_service.get_all_incidentes(
        db, current_user.empresa_id, estado, tipo, skip, limit
    )


@router.post("/", response_model=IncidenteResponse, status_code=201)
def crear_incidente(
    datos: IncidenteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crea un nuevo reporte de incidente.
    Accesible para SST y Empleados.
    """
    return incidente_service.create_incidente(
        db, datos, current_user.empresa_id, current_user.id
    )


@router.get("/{incidente_id}", response_model=IncidenteResponse)
def obtener_incidente(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna el detalle completo de un incidente."""
    return incidente_service.get_incidente_by_id(
        db, incidente_id, current_user.empresa_id
    )


@router.patch("/{incidente_id}/estado", response_model=IncidenteResponse)
def cambiar_estado(
    incidente_id: UUID,
    datos: IncidenteEstadoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Cambia el estado de un incidente.
    Solo el Encargado SST puede cambiar estados.
    No permite cerrar sin investigación documentada.
    """
    return incidente_service.update_estado_incidente(
        db, incidente_id, current_user.empresa_id, datos.estado
    )


@router.get("/{incidente_id}/progreso")
def progreso_incidente(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna el % de acciones correctivas completadas."""
    return incidente_service.get_progreso_incidente(
        db, incidente_id, current_user.empresa_id
    )


# ── Investigación ─────────────────────────────────────────────────


@router.get("/{incidente_id}/investigacion", response_model=InvestigacionResponse)
def obtener_investigacion(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna la investigación de causas de un incidente. 404 si no existe."""
    return incidente_service.get_investigacion(
        db, incidente_id, current_user.empresa_id
    )


@router.patch("/{incidente_id}/investigacion", response_model=InvestigacionResponse)
def actualizar_investigacion(
    incidente_id: UUID,
    datos: InvestigacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Actualiza los campos enviados de una investigación existente. 404 si no existe."""
    return incidente_service.update_investigacion(
        db, incidente_id, current_user.empresa_id, datos
    )


@router.post(
    "/{incidente_id}/investigacion",
    response_model=InvestigacionResponse,
    status_code=201,
)
def crear_investigacion(
    incidente_id: UUID,
    datos: InvestigacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Crea la investigación de causas de un incidente.
    Solo el Encargado SST puede crear investigaciones.
    """
    return incidente_service.create_investigacion(
        db, incidente_id, current_user.empresa_id, datos
    )


# ── Acciones Correctivas ──────────────────────────────────────────


@router.get("/{incidente_id}/acciones", response_model=List[AccionCorrectivaResponse])
def listar_acciones_correctivas(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna todas las acciones correctivas de un incidente. [] si no hay."""
    return incidente_service.get_acciones_correctivas(
        db, incidente_id, current_user.empresa_id
    )


@router.post(
    "/{incidente_id}/acciones", response_model=AccionCorrectivaResponse, status_code=201
)
def crear_accion_correctiva(
    incidente_id: UUID,
    datos: AccionCorrectivaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Crea una acción correctiva para un incidente."""
    return incidente_service.create_accion_correctiva(
        db, incidente_id, current_user.empresa_id, datos
    )


@router.patch("/acciones/{accion_id}", response_model=AccionCorrectivaResponse)
def actualizar_accion_correctiva(
    accion_id: UUID,
    datos: AccionCorrectivaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Actualiza una acción correctiva.
    No permite cerrarla sin evidencia documentada.
    """
    return incidente_service.update_accion_correctiva(
        db, accion_id, current_user.empresa_id, datos
    )


@router.get("/{incidente_id}/furat")
def descargar_furat(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Genera y descarga el FURAT en PDF.
    Solo el Encargado SST puede generar el FURAT.
    """
    pdf_bytes = furat_service.generar_furat(db, incidente_id, current_user.empresa_id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=FURAT_{incidente_id}.pdf"
        },
    )
