# app/services/capacitacion_service.py
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.capacitacion import (
    Asistencia,
    Capacitacion,
    Evaluacion,
    Pregunta,
    RespuestaEmpleado,
    SesionCapacitacion,
    capacitacion_areas,
)
from app.models.user import User
from app.schemas.capacitacion import (
    AsistenciaCreate,
    CapacitacionCreate,
    EvaluacionCreate,
    ResponderEvaluacionRequest,
    SesionCreate,
)

# ── Capacitaciones ────────────────────────────────────────────────


def get_all_capacitaciones(db: Session, empresa_id: UUID, activo: bool | None = None):
    query = db.query(Capacitacion).filter(Capacitacion.empresa_id == empresa_id)
    if activo is not None:
        query = query.filter(Capacitacion.activo == activo)
    return query.order_by(Capacitacion.fecha_creacion.desc()).all()


def create_capacitacion(db: Session, datos: CapacitacionCreate, empresa_id: UUID):
    from app.models.area import Area

    capacitacion = Capacitacion(
        titulo=datos.titulo,
        objetivos=datos.objetivos,
        duracion_horas=datos.duracion_horas,
        facilitador_id=datos.facilitador_id,
        empresa_id=empresa_id,
    )
    db.add(capacitacion)
    db.flush()

    if datos.area_ids:
        areas = db.query(Area).filter(Area.id.in_(datos.area_ids)).all()
        capacitacion.areas = areas

    db.commit()
    db.refresh(capacitacion)
    return capacitacion


def update_capacitacion(db: Session, capacitacion_id: UUID, empresa_id: UUID, datos):
    cap = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.id == capacitacion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )

    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")

    if datos.activo is not None:
        cap.activo = datos.activo
    if datos.titulo is not None:
        cap.titulo = datos.titulo
    if datos.objetivos is not None:
        cap.objetivos = datos.objetivos
    if datos.duracion_horas is not None:
        cap.duracion_horas = datos.duracion_horas
    if datos.area_ids is not None:
        from app.models.area import Area

        cap.areas = db.query(Area).filter(Area.id.in_(datos.area_ids)).all()

    db.commit()
    db.refresh(cap)
    return cap


def toggle_capacitacion(
    db: Session, capacitacion_id: UUID, empresa_id: UUID, activo: bool
):
    cap = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.id == capacitacion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )

    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")

    cap.activo = activo
    db.commit()
    db.refresh(cap)
    return cap


ESTADOS_SESION_VALIDOS = {"programada", "realizada", "no_realizada", "cancelada"}

# ── Sesiones ──────────────────────────────────────────────────────


def create_sesion(db: Session, datos: SesionCreate, empresa_id: UUID):
    cap = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.id == datos.capacitacion_id,
            Capacitacion.empresa_id == empresa_id,
        )
        .first()
    )
    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")

    sesion = SesionCapacitacion(
        fecha=datos.fecha, lugar=datos.lugar, capacitacion_id=datos.capacitacion_id
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


def get_sesiones_by_capacitacion(db: Session, capacitacion_id: UUID, empresa_id: UUID):
    cap = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.id == capacitacion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )
    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")
    return cap.sesiones


def reprogramar_sesion(db: Session, sesion_id: UUID, empresa_id: UUID, datos):
    sesion = (
        db.query(SesionCapacitacion)
        .join(Capacitacion)
        .filter(
            SesionCapacitacion.id == sesion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    if sesion.estado != "programada":
        raise HTTPException(
            status_code=400,
            detail="Solo se pueden reprogramar sesiones en estado 'programada'",
        )

    if datos.fecha is not None:
        sesion.fecha = datos.fecha
    if datos.lugar is not None:
        sesion.lugar = datos.lugar

    db.commit()
    db.refresh(sesion)
    return sesion


def cambiar_estado_sesion(db: Session, sesion_id: UUID, empresa_id: UUID, estado: str):
    if estado not in ESTADOS_SESION_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Estado inválido. Valores permitidos: {sorted(ESTADOS_SESION_VALIDOS)}",
        )

    sesion = (
        db.query(SesionCapacitacion)
        .join(Capacitacion)
        .filter(
            SesionCapacitacion.id == sesion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )

    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    sesion.estado = estado
    db.commit()
    db.refresh(sesion)
    return sesion


# ── Asistencia ────────────────────────────────────────────────────


def registrar_asistencia(db: Session, datos: AsistenciaCreate, empresa_id: UUID):
    # Verificar que la sesión pertenece a la empresa
    sesion = (
        db.query(SesionCapacitacion)
        .join(SesionCapacitacion.capacitacion)
        .filter(
            SesionCapacitacion.id == datos.sesion_id,
            Capacitacion.empresa_id == empresa_id,
        )
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    # Verificar que el empleado pertenece a la empresa
    empleado = (
        db.query(User)
        .filter(User.id == datos.empleado_id, User.empresa_id == empresa_id)
        .first()
    )
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    existe = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == datos.sesion_id,
            Asistencia.empleado_id == datos.empleado_id,
        )
        .first()
    )

    if existe:
        existe.estado = datos.estado
        db.commit()
        db.refresh(existe)
        return existe

    asistencia = Asistencia(
        sesion_id=datos.sesion_id, empleado_id=datos.empleado_id, estado=datos.estado
    )
    db.add(asistencia)
    db.commit()
    db.refresh(asistencia)
    return asistencia


def get_asistencia_by_sesion(db: Session, sesion_id: UUID, empresa_id: UUID):
    sesion = (
        db.query(SesionCapacitacion)
        .join(SesionCapacitacion.capacitacion)
        .filter(
            SesionCapacitacion.id == sesion_id,
            Capacitacion.empresa_id == empresa_id,
        )
        .first()
    )
    if not sesion:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return db.query(Asistencia).filter(Asistencia.sesion_id == sesion_id).all()


def get_historial_empleado(db: Session, empleado_id: UUID, empresa_id: UUID):
    empleado = (
        db.query(User)
        .filter(User.id == empleado_id, User.empresa_id == empresa_id)
        .first()
    )
    if not empleado:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    if not empleado.area_id:
        return []

    # Todas las capacitaciones del área del empleado, en esta empresa
    cap_ids_en_area = select(capacitacion_areas.c.capacitacion_id).where(
        capacitacion_areas.c.area_id == empleado.area_id
    )
    capacitaciones = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.empresa_id == empresa_id,
            Capacitacion.id.in_(cap_ids_en_area),
        )
        .order_by(Capacitacion.fecha_creacion.desc())
        .all()
    )

    historial = []

    for cap in capacitaciones:
        if not cap.sesiones:
            historial.append(
                {
                    "capacitacion_id": str(cap.id),
                    "capacitacion_nombre": cap.titulo,
                    "capacitacion_activo": cap.activo,
                    "fecha_sesion": None,
                    "sesion_estado": None,
                    "evaluacion_id": None,
                    "evaluacion": None,
                    "resultado": None,
                }
            )
            continue

        for sesion in cap.sesiones:
            # Asistencia de este empleado en esta sesión (puede ser None)
            asistencia = next(
                (a for a in sesion.asistencias if a.empleado_id == empleado_id),
                None,
            )

            evaluacion = sesion.evaluaciones[0] if sesion.evaluaciones else None
            evaluacion_data = None
            resultado_data = None

            if evaluacion:
                evaluacion_data = {
                    "id": str(evaluacion.id),
                    "titulo": evaluacion.titulo,
                    "puntaje_minimo": evaluacion.puntaje_minimo,
                    "preguntas": [
                        {
                            "id": str(p.id),
                            "texto": p.texto,
                            "opciones": [
                                {"clave": "a", "texto": p.opcion_a},
                                {"clave": "b", "texto": p.opcion_b},
                                {"clave": "c", "texto": p.opcion_c},
                                {"clave": "d", "texto": p.opcion_d},
                            ],
                        }
                        for p in evaluacion.preguntas
                    ],
                }

                if asistencia:
                    respuestas = (
                        db.query(RespuestaEmpleado)
                        .filter(
                            RespuestaEmpleado.evaluacion_id == evaluacion.id,
                            RespuestaEmpleado.empleado_id == empleado_id,
                        )
                        .all()
                    )
                    if respuestas:
                        resultado_data = {
                            "puntaje_final": respuestas[0].puntaje_final,
                            "aprobado": respuestas[0].aprobado,
                            "total_preguntas": len(respuestas),
                            "respuestas_correctas": sum(
                                1 for r in respuestas if r.es_correcta
                            ),
                        }

            historial.append(
                {
                    "capacitacion_id": str(cap.id),
                    "capacitacion_nombre": cap.titulo,
                    "capacitacion_activo": cap.activo,
                    "fecha_sesion": sesion.fecha,
                    "sesion_estado": sesion.estado if sesion.estado else None,
                    "evaluacion_id": str(evaluacion.id) if evaluacion else None,
                    "evaluacion": evaluacion_data,
                    "resultado": resultado_data,
                }
            )

    return historial


# ── Evaluaciones ──────────────────────────────────────────────────


def create_evaluacion(db: Session, datos: EvaluacionCreate):
    evaluacion = Evaluacion(
        titulo=datos.titulo,
        puntaje_minimo=datos.puntaje_minimo,
        sesion_id=datos.sesion_id,
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
            evaluacion_id=evaluacion.id,
        )
        db.add(pregunta)

    db.commit()
    db.refresh(evaluacion)
    return evaluacion


def responder_evaluacion(
    db: Session, datos: ResponderEvaluacionRequest, empleado_id: UUID, empresa_id: UUID
):
    evaluacion = (
        db.query(Evaluacion)
        .join(Evaluacion.sesion)
        .join(SesionCapacitacion.capacitacion)
        .filter(
            Evaluacion.id == datos.evaluacion_id,
            Capacitacion.empresa_id == empresa_id,
        )
        .first()
    )
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluación no encontrada")

    correctas = 0
    total = len(datos.respuestas)

    for resp in datos.respuestas:
        pregunta = db.query(Pregunta).filter(Pregunta.id == resp.pregunta_id).first()
        if not pregunta:
            continue

        opciones_map = {
            "a": pregunta.opcion_a,
            "b": pregunta.opcion_b,
            "c": pregunta.opcion_c,
            "d": pregunta.opcion_d,
        }
        texto_correcto = opciones_map.get(pregunta.respuesta_correcta, "")
        respuesta_norm = resp.respuesta_dada.strip().lower()
        es_correcta = (
            respuesta_norm == pregunta.respuesta_correcta
            or respuesta_norm == texto_correcto.strip().lower()
        )
        if es_correcta:
            correctas += 1

        respuesta = RespuestaEmpleado(
            pregunta_id=resp.pregunta_id,
            evaluacion_id=datos.evaluacion_id,
            empleado_id=empleado_id,
            respuesta_dada=resp.respuesta_dada,
            es_correcta=es_correcta,
        )
        db.add(respuesta)

    puntaje = round((correctas / total) * 100) if total > 0 else 0
    aprobado = puntaje >= evaluacion.puntaje_minimo

    db.commit()

    db.query(RespuestaEmpleado).filter(
        RespuestaEmpleado.evaluacion_id == datos.evaluacion_id,
        RespuestaEmpleado.empleado_id == empleado_id,
    ).update({"puntaje_final": puntaje, "aprobado": aprobado})
    db.commit()

    return {
        "evaluacion_id": datos.evaluacion_id,
        "empleado_id": empleado_id,
        "puntaje_final": puntaje,
        "aprobado": aprobado,
        "total_preguntas": total,
        "respuestas_correctas": correctas,
    }


def get_cobertura_capacitaciones(db: Session, empresa_id: UUID):
    total = (
        db.query(Capacitacion)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .count()
    )

    if total == 0:
        return {"total": 0, "completadas": 0, "porcentaje": 0}

    completadas = (
        db.query(Capacitacion)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .join(SesionCapacitacion)
        .filter(SesionCapacitacion.estado == "realizada")
        .distinct()
        .count()
    )

    porcentaje = round((completadas / total) * 100)
    return {
        "total": total,
        "completadas": completadas,
        "porcentaje": porcentaje,
    }


# ── Certificados ──────────────────────────────────────────────────


def generar_certificado(db: Session, evaluacion_id: UUID, empleado_id: UUID):
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    resultado = (
        db.query(RespuestaEmpleado)
        .filter(
            RespuestaEmpleado.evaluacion_id == evaluacion_id,
            RespuestaEmpleado.empleado_id == empleado_id,
            RespuestaEmpleado.aprobado == True,
        )
        .first()
    )

    if not resultado:
        raise HTTPException(
            status_code=404,
            detail="El empleado no ha aprobado esta evaluación o no existe el registro",
        )

    evaluacion = db.query(Evaluacion).filter(Evaluacion.id == evaluacion_id).first()
    empleado = db.query(User).filter(User.id == empleado_id).first()
    sesion = (
        db.query(SesionCapacitacion)
        .filter(SesionCapacitacion.id == evaluacion.sesion_id)
        .first()
    )
    capacitacion = sesion.capacitacion

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()

    def estilo(nombre, size, color, bold=False, after=12):
        return ParagraphStyle(
            nombre,
            parent=styles["Normal"],
            fontSize=size,
            textColor=colors.HexColor(color),
            alignment=TA_CENTER,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            spaceAfter=after,
        )

    fecha_str = resultado.fecha_respuesta.strftime("%d de %B de %Y")

    contenido = [
        Spacer(1, 0.3 * inch),
        Paragraph("PISST", estilo("t1", 32, "#1E3A5F", bold=True, after=4)),
        Paragraph(
            "Plataforma Integral de Seguridad y Salud en el Trabajo",
            estilo("t2", 11, "#666666", after=20),
        ),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee")),
        Spacer(1, 0.4 * inch),
        Paragraph(
            "CERTIFICADO DE APROBACIÓN",
            estilo("t3", 16, "#1E3A5F", bold=True, after=24),
        ),
        Paragraph(
            "Este certificado se otorga a:", estilo("t4", 13, "#444444", after=8)
        ),
        Paragraph(empleado.nombre, estilo("t5", 26, "#1d4ed8", bold=True, after=8)),
        Paragraph(
            "por haber completado y aprobado satisfactoriamente la capacitación:",
            estilo("t6", 13, "#444444", after=8),
        ),
        Paragraph(
            capacitacion.titulo, estilo("t7", 14, "#1E3A5F", bold=True, after=20)
        ),
        HRFlowable(width="60%", thickness=1, color=colors.HexColor("#1d4ed8")),
        Spacer(1, 0.3 * inch),
        Paragraph(
            f"Evaluación: {evaluacion.titulo}", estilo("t8", 11, "#444444", after=6)
        ),
        Paragraph(
            f"Puntaje obtenido: <b>{resultado.puntaje_final}%</b>",
            estilo("t9", 11, "#444444", after=6),
        ),
        Paragraph(
            f"Puntaje mínimo requerido: {evaluacion.puntaje_minimo}%",
            estilo("t10", 11, "#444444", after=6),
        ),
        Paragraph(
            f"Fecha de aprobación: {fecha_str}", estilo("t11", 11, "#444444", after=24)
        ),
        Spacer(1, 0.4 * inch),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee")),
        Spacer(1, 0.2 * inch),
        Paragraph(
            "PISST — Sistema de Gestión de Seguridad y Salud en el Trabajo",
            estilo("t12", 10, "#999999", after=4),
        ),
        Paragraph(
            "Este documento es generado automáticamente por el sistema.",
            estilo("t13", 10, "#999999", after=0),
        ),
    ]

    doc.build(contenido)
    buffer.seek(0)
    return buffer
