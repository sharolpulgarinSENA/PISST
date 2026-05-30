# app/routers/capacitacion_router.py
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.capacitacion import (
    AsistenciaCreate,
    AsistenciaResponse,
    CapacitacionCreate,
    CapacitacionResponse,
    CapacitacionUpdate,
    EvaluacionCreate,
    EvaluacionResponse,
    ResponderEvaluacionRequest,
    ResultadoEvaluacionResponse,
    SesionCreate,
    SesionResponse,
    SesionUpdate,
)
from app.services import capacitacion_service

router = APIRouter(prefix="/capacitaciones", tags=["Capacitaciones"])


# ── Capacitaciones ────────────────────────────────────────────────


@router.get("/")
def listar_capacitaciones(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Lista todas las capacitaciones de la empresa."""
    return capacitacion_service.get_all_capacitaciones(db, current_user.empresa_id)


@router.post("/", status_code=201)
def crear_capacitacion(
    datos: CapacitacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Crea un nuevo programa de capacitación. Solo el Encargado SST."""
    return capacitacion_service.create_capacitacion(db, datos, current_user.empresa_id)


@router.patch("/{capacitacion_id}", response_model=CapacitacionResponse)
def actualizar_capacitacion(
    capacitacion_id: UUID,
    datos: CapacitacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Actualiza una capacitación — puede suspender/activar,
    cambiar título, objetivos o duración.
    """
    return capacitacion_service.update_capacitacion(
        db, capacitacion_id, current_user.empresa_id, datos
    )


@router.get("/cobertura")
def cobertura_capacitaciones(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia")),
):
    """Retorna el % de cobertura del plan anual de capacitaciones."""
    return capacitacion_service.get_cobertura_capacitaciones(
        db, current_user.empresa_id
    )


# ── Sesiones ──────────────────────────────────────────────────────


@router.post("/sesiones", status_code=201)
def crear_sesion(
    datos: SesionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Programa una sesión de capacitación."""
    return capacitacion_service.create_sesion(db, datos, current_user.empresa_id)


@router.patch("/sesiones/{sesion_id}", response_model=SesionResponse)
def reprogramar_sesion(
    sesion_id: UUID,
    datos: SesionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Reprograma una sesión de capacitación.
    Puede cambiar fecha, lugar o ambos.
    """
    return capacitacion_service.reprogramar_sesion(
        db, sesion_id, current_user.empresa_id, datos
    )


@router.get("/{capacitacion_id}/sesiones")
def listar_sesiones(
    capacitacion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las sesiones de una capacitación."""
    return capacitacion_service.get_sesiones_by_capacitacion(
        db, capacitacion_id, current_user.empresa_id
    )


# ── Asistencia ────────────────────────────────────────────────────


@router.post("/asistencia", response_model=AsistenciaResponse, status_code=201)
def registrar_asistencia(
    datos: AsistenciaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """
    Registra o actualiza la asistencia de un empleado a una sesión.
    Estados: presente, ausente, justificado.
    """
    return capacitacion_service.registrar_asistencia(db, datos)


@router.get("/sesiones/{sesion_id}/asistencia", response_model=list[AsistenciaResponse])
def asistencia_por_sesion(
    sesion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Lista la asistencia de todos los empleados en una sesión."""
    return capacitacion_service.get_asistencia_by_sesion(db, sesion_id)


@router.get("/empleados/{empleado_id}/historial")
def historial_empleado(
    empleado_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Retorna el historial de capacitaciones de un empleado."""
    return capacitacion_service.get_historial_empleado(db, empleado_id)


# ── Evaluaciones ──────────────────────────────────────────────────


@router.post("/evaluaciones", response_model=EvaluacionResponse, status_code=201)
def crear_evaluacion(
    datos: EvaluacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Crea una evaluación con sus preguntas de opción múltiple."""
    return capacitacion_service.create_evaluacion(db, datos)


@router.post("/evaluaciones/responder", response_model=ResultadoEvaluacionResponse)
def responder_evaluacion(
    datos: ResponderEvaluacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    El empleado responde la evaluación.
    El sistema calcula automáticamente el puntaje y si aprobó.
    """
    return capacitacion_service.responder_evaluacion(db, datos, current_user.id)


# ── Certificados ──────────────────────────────────────────────────


@router.get("/evaluaciones/{evaluacion_id}/certificado/{empleado_id}")
def descargar_certificado(
    evaluacion_id: UUID,
    empleado_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Descarga el certificado PDF de aprobación de una evaluación.
    Solo disponible si el empleado aprobó.
    """
    from fastapi.responses import StreamingResponse

    buffer = capacitacion_service.generar_certificado(db, evaluacion_id, empleado_id)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificado_{empleado_id}.pdf"
        },
    )
