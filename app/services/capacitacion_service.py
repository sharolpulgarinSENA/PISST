# app/services/capacitacion_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

from app.models.capacitacion import (
    Capacitacion, SesionCapacitacion,
    Asistencia, Evaluacion, Pregunta, RespuestaEmpleado
)
from app.schemas.capacitacion import (
    CapacitacionCreate, SesionCreate, AsistenciaCreate,
    EvaluacionCreate, ResponderEvaluacionRequest
)


# ── Capacitaciones ────────────────────────────────────────────────

def get_all_capacitaciones(db: Session, empresa_id: UUID):
    return db.query(Capacitacion)\
        .filter(Capacitacion.empresa_id == empresa_id,
                Capacitacion.activo == True)\
        .order_by(Capacitacion.fecha_creacion.desc()).all()


def create_capacitacion(db: Session, datos: CapacitacionCreate, empresa_id: UUID):
    capacitacion = Capacitacion(
        titulo=datos.titulo,
        objetivos=datos.objetivos,
        duracion_horas=datos.duracion_horas,
        facilitador_id=datos.facilitador_id,
        empresa_id=empresa_id
    )
    db.add(capacitacion)
    db.commit()
    db.refresh(capacitacion)
    return capacitacion


# ── Sesiones ──────────────────────────────────────────────────────

def create_sesion(db: Session, datos: SesionCreate, empresa_id: UUID):
    # Verificar que la capacitación pertenece a la empresa
    cap = db.query(Capacitacion).filter(
        Capacitacion.id == datos.capacitacion_id,
        Capacitacion.empresa_id == empresa_id
    ).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")

    sesion = SesionCapacitacion(
        fecha=datos.fecha,
        lugar=datos.lugar,
        capacitacion_id=datos.capacitacion_id
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def get_sesiones_by_capacitacion(db: Session, capacitacion_id: UUID, empresa_id: UUID):
    cap = db.query(Capacitacion).filter(
        Capacitacion.id == capacitacion_id,
        Capacitacion.empresa_id == empresa_id
    ).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")
    return cap.sesiones


# ── Asistencia ────────────────────────────────────────────────────

def registrar_asistencia(db: Session, datos: AsistenciaCreate):
    # Verificar si ya existe registro para este empleado en esta sesión
    existe = db.query(Asistencia).filter(
        Asistencia.sesion_id == datos.sesion_id,
        Asistencia.empleado_id == datos.empleado_id
    ).first()

    if existe:
        # Actualizar el estado existente
        existe.estado = datos.estado
        db.commit()
        db.refresh(existe)
        return existe

    asistencia = Asistencia(
        sesion_id=datos.sesion_id,
        empleado_id=datos.empleado_id,
        estado=datos.estado
    )
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)
    return asistencia


def get_asistencia_by_sesion(db: Session, sesion_id: UUID):
    return db.query(Asistencia)\
        .filter(Asistencia.sesion_id == sesion_id).all()


def get_historial_empleado(db: Session, empleado_id: UUID):
    """Retorna el historial de capacitaciones de un empleado."""
    return db.query(Asistencia)\
        .filter(Asistencia.empleado_id == empleado_id)\
        .order_by(Asistencia.fecha_registro.desc()).all()


# ── Evaluaciones ──────────────────────────────────────────────────

def create_evaluacion(db: Session, datos: EvaluacionCreate):
    evaluacion = Evaluacion(
        titulo=datos.titulo,
        puntaje_minimo=datos.puntaje_minimo,
        sesion_id=datos.sesion_id
    )
    db.add(evaluacion)
    db.flush()

    for p in datos.preguntas:
        pregunta = Pregunta(
            texto=p.texto,
            opcion_a=p.opcion_a,
            opcion_b=p.opcion_b,
            opcion_c=p.opcion_c,
            opcion_d=p.opcion_d,
            respuesta_correcta=p.respuesta_correcta,
            evaluacion_id=evaluacion.id
        )
        db.add(pregunta)

    db.commit()
    db.refresh(evaluacion)
    return evaluacion


def responder_evaluacion(db: Session, datos: ResponderEvaluacionRequest,
                         empleado_id: UUID):
    """
    Calcula automáticamente el puntaje del empleado.
    Retorna si aprobó o no según el puntaje mínimo.
    """
    evaluacion = db.query(Evaluacion).filter(
        Evaluacion.id == datos.evaluacion_id
    ).first()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    correctas = 0
    total = len(datos.respuestas)

    for resp in datos.respuestas:
        pregunta = db.query(Pregunta).filter(
            Pregunta.id == resp.pregunta_id
        ).first()
        if not pregunta:
            continue

        es_correcta = pregunta.respuesta_correcta == resp.respuesta_dada

        if es_correcta:
            correctas += 1

        # Guardar cada respuesta
        respuesta = RespuestaEmpleado(
            pregunta_id=resp.pregunta_id,
            evaluacion_id=datos.evaluacion_id,
            empleado_id=empleado_id,
            respuesta_dada=resp.respuesta_dada,
            es_correcta=es_correcta
        )
        db.add(respuesta)

    # Calcular puntaje final
    puntaje = round((correctas / total) * 100) if total > 0 else 0
    aprobado = puntaje >= evaluacion.puntaje_minimo

    db.commit()

    return {
        "evaluacion_id": datos.evaluacion_id,
        "empleado_id": empleado_id,
        "puntaje_final": puntaje,
        "aprobado": aprobado,
        "total_preguntas": total,
        "respuestas_correctas": correctas
    }


def get_cobertura_capacitaciones(db: Session, empresa_id: UUID):
    """
    Calcula el % de cobertura del plan anual de capacitaciones.
    """
    total_capacitaciones = db.query(Capacitacion).filter(
        Capacitacion.empresa_id == empresa_id,
        Capacitacion.activo == True
    ).count()

    if total_capacitaciones == 0:
        return {"total": 0, "con_sesiones": 0, "porcentaje": 0}

    con_sesiones = db.query(Capacitacion).filter(
        Capacitacion.empresa_id == empresa_id,
        Capacitacion.activo == True
    ).join(SesionCapacitacion).distin