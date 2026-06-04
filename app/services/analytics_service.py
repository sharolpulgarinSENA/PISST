# app/services/analytics_service.py
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria, NoConformidad
from app.models.capacitacion import (
    Asistencia,
    Capacitacion,
    RespuestaEmpleado,
    SesionCapacitacion,
)
from app.models.incidente import Incidente
from app.models.riesgo import MedidaControl, Peligro


def analizar_incidentes(db: Session, empresa_id: UUID) -> dict:
    registros = db.query(Incidente).filter(Incidente.empresa_id == empresa_id).all()

    if not registros:
        return {
            "total_incidentes": 0,
            "por_tipo": {},
            "por_severidad": {},
            "tasa_mensual_promedio": 0.0,
            "top_areas": [],
            "tendencia": "sin_datos",
        }

    df = pd.DataFrame(
        [
            {
                "tipo": r.tipo.value,
                "severidad": r.severidad.value,
                "estado": r.estado.value,
                "fecha": r.fecha,
            }
            for r in registros
        ]
    )

    df["fecha"] = pd.to_datetime(df["fecha"])

    por_tipo = df["tipo"].value_counts().to_dict()
    por_severidad = df["severidad"].value_counts().to_dict()
    meses_activos = df["fecha"].dt.to_period("M").nunique()
    tasa_mensual = round(len(df) / max(meses_activos, 1), 1)

    # Tendencia: último mes vs mes anterior (±20%)
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

    # Top 3 áreas — a través de lesiones (join se hace en el router si se necesita área)
    # Por ahora se deja como lista vacía hasta tener el join con lesiones
    top_areas: list = []

    return {
        "total_incidentes": len(df),
        "por_tipo": por_tipo,
        "por_severidad": por_severidad,
        "tasa_mensual_promedio": tasa_mensual,
        "top_areas": top_areas,
        "tendencia": tendencia,
    }


def analizar_riesgos(db: Session, empresa_id: UUID) -> dict:
    peligros = db.query(Peligro).filter(Peligro.empresa_id == empresa_id).all()

    if not peligros:
        return {
            "total_peligros": 0,
            "por_nivel": {},
            "por_tipo": {},
            "pct_con_control_implementado": 0.0,
            "criticos_sin_control": 0,
        }

    ids_peligros = [p.id for p in peligros]

    controles = (
        db.query(MedidaControl).filter(MedidaControl.peligro_id.in_(ids_peligros)).all()
    )

    df_p = pd.DataFrame(
        [{"peligro_id": str(p.id), "tipo": p.tipo.value} for p in peligros]
    )

    # Nivel de riesgo desde la evaluación más reciente (no residual)
    niveles = {}
    for p in peligros:
        ev_iniciales = [e for e in p.evaluaciones if not e.es_residual]
        if ev_iniciales:
            mas_reciente = max(ev_iniciales, key=lambda e: e.fecha_evaluacion)
            niveles[str(p.id)] = mas_reciente.nivel_riesgo.value
        else:
            niveles[str(p.id)] = "sin_evaluar"

    df_p["nivel"] = df_p["peligro_id"].map(niveles)

    por_nivel = df_p["nivel"].value_counts().to_dict()
    por_tipo = df_p["tipo"].value_counts().to_dict()

    # % con medidas completadas
    peligros_con_control = {
        str(c.peligro_id) for c in controles if c.estado.value == "completada"
    }
    total = len(peligros)
    pct_control = (
        round(len(peligros_con_control) / total * 100, 1) if total > 0 else 0.0
    )

    # Críticos sin ninguna medida
    ids_con_alguna_medida = {str(c.peligro_id) for c in controles}
    criticos_sin_control = int(
        df_p[
            (df_p["nivel"] == "critico")
            & (~df_p["peligro_id"].isin(ids_con_alguna_medida))
        ].shape[0]
    )

    return {
        "total_peligros": total,
        "por_nivel": por_nivel,
        "por_tipo": por_tipo,
        "pct_con_control_implementado": pct_control,
        "criticos_sin_control": criticos_sin_control,
    }


def analizar_capacitaciones(db: Session, empresa_id: UUID) -> dict:
    capacitaciones = (
        db.query(Capacitacion)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .all()
    )

    if not capacitaciones:
        return {
            "total_evaluaciones": 0,
            "tasa_aprobacion_pct": 0.0,
            "asistencia_promedio_pct": 0.0,
            "alertas_asistencia": [],
            "capacitaciones_sin_sesion_realizada": 0,
        }

    ids_cap = [c.id for c in capacitaciones]

    # Sesiones realizadas
    sesiones_realizadas = (
        db.query(SesionCapacitacion)
        .filter(
            SesionCapacitacion.capacitacion_id.in_(ids_cap),
            SesionCapacitacion.estado == "realizada",
        )
        .all()
    )

    ids_sesiones_realizadas = [s.id for s in sesiones_realizadas]

    # Asistencias en sesiones realizadas
    asistencias = []
    if ids_sesiones_realizadas:
        asistencias = (
            db.query(Asistencia)
            .filter(Asistencia.sesion_id.in_(ids_sesiones_realizadas))
            .all()
        )

    # Tasa de aprobación (todas las evaluaciones de la empresa)
    todas_sesiones = (
        db.query(SesionCapacitacion)
        .filter(SesionCapacitacion.capacitacion_id.in_(ids_cap))
        .all()
    )
    ids_todas_sesiones = [s.id for s in todas_sesiones]

    respuestas = []
    if ids_todas_sesiones:
        from app.models.capacitacion import Evaluacion

        evaluaciones = (
            db.query(Evaluacion)
            .filter(Evaluacion.sesion_id.in_(ids_todas_sesiones))
            .all()
        )
        ids_evaluaciones = [e.id for e in evaluaciones]
        if ids_evaluaciones:
            respuestas = (
                db.query(RespuestaEmpleado)
                .filter(RespuestaEmpleado.evaluacion_id.in_(ids_evaluaciones))
                .all()
            )

    # Tasa de aprobación
    if not respuestas:
        total_evaluaciones = 0
        tasa_aprobacion = 0.0
    else:
        df_resp = pd.DataFrame(
            [
                {"empleado_id": str(r.empleado_id), "aprobado": r.aprobado}
                for r in respuestas
            ]
        )
        total_evaluaciones = len(df_resp)
        tasa_aprobacion = round(float(df_resp["aprobado"].mean() * 100), 1)

    # Asistencia promedio y alertas
    if not asistencias:
        asistencia_promedio = 0.0
        alertas = []
    else:
        df_asi = pd.DataFrame(
            [
                {
                    "empleado_id": str(a.empleado_id),
                    "presente": 1 if a.estado == "presente" else 0,
                }
                for a in asistencias
            ]
        )

        por_empleado = (
            df_asi.groupby("empleado_id")["presente"]
            .agg(["sum", "count"])
            .reset_index()
        )
        por_empleado["pct"] = np.round(
            por_empleado["sum"] / por_empleado["count"] * 100, 1
        )

        asistencia_promedio = round(float(por_empleado["pct"].mean()), 1)

        df_alertas = por_empleado[por_empleado["pct"] < 80]
        alertas = [
            {"empleado_id": row["empleado_id"], "asistencia_pct": row["pct"]}
            for _, row in df_alertas.iterrows()
        ]

    # Capacitaciones sin sesión realizada
    ids_con_sesion = {s.capacitacion_id for s in sesiones_realizadas}
    sin_sesion = len([c for c in capacitaciones if c.id not in ids_con_sesion])

    return {
        "total_evaluaciones": total_evaluaciones,
        "tasa_aprobacion_pct": tasa_aprobacion,
        "asistencia_promedio_pct": asistencia_promedio,
        "alertas_asistencia": alertas,
        "capacitaciones_sin_sesion_realizada": sin_sesion,
    }


def calcular_cumplimiento(db: Session, empresa_id: UUID) -> dict:
    """
    Score SG-SST (0–100) basado en 4 componentes con peso igual (25 c/u):
    1. % incidentes investigados (estado != 'borrador')
    2. % peligros con medida de control completada
    3. % capacitaciones activas con al menos una sesión realizada
    4. % no conformidades cerradas
    """
    scores = {}

    # 1. Incidentes investigados
    incidentes = db.query(Incidente).filter(Incidente.empresa_id == empresa_id).all()
    if incidentes:
        investigados = sum(1 for i in incidentes if i.estado.value != "borrador")
        scores["incidentes_investigados"] = round(
            investigados / len(incidentes) * 100, 1
        )
    else:
        scores["incidentes_investigados"] = 0.0

    # 2. Peligros con control implementado
    peligros = (
        db.query(Peligro)
        .filter(Peligro.empresa_id == empresa_id, Peligro.activo == True)
        .all()
    )
    if peligros:
        ids_peligros = [p.id for p in peligros]
        controles_impl = (
            db.query(MedidaControl)
            .filter(
                MedidaControl.peligro_id.in_(ids_peligros),
                MedidaControl.estado == "completada",
            )
            .all()
        )
        ids_con_control = {c.peligro_id for c in controles_impl}
        scores["peligros_con_control"] = round(
            len(ids_con_control) / len(peligros) * 100, 1
        )
    else:
        scores["peligros_con_control"] = 0.0

    # 3. Capacitaciones con sesión realizada
    capacitaciones = (
        db.query(Capacitacion)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .all()
    )
    if capacitaciones:
        ids_cap = [c.id for c in capacitaciones]
        sesiones_reali = (
            db.query(SesionCapacitacion)
            .filter(
                SesionCapacitacion.capacitacion_id.in_(ids_cap),
                SesionCapacitacion.estado == "realizada",
            )
            .all()
        )
        ids_cap_con_sesion = {s.capacitacion_id for s in sesiones_reali}
        scores["capacitaciones_realizadas"] = round(
            len(ids_cap_con_sesion) / len(capacitaciones) * 100, 1
        )
    else:
        scores["capacitaciones_realizadas"] = 0.0

    # 4. No conformidades cerradas
    no_conformidades = (
        db.query(NoConformidad)
        .join(NoConformidad.hallazgo)
        .join(NoConformidad.hallazgo.property.mapper.class_.auditoria)
        .filter(Auditoria.empresa_id == empresa_id)
        .all()
    )
    if no_conformidades:
        cerradas = sum(1 for nc in no_conformidades if nc.estado.value == "cerrada")
        scores["no_conformidades_cerradas"] = round(
            cerradas / len(no_conformidades) * 100, 1
        )
    else:
        scores["no_conformidades_cerradas"] = 0.0

    score_total = round(float(np.mean(list(scores.values()))), 1)

    return {
        "score_total": score_total,
        "desglose": scores,
    }
