# app/routers/capacitacion_router.py
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import RoleEnum, User
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
from app.services import capacitacion_service, notificacion_service

router = APIRouter(prefix="/capacitaciones", tags=["Capacitaciones"])


# ── Capacitaciones ────────────────────────────────────────────────


@router.get("/", response_model=List[CapacitacionResponse])
def listar_capacitaciones(
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista capacitaciones de la empresa. ?activo=true (default) | false | sin parámetro = todas."""
    return capacitacion_service.get_all_capacitaciones(
        db, current_user.empresa_id, activo
    )


@router.post("/", response_model=CapacitacionResponse, status_code=201)
def crear_capacitacion(
    datos: CapacitacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Crea un nuevo programa de capacitación. Solo el Encargado SST."""
    cap = capacitacion_service.create_capacitacion(db, datos, current_user.empresa_id)
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="capacitacion_nueva",
        titulo="Nueva capacitación creada",
        descripcion=f"{datos.titulo} agregada al plan anual",
        modulo="capacitaciones",
        url_destino=f"/capacitaciones?capacitacion={cap.id}",
    )
    db.commit()
    return cap


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


@router.post("/sesiones", response_model=SesionResponse, status_code=201)
def crear_sesion(
    datos: SesionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Programa una sesión de capacitación."""
    sesion = capacitacion_service.create_sesion(db, datos, current_user.empresa_id)
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="capacitacion_sesion_programada",
        titulo="Sesión de capacitación programada",
        descripcion=f"Nueva sesión programada para el {datos.fecha.strftime('%d/%m/%Y')}",
        modulo="capacitaciones",
        url_destino=f"/capacitaciones?capacitacion={sesion.capacitacion_id}",
    )
    db.commit()
    return sesion


@router.patch("/sesiones/{sesion_id}/estado", response_model=SesionResponse)
def cambiar_estado_sesion(
    sesion_id: UUID,
    estado: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Cambia el estado de una sesión. Valores: programada, realizada, no_realizada, cancelada."""
    sesion = capacitacion_service.cambiar_estado_sesion(
        db, sesion_id, current_user.empresa_id, estado
    )
    tipos_evento = {
        "realizada": (
            "capacitacion_sesion_realizada",
            "Sesión de capacitación realizada",
        ),
        "cancelada": (
            "capacitacion_sesion_cancelada",
            "Sesión de capacitación cancelada",
        ),
    }
    if estado in tipos_evento:
        tipo, titulo = tipos_evento[estado]
        notificacion_service.crear_notificacion(
            db,
            empresa_id=current_user.empresa_id,
            tipo=tipo,
            titulo=titulo,
            descripcion=f"La sesión fue marcada como {estado}",
            modulo="capacitaciones",
            url_destino=f"/capacitaciones?capacitacion={sesion.capacitacion_id}",
        )
        db.commit()
    return sesion


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
    sesion = capacitacion_service.reprogramar_sesion(
        db, sesion_id, current_user.empresa_id, datos
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="capacitacion_sesion_reprogramada",
        titulo="Sesión de capacitación reprogramada",
        descripcion="Una sesión fue reprogramada",
        modulo="capacitaciones",
        url_destino=f"/capacitaciones?capacitacion={sesion.capacitacion_id}",
    )
    db.commit()
    return sesion


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
    asistencia = capacitacion_service.registrar_asistencia(
        db, datos, current_user.empresa_id
    )
    notificacion_service.crear_notificacion(
        db,
        empresa_id=current_user.empresa_id,
        tipo="capacitacion_asignada",
        titulo="Te han asignado a una capacitación",
        descripcion="Fuiste registrado en una sesión de capacitación. Revisa tu historial.",
        modulo="capacitaciones",
        url_destino="/capacitaciones/historial",
        usuario_id=datos.empleado_id,
    )
    db.commit()
    return asistencia


@router.get("/sesiones/{sesion_id}/asistencia", response_model=list[AsistenciaResponse])
def asistencia_por_sesion(
    sesion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    """Lista la asistencia de todos los empleados en una sesión."""
    return capacitacion_service.get_asistencia_by_sesion(
        db, sesion_id, current_user.empresa_id
    )


@router.get("/empleados/{empleado_id}/historial")
def historial_empleado(
    empleado_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retorna el historial de capacitaciones de un empleado."""
    if current_user.role == RoleEnum.empleado and current_user.id != empleado_id:
        raise HTTPException(status_code=403, detail="No autorizado.")
    return capacitacion_service.get_historial_empleado(
        db, empleado_id, current_user.empresa_id
    )


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
    return capacitacion_service.responder_evaluacion(
        db, datos, current_user.id, current_user.empresa_id
    )


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

    from app.models.user import User as UserModel

    # Empleado solo puede descargar su propio certificado
    if current_user.role == RoleEnum.empleado and current_user.id != empleado_id:
        raise HTTPException(status_code=403, detail="No autorizado.")

    # Verificar que el empleado pertenece a la misma empresa
    empleado = (
        db.query(UserModel)
        .filter(
            UserModel.id == empleado_id,
            UserModel.empresa_id == current_user.empresa_id,
        )
        .first()
    )
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    buffer = capacitacion_service.generar_certificado(db, evaluacion_id, empleado_id)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=certificado_{empleado_id}.pdf"
        },
    )
