# app/routers/incidente_router.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
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
from app.services import furat_service, incidente_service, notificacion_service

router = APIRouter(prefix="/incidentes", tags=["Incidentes"])


# ── Incidentes ────────────────────────────────────────────────────


@router.get("/", response_model=List[IncidenteResponse])
def listar_incidentes(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incidentes = incidente_service.get_all_incidentes(
        db, current_user.empresa_id, estado, tipo, skip, limit
    )
    return [IncidenteResponse.from_orm_with_creator(i) for i in incidentes]


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
    incidente = incidente_service.create_incidente(
        db, datos, current_user.empresa_id, current_user.id
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="reporte_nuevo",
        titulo="Nuevo reporte de empleado",
        descripcion=f"{current_user.nombre} reportó un incidente",
        modulo="reportes",
        url_destino=f"/incidentes?reporte={incidente.id}",
    )
    db.commit()
    return incidente


@router.get("/{incidente_id}", response_model=IncidenteResponse)
def obtener_incidente(
    incidente_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna el detalle completo de un incidente."""
    incidente = incidente_service.get_incidente_by_id(
        db, incidente_id, current_user.empresa_id
    )
    return IncidenteResponse.from_orm_with_creator(incidente)


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
    incidente = incidente_service.update_estado_incidente(
        db, incidente_id, current_user.empresa_id, datos.estado
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="reporte_estado_cambio",
        titulo="Estado de reporte actualizado",
        descripcion=f"El incidente cambió a estado: {datos.estado}",
        modulo="reportes",
        url_destino=f"/incidentes?reporte={incidente_id}",
    )
    db.commit()
    return incidente


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
    investigacion = incidente_service.create_investigacion(
        db, incidente_id, current_user.empresa_id, datos
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="investigacion_completada",
        titulo="Investigación de incidente completada",
        descripcion="Se completó la investigación de causas de un incidente",
        modulo="incidentes",
        url_destino=f"/incidentes?reporte={incidente_id}&tab=investigacion",
    )
    db.commit()
    return investigacion


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
    accion = incidente_service.create_accion_correctiva(
        db, incidente_id, current_user.empresa_id, datos
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="accion_correctiva_nueva",
        titulo="Nueva acción correctiva",
        descripcion=f"Acción correctiva registrada: {datos.descripcion[:80]}",
        modulo="incidentes",
        url_destino=f"/incidentes?reporte={incidente_id}&tab=acciones",
    )
    db.commit()
    return accion


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
    accion = incidente_service.update_accion_correctiva(
        db, accion_id, current_user.empresa_id, datos
    )
    if datos.estado == "completada":
        notificacion_service.crear_notificacion(
            db,
            empresa_id=current_user.empresa_id,
            tipo="accion_correctiva_completada",
            titulo="Acción correctiva completada",
            descripcion="Una acción correctiva fue marcada como completada",
            modulo="incidentes",
            url_destino=f"/incidentes?reporte={accion.incidente_id}&tab=acciones",
        )
        db.commit()
    return accion


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
