# app/services/analytics_service.py
from datetime import date, datetime
from typing import Optional
from uuid import UUID

import pandas as pd
from sqlalchemy import case, func
from sqlalchemy.orm import Session, joinedload

from app.models.auditoria import Auditoria, Hallazgo, NoConformidad
from app.models.capacitacion import (
    Asistencia,
    Capacitacion,
    Evaluacion,
    RespuestaEmpleado,
    SesionCapacitacion,
)
from app.models.incidente import EstadoIncidenteEnum, Incidente
from app.models.riesgo import EstadoControlEnum, MedidaControl, Peligro


def analizar_incidentes(
    db: Session,
    empresa_id: UUID,
    limit: int = 1000,
    offset: int = 0,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict:
    base = [Incidente.empresa_id == empresa_id]
    if fecha_desde:
        base.append(
            Incidente.fecha >= datetime.combine(fecha_desde, datetime.min.time())
        )
    if fecha_hasta:
        base.append(
            Incidente.fecha <= datetime.combine(fecha_hasta, datetime.max.time())
        )

    # Total — SQL COUNT, nunca carga objetos
    total = db.query(func.count(Incidente.id)).filter(*base).scalar() or 0

    if total == 0:
        return {
            "total_incidentes": 0,
            "por_tipo": {},
            "por_severidad": {},
            "tasa_mensual_promedio": 0.0,
            "top_areas": [],
            "tendencia": "sin_datos",
        }

    # Distribuciones — SQL GROUP BY
    por_tipo = {
        r[0].value: r[1]
        for r in db.query(Incidente.tipo, func.count(Incidente.id))
        .filter(*base)
        .group_by(Incidente.tipo)
        .all()
    }
    por_severidad = {
        r[0].value: r[1]
        for r in db.query(Incidente.severidad, func.count(Incidente.id))
        .filter(*base)
        .group_by(Incidente.severidad)
        .all()
    }

    # Tendencia — solo fechas, con límite para evitar cargar todo en RAM
    fechas = [
        r[0]
        for r in db.query(Incidente.fecha)
        .filter(*base)
        .order_by(Incidente.fecha.desc())
        .limit(limit)
        .offset(offset)
        .all()
    ]

    df = pd.DataFrame({"fecha": pd.to_datetime(fechas)})
    meses_activos = df["fecha"].dt.to_period("M").nunique()
    tasa_mensual = round(total / max(meses_activos, 1), 1)

    ultimo_mes = df["fecha"].max().to_period("M")
    mes_anterior = ultimo_mes - 1
    cnt_ultimo = int((df["fecha"].dt.to_period("M") == ultimo_mes).sum())
    cnt_anterior = int((df["fecha"].dt.to_period("M") == mes_anterior).sum())
    if cnt_anterior == 0:
        tendencia = "estable"
    elif cnt_ultimo > cnt_anterior * 1.2:
        tendencia = "aumento"
    elif cnt_ultimo < cnt_anterior * 0.8:
        tendencia = "baja"
    else:
        tendencia = "estable"

    return {
        "total_incidentes": total,
        "por_tipo": por_tipo,
        "por_severidad": por_severidad,
        "tasa_mensual_promedio": tasa_mensual,
        "top_areas": [],
        "tendencia": tendencia,
    }


def analizar_riesgos(
    db: Session,
    empresa_id: UUID,
    limit: int = 1000,
    offset: int = 0,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict:
    base = [Peligro.empresa_id == empresa_id]
    if fecha_desde:
        base.append(
            Peligro.fecha_creacion >= datetime.combine(fecha_desde, datetime.min.time())
        )
    if fecha_hasta:
        base.append(
            Peligro.fecha_creacion <= datetime.combine(fecha_hasta, datetime.max.time())
        )

    # Total real — SQL COUNT
    total = db.query(func.count(Peligro.id)).filter(*base).scalar() or 0

    if total == 0:
        return {
            "total_peligros": 0,
            "por_nivel": {},
            "por_tipo": {},
            "pct_con_control_implementado": 0.0,
            "criticos_sin_control": 0,
        }

    # Distribución por tipo — SQL GROUP BY
    por_tipo = {
        r[0].value: r[1]
        for r in db.query(Peligro.tipo, func.count(Peligro.id))
        .filter(*base)
        .group_by(Peligro.tipo)
        .all()
    }

    # Peligros con evaluación — joinedload evita N+1, limit acota RAM
    peligros = (
        db.query(Peligro)
        .options(joinedload(Peligro.evaluaciones))
        .filter(*base)
        .limit(limit)
        .offset(offset)
        .all()
    )
    ids_peligros = [p.id for p in peligros]

    # Nivel por peligro (última evaluación no-residual) — UUID como clave
    niveles: dict = {}
    for p in peligros:
        ev_iniciales = [e for e in p.evaluaciones if not e.es_residual]
        if ev_iniciales:
            mas_reciente = max(ev_iniciales, key=lambda e: e.fecha_evaluacion)
            niveles[p.id] = mas_reciente.nivel_riesgo.value
        else:
            niveles[p.id] = "sin_evaluar"

    por_nivel: dict[str, int] = {}
    for nivel in niveles.values():
        por_nivel[nivel] = por_nivel.get(nivel, 0) + 1

    # % con medida completada — SQL COUNT DISTINCT
    con_control = (
        db.query(func.count(func.distinct(MedidaControl.peligro_id)))
        .filter(
            MedidaControl.peligro_id.in_(ids_peligros),
            MedidaControl.estado == EstadoControlEnum.completada,
        )
        .scalar()
        or 0
    )
    pct_control = round(con_control / len(peligros) * 100, 1) if peligros else 0.0

    # Críticos sin ninguna medida — SQL con UUID
    criticos_ids = [p_id for p_id, nv in niveles.items() if nv == "critico"]
    if criticos_ids:
        criticos_con_medida = (
            db.query(func.count(func.distinct(MedidaControl.peligro_id)))
            .filter(MedidaControl.peligro_id.in_(criticos_ids))
            .scalar()
            or 0
        )
        criticos_sin_control = len(criticos_ids) - criticos_con_medida
    else:
        criticos_sin_control = 0

    return {
        "total_peligros": total,
        "por_nivel": por_nivel,
        "por_tipo": por_tipo,
        "pct_con_control_implementado": pct_control,
        "criticos_sin_control": criticos_sin_control,
    }


def analizar_capacitaciones(
    db: Session,
    empresa_id: UUID,
    limit: int = 1000,
    offset: int = 0,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict:
    # Total capacitaciones activas — SQL COUNT
    total_cap = (
        db.query(func.count(Capacitacion.id))
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .scalar()
        or 0
    )

    if total_cap == 0:
        return {
            "total_evaluaciones": 0,
            "tasa_aprobacion_pct": 0.0,
            "asistencia_promedio_pct": 0.0,
            "alertas_asistencia": [],
            "capacitaciones_sin_sesion_realizada": 0,
        }

    # Tasa aprobación — SQL JOIN + COUNT
    total_resp = (
        db.query(func.count(RespuestaEmpleado.id))
        .join(Evaluacion, Evaluacion.id == RespuestaEmpleado.evaluacion_id)
        .join(SesionCapacitacion, SesionCapacitacion.id == Evaluacion.sesion_id)
        .join(Capacitacion, Capacitacion.id == SesionCapacitacion.capacitacion_id)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .scalar()
        or 0
    )

    aprobados = (
        db.query(func.count(RespuestaEmpleado.id))
        .join(Evaluacion, Evaluacion.id == RespuestaEmpleado.evaluacion_id)
        .join(SesionCapacitacion, SesionCapacitacion.id == Evaluacion.sesion_id)
        .join(Capacitacion, Capacitacion.id == SesionCapacitacion.capacitacion_id)
        .filter(
            Capacitacion.empresa_id == empresa_id,
            Capacitacion.activo == True,
            RespuestaEmpleado.aprobado == True,
        )
        .scalar()
        or 0
    )

    tasa_aprobacion = round(aprobados / total_resp * 100, 1) if total_resp else 0.0

    # Asistencia por empleado — SQL GROUP BY, sin pandas
    asistencia_q = (
        db.query(
            Asistencia.empleado_id,
            func.count(Asistencia.id).label("total"),
            func.sum(case((Asistencia.estado == "presente", 1), else_=0)).label(
                "presentes"
            ),
        )
        .join(SesionCapacitacion, SesionCapacitacion.id == Asistencia.sesion_id)
        .join(Capacitacion, Capacitacion.id == SesionCapacitacion.capacitacion_id)
        .filter(
            Capacitacion.empresa_id == empresa_id,
            SesionCapacitacion.estado == "realizada",
        )
    )
    if fecha_desde:
        asistencia_q = asistencia_q.filter(
            SesionCapacitacion.fecha
            >= datetime.combine(fecha_desde, datetime.min.time())
        )
    if fecha_hasta:
        asistencia_q = asistencia_q.filter(
            SesionCapacitacion.fecha
            <= datetime.combine(fecha_hasta, datetime.max.time())
        )
    asistencia_rows = asistencia_q.group_by(Asistencia.empleado_id).all()

    if not asistencia_rows:
        asistencia_promedio = 0.0
        alertas: list = []
    else:
        pcts = [r.presentes / r.total * 100 for r in asistencia_rows if r.total > 0]
        asistencia_promedio = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
        alertas = [
            {
                "empleado_id": str(r.empleado_id),
                "asistencia_pct": round(r.presentes / r.total * 100, 1),
            }
            for r in asistencia_rows
            if r.total > 0 and r.presentes / r.total < 0.8
        ]

    # Capacitaciones sin sesión realizada — SQL
    cap_con_sesion = (
        db.query(func.count(func.distinct(SesionCapacitacion.capacitacion_id)))
        .join(Capacitacion, Capacitacion.id == SesionCapacitacion.capacitacion_id)
        .filter(
            Capacitacion.empresa_id == empresa_id,
            Capacitacion.activo == True,
            SesionCapacitacion.estado == "realizada",
        )
        .scalar()
        or 0
    )
    sin_sesion = total_cap - cap_con_sesion

    return {
        "total_evaluaciones": total_resp,
        "tasa_aprobacion_pct": tasa_aprobacion,
        "asistencia_promedio_pct": asistencia_promedio,
        "alertas_asistencia": alertas,
        "capacitaciones_sin_sesion_realizada": sin_sesion,
    }


def calcular_cumplimiento(
    db: Session,
    empresa_id: UUID,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> dict:
    """
    Score SG-SST (0–100) basado en 4 componentes con peso igual (25 c/u).
    100% SQL — no carga objetos en memoria.
    """
    scores: dict[str, float] = {}

    desde_dt = (
        datetime.combine(fecha_desde, datetime.min.time()) if fecha_desde else None
    )
    hasta_dt = (
        datetime.combine(fecha_hasta, datetime.max.time()) if fecha_hasta else None
    )

    # 1. Incidentes investigados (estado != borrador)
    inc_base = [Incidente.empresa_id == empresa_id]
    if desde_dt:
        inc_base.append(Incidente.fecha >= desde_dt)
    if hasta_dt:
        inc_base.append(Incidente.fecha <= hasta_dt)

    total_inc = db.query(func.count(Incidente.id)).filter(*inc_base).scalar() or 0
    investigados = (
        db.query(func.count(Incidente.id))
        .filter(*inc_base, Incidente.estado != EstadoIncidenteEnum.borrador)
        .scalar()
        or 0
    )
    scores["incidentes_investigados"] = (
        round(investigados / total_inc * 100, 1) if total_inc else 0.0
    )

    # 2. Peligros con medida de control completada
    peligro_base = [Peligro.empresa_id == empresa_id, Peligro.activo == True]
    if desde_dt:
        peligro_base.append(Peligro.fecha_creacion >= desde_dt)
    if hasta_dt:
        peligro_base.append(Peligro.fecha_creacion <= hasta_dt)

    total_peligros = (
        db.query(func.count(Peligro.id)).filter(*peligro_base).scalar() or 0
    )
    peligros_con_control = (
        db.query(func.count(func.distinct(MedidaControl.peligro_id)))
        .join(Peligro, Peligro.id == MedidaControl.peligro_id)
        .filter(*peligro_base, MedidaControl.estado == EstadoControlEnum.completada)
        .scalar()
        or 0
    )
    scores["peligros_con_control"] = (
        round(peligros_con_control / total_peligros * 100, 1) if total_peligros else 0.0
    )

    # 3. Capacitaciones activas con al menos una sesión realizada
    cap_base = [Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True]
    if desde_dt:
        cap_base.append(Capacitacion.fecha_creacion >= desde_dt)
    if hasta_dt:
        cap_base.append(Capacitacion.fecha_creacion <= hasta_dt)

    total_cap = db.query(func.count(Capacitacion.id)).filter(*cap_base).scalar() or 0
    cap_con_sesion = (
        db.query(func.count(func.distinct(SesionCapacitacion.capacitacion_id)))
        .join(Capacitacion, Capacitacion.id == SesionCapacitacion.capacitacion_id)
        .filter(*cap_base, SesionCapacitacion.estado == "realizada")
        .scalar()
        or 0
    )
    scores["capacitaciones_realizadas"] = (
        round(cap_con_sesion / total_cap * 100, 1) if total_cap else 0.0
    )

    # 4. No conformidades cerradas
    nc_base = [Auditoria.empresa_id == empresa_id]
    if desde_dt:
        nc_base.append(NoConformidad.fecha_creacion >= desde_dt)
    if hasta_dt:
        nc_base.append(NoConformidad.fecha_creacion <= hasta_dt)

    total_nc = (
        db.query(func.count(NoConformidad.id))
        .join(Hallazgo, Hallazgo.id == NoConformidad.hallazgo_id)
        .join(Auditoria, Auditoria.id == Hallazgo.auditoria_id)
        .filter(*nc_base)
        .scalar()
        or 0
    )
    cerradas_nc = (
        db.query(func.count(NoConformidad.id))
        .join(Hallazgo, Hallazgo.id == NoConformidad.hallazgo_id)
        .join(Auditoria, Auditoria.id == Hallazgo.auditoria_id)
        .filter(*nc_base, NoConformidad.estado == "cerrada")
        .scalar()
        or 0
    )
    scores["no_conformidades_cerradas"] = (
        round(cerradas_nc / total_nc * 100, 1) if total_nc else 0.0
    )

    valores = list(scores.values())
    score_total = round(sum(valores) / len(valores), 1) if valores else 0.0

    return {"score_total": score_total, "desglose": scores}
