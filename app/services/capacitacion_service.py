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


def delete_capacitacion(db: Session, capacitacion_id: UUID, empresa_id: UUID):
    cap = (
        db.query(Capacitacion)
        .filter(
            Capacitacion.id == capacitacion_id, Capacitacion.empresa_id == empresa_id
        )
        .first()
    )
    if not cap:
        raise HTTPException(status_code=404, detail="Capacitación no encontrada")

    tiene_asistencia = (
        db.query(Asistencia)
        .join(SesionCapacitacion, SesionCapacitacion.id == Asistencia.sesion_id)
        .filter(SesionCapacitacion.capacitacion_id == capacitacion_id)
        .first()
        is not None
    )
    if tiene_asistencia:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar una capacitación con asistencia registrada. Suspéndela en su lugar.",
        )

    db.delete(cap)
    db.commit()


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


def registrar_asistencia_propia(
    db: Session, sesion_id: UUID, empleado_id: UUID, empresa_id: UUID
):
    from datetime import datetime, timezone

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

    if sesion.estado != "programada":
        raise HTTPException(
            status_code=400,
            detail="Solo puedes confirmar asistencia en sesiones programadas",
        )

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    if sesion.fecha.date() != ahora.date():
        raise HTTPException(
            status_code=400,
            detail="Solo puedes confirmar asistencia el día de la sesión",
        )

    existe = (
        db.query(Asistencia)
        .filter(
            Asistencia.sesion_id == sesion_id,
            Asistencia.empleado_id == empleado_id,
        )
        .first()
    )
    if existe:
        raise HTTPException(
            status_code=400, detail="Ya tienes asistencia registrada en esta sesión"
        )

    asistencia = Asistencia(
        sesion_id=sesion_id, empleado_id=empleado_id, estado="presente"
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
                    "sesion_id": None,
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
                    "sesion_id": str(sesion.id),
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
    from reportlab.lib.pagesizes import landscape, letter
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

    # Fecha en español
    MESES = {
        1: "enero",
        2: "febrero",
        3: "marzo",
        4: "abril",
        5: "mayo",
        6: "junio",
        7: "julio",
        8: "agosto",
        9: "septiembre",
        10: "octubre",
        11: "noviembre",
        12: "diciembre",
    }
    fecha_obj = resultado.fecha_respuesta
    fecha_str = f"{fecha_obj.day} de {MESES[fecha_obj.month]} de {fecha_obj.year}"

    # ── Paleta ────────────────────────────────────────────────────
    NAVY = colors.HexColor("#1B3A5C")
    BLUE = colors.HexColor("#2563EB")
    ACCENT = colors.HexColor("#0EA5E9")
    GOLD = colors.HexColor("#B8860B")
    WHITE = colors.white
    MUTED = colors.HexColor("#64748B")
    TEXT = colors.HexColor("#1E293B")

    W, H = landscape(letter)  # 11 x 8.5 in

    # ── Decoración de página con canvas ──────────────────────────
    def decorar(canvas_obj, doc_obj):
        canvas_obj.saveState()

        # Fondo crema muy suave
        canvas_obj.setFillColor(colors.HexColor("#FFFDF7"))
        canvas_obj.rect(0, 0, W, H, fill=True, stroke=False)

        # Borde exterior dorado grueso
        canvas_obj.setStrokeColor(GOLD)
        canvas_obj.setLineWidth(4)
        canvas_obj.rect(18, 18, W - 36, H - 36, fill=False, stroke=True)

        # Borde interior dorado fino
        canvas_obj.setLineWidth(1)
        canvas_obj.rect(26, 26, W - 52, H - 52, fill=False, stroke=True)

        # Banda superior navy
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(26, H - 80, W - 52, 54, fill=True, stroke=False)

        # Línea de acento celeste debajo de la banda
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(26, H - 84, W - 52, 4, fill=True, stroke=False)

        # PISST en la banda
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 20)
        canvas_obj.drawCentredString(W / 2, H - 52, "PISST")
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.setFillColor(colors.HexColor("#A0C4E8"))
        canvas_obj.drawCentredString(
            W / 2, H - 67, "Plataforma Integral de Seguridad y Salud en el Trabajo"
        )

        # Banda inferior navy
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(26, 26, W - 52, 48, fill=True, stroke=False)

        # Línea de acento sobre banda inferior
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(26, 74, W - 52, 3, fill=True, stroke=False)

        # Texto footer en banda inferior
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#CBD5E1"))
        canvas_obj.drawCentredString(
            W / 2,
            56,
            "Certificado generado automáticamente por PISST — "
            "Sistema de Gestión de Seguridad y Salud en el Trabajo",
        )
        canvas_obj.setFillColor(colors.HexColor("#64748B"))
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawCentredString(
            W / 2,
            40,
            f"ID de evaluación: {str(evaluacion_id)[:8]}...  |  "
            f"Resolución 0312 de 2019 — Decreto 1072 de 2015",
        )

        # Ornamentos en esquinas (pequeños rombos dorados)
        canvas_obj.setFillColor(GOLD)
        for x, y in [(28, H - 82), (W - 30, H - 82), (28, 76), (W - 30, 76)]:
            canvas_obj.circle(x, y, 4, fill=True, stroke=False)

        canvas_obj.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.9 * inch,
        leftMargin=0.9 * inch,
        topMargin=1.25 * inch,
        bottomMargin=1.0 * inch,
    )
    styles = getSampleStyleSheet()

    def s(nombre, size, color, bold=False, after=10, before=0):
        return ParagraphStyle(
            nombre,
            parent=styles["Normal"],
            fontSize=size,
            textColor=color,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            spaceAfter=after,
            spaceBefore=before,
            leading=size * 1.4,
        )

    contenido = [
        Spacer(1, 0.15 * inch),
        # Título del certificado
        Paragraph(
            "CERTIFICADO DE APROBACIÓN",
            s("h1", 22, NAVY, bold=True, after=6),
        ),
        Paragraph(
            "SG-SST — Seguridad y Salud en el Trabajo",
            s("h2", 10, MUTED, after=20),
        ),
        # Línea decorativa dorada
        HRFlowable(width="50%", thickness=2, color=GOLD, spaceAfter=16, spaceBefore=0),
        # Otorgado a
        Paragraph(
            "Este certificado se otorga a:",
            s("sub", 11, MUTED, after=6),
        ),
        # Nombre del empleado
        Paragraph(
            empleado.nombre,
            s("nombre", 30, NAVY, bold=True, after=10),
        ),
        # Cargo si existe
        Paragraph(
            empleado.cargo.nombre if empleado.cargo else "",
            s("cargo", 10, MUTED, after=14),
        ),
        Paragraph(
            "por haber completado y aprobado satisfactoriamente la capacitación:",
            s("desc", 11, TEXT, after=8),
        ),
        # Título de la capacitación
        Paragraph(
            capacitacion.titulo,
            s("cap", 15, BLUE, bold=True, after=20),
        ),
        # Línea separadora
        HRFlowable(width="60%", thickness=1, color=ACCENT, spaceAfter=16),
        # Detalles en línea
        Paragraph(
            f"<b>Evaluación:</b> {evaluacion.titulo}&nbsp;&nbsp;&nbsp;"
            f"<b>Puntaje obtenido:</b> {resultado.puntaje_final}%&nbsp;&nbsp;&nbsp;"
            f"<b>Puntaje mínimo:</b> {evaluacion.puntaje_minimo}%&nbsp;&nbsp;&nbsp;"
            f"<b>Fecha:</b> {fecha_str}",
            s("detalles", 9.5, MUTED, after=0),
        ),
    ]

    doc.build(contenido, onFirstPage=decorar, onLaterPages=decorar)
    buffer.seek(0)
    return buffer
