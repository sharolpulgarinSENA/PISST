# app/services/capacitacion_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID
from datetime import datetime

from app.models.capacitacion import (
    Capacitacion, SesionCapacitacion,
    Asistencia, Evaluacion, Pregunta, RespuestaEmpleado
)
from app.models.user import User
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
    existe = db.query(Asistencia).filter(
        Asistencia.sesion_id == datos.sesion_id,
        Asistencia.empleado_id == datos.empleado_id
    ).first()

    if existe:
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

        respuesta = RespuestaEmpleado(
            pregunta_id=resp.pregunta_id,
            evaluacion_id=datos.evaluacion_id,
            empleado_id=empleado_id,
            respuesta_dada=resp.respuesta_dada,
            es_correcta=es_correcta
        )
        db.add(respuesta)

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
    total_capacitaciones = db.query(Capacitacion).filter(
        Capacitacion.empresa_id == empresa_id,
        Capacitacion.activo == True
    ).count()

    if total_capacitaciones == 0:
        return {"total": 0, "con_sesiones": 0, "porcentaje": 0}

    con_sesiones = db.query(Capacitacion).filter(
        Capacitacion.empresa_id == empresa_id,
        Capacitacion.activo == True
    ).join(SesionCapacitacion).distinct().count()

    porcentaje = round((con_sesiones / total_capacitaciones) * 100)
    return {
        "total": total_capacitaciones,
        "con_sesiones": con_sesiones,
        "porcentaje": porcentaje
    }


# ── Certificados ──────────────────────────────────────────────────

def generar_certificado(db: Session, evaluacion_id: UUID, empleado_id: UUID):
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER

    resultado = db.query(RespuestaEmpleado).filter(
        RespuestaEmpleado.evaluacion_id == evaluacion_id,
        RespuestaEmpleado.empleado_id == empleado_id,
        RespuestaEmpleado.aprobado == True
    ).first()

    if not resultado:
        raise HTTPException(
            status_code=404,
            detail="El empleado no ha aprobado esta evaluación o no existe el registro"
        )

    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    empleado = db.query(User).filter(User.id == empleado_id).first()
    sesion = db.query(SesionCapacitacion).filter(
        SesionCapacitacion.id == evaluacion.sesion_id
    ).first()
    capacitacion = sesion.capacitacion

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch, leftMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()

    def estilo(nombre, size, color, bold=False, after=12):
        return ParagraphStyle(nombre, parent=styles['Normal'],
                              fontSize=size,
                              textColor=colors.HexColor(color),
                              alignment=TA_CENTER,
                              fontName='Helvetica-Bold' if bold else 'Helvetica',
                              spaceAfter=after)

    fecha_str = resultado.fecha_respuesta.strftime("%d de %B de %Y")

    contenido = [
        Spacer(1, 0.3 * inch),
        Paragraph("PISST", estilo('t1', 32, '#1E3A5F', bold=True, after=4)),
        Paragraph("Plataforma Integral de Seguridad y Salud en el Trabajo",
                  estilo('t2', 11, '#666666', after=20)),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#eeeeee')),
        Spacer(1, 0.4 * inch),
        Paragraph("CERTIFICADO DE APROBACIÓN",
                  estilo('t3', 16, '#1E3A5F', bold=True, after=24)),
        Paragraph("Este certificado se otorga a:", estilo('t4', 13, '#444444', after=8)),
        Paragraph(empleado.nombre, estilo('t5', 26, '#1d4ed8', bold=True, after=8)),
        Paragraph("por haber completado y aprobado satisfactoriamente la capacitación:",
                  estilo('t6', 13, '#444444', after=8)),
        Paragraph(capacitacion.titulo, estilo('t7', 14, '#1E3A5F', bold=True, after=20)),
        HRFlowable(width="60%", thickness=1, color=colors.HexColor('#1d4ed8')),
        Spacer(1, 0.3 * inch),
        Paragraph(f"Evaluación: {evaluacion.titulo}", estilo('t8', 11, '#444444', after=6)),
        Paragraph(f"Puntaje obtenido: <b>{resultado.puntaje_final}%</b>",
                  estilo('t9', 11, '#444444', after=6)),
        Paragraph(f"Puntaje mínimo requerido: {evaluacion.puntaje_minimo}%",
                  estilo('t10', 11, '#444444', after=6)),
        Paragraph(f"Fecha de aprobación: {fecha_str}",
                  estilo('t11', 11, '#444444', after=24)),
        Spacer(1, 0.4 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor('#eeeeee')),
        Spacer(1, 0.2 * inch),
        Paragraph("PISST — Sistema de Gestión de Seguridad y Salud en el Trabajo",
                  estilo('t12', 10, '#999999', after=4)),
        Paragraph("Este documento es generado automáticamente por el sistema.",
                  estilo('t13', 10, '#999999', after=0)),
    ]

    doc.build(contenido)
    buffer.seek(0)
    return buffer
