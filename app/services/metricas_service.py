# app/services/metricas_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime, timedelta

from app.models.incidente import Incidente, EstadoIncidenteEnum
from app.models.accion_correctiva import AccionCorrectiva
from app.models.capacitacion import Capacitacion, SesionCapacitacion, Asistencia
from app.models.user import User


def get_kpis(db: Session, empresa_id: UUID):
    """
    Calcula los KPIs principales del SG-SST.
    Tasa de Accidentalidad = (N° accidentes / N° trabajadores) x 100
    Índice de Frecuencia  = (N° accidentes / horas trabajadas) x 1.000.000
    Índice de Severidad   = (días perdidos / horas trabajadas) x 1.000.000
    """
    # Total de trabajadores activos
    total_trabajadores = db.query(User).filter(
        User.empresa_id == empresa_id,
        User.activo == True,
        User.role == "empleado"
    ).count()

    # Total de accidentes del año actual
    inicio_anio = datetime(datetime.utcnow().year, 1, 1)
    total_accidentes = db.query(Incidente).filter(
        Incidente.empresa_id == empresa_id,
        Incidente.tipo == "accidente",
        Incidente.fecha >= inicio_anio
    ).count()

    # Días perdidos por incapacidad
    from app.models.lesion import Lesion
    dias_perdidos_result = db.query(func.sum(Lesion.incapacidad_dias))\
        .join(Incidente, Lesion.incidente_id == Incidente.id)\
        .filter(
            Incidente.empresa_id == empresa_id,
            Incidente.fecha >= inicio_anio
        ).scalar()
    dias_perdidos = dias_perdidos_result or 0

    # Horas trabajadas estimadas (trabajadores x 8 horas x días laborables)
    dias_transcurridos = (datetime.utcnow() - inicio_anio).days
    horas_trabajadas = total_trabajadores * 8 * dias_transcurridos if total_trabajadores > 0 else 1

    # Cálculos
    tasa_accidentalidad = round((total_accidentes / total_trabajadores) * 100, 2) \
        if total_trabajadores > 0 else 0
    indice_frecuencia = round((total_accidentes / horas_trabajadas) * 1000000, 2) \
        if horas_trabajadas > 0 else 0
    indice_severidad = round((dias_perdidos / horas_trabajadas) * 1000000, 2) \
        if horas_trabajadas > 0 else 0

    return {
        "total_trabajadores": total_trabajadores,
        "total_accidentes": total_accidentes,
        "dias_perdidos": dias_perdidos,
        "tasa_accidentalidad": tasa_accidentalidad,
        "indice_frecuencia": indice_frecuencia,
        "indice_severidad": indice_severidad
    }


def get_dashboard_gerencia(db: Session, empresa_id: UUID):
    """
    Resumen ejecutivo para el rol Gerencia.
    Solo lectura — sin datos sensibles.
    """
    kpis = get_kpis(db, empresa_id)

    # Incidentes activos (no cerrados)
    incidentes_activos = db.query(Incidente).filter(
        Incidente.empresa_id == empresa_id,
        Incidente.estado != EstadoIncidenteEnum.cerrado
    ).count()

    # Incidentes del último mes
    hace_un_mes = datetime.utcnow() - timedelta(days=30)
    incidentes_ultimo_mes = db.query(Incidente).filter(
        Incidente.empresa_id == empresa_id,
        Incidente.fecha_creacion >= hace_un_mes
    ).count()

    # Capacitaciones activas
    total_capacitaciones = db.query(Capacitacion).filter(
        Capacitacion.empresa_id == empresa_id,
        Capacitacion.activo == True
    ).count()

    # Acciones correctivas vencidas
    acciones_vencidas = db.query(AccionCorrectiva)\
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)\
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != "completada",
            AccionCorrectiva.fecha_limite < datetime.utcnow()
        ).count()

    # Calcular % cumplimiento SG-SST
    # Basado en: acciones completadas vs total
    total_acciones = db.query(AccionCorrectiva)\
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)\
        .filter(Incidente.empresa_id == empresa_id).count()

    acciones_completadas = db.query(AccionCorrectiva)\
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)\
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado == "completada"
        ).count()

    cumplimiento = round((acciones_completadas / total_acciones) * 100) \
        if total_acciones > 0 else 100

    return {
        "cumplimiento_sgsst": cumplimiento,
        "incidentes_activos": incidentes_activos,
        "incidentes_ultimo_mes": incidentes_ultimo_mes,
        "total_capacitaciones": total_capacitaciones,
        "acciones_vencidas": acciones_vencidas,
        "kpis": kpis
    }


def get_alertas(db: Session, empresa_id: UUID):
    """
    Retorna alertas activas para el Encargado SST.
    """
    alertas = []

    # Incidentes sin investigación abierta
    sin_investigacion = db.query(Incidente).filter(
        Incidente.empresa_id == empresa_id,
        Incidente.estado == "abierto",
        Incidente.investigacion == None
    ).count()

    if sin_investigacion > 0:
        alertas.append({
            "tipo": "incidente_sin_investigacion",
            "nivel": "critico",
            "mensaje": f"{sin_investigacion} incidente(s) abiertos sin investigación documentada",
            "url_destino": "/incidentes?estado=abierto"
        })

    # Acciones correctivas vencidas
    acciones_vencidas = db.query(AccionCorrectiva)\
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)\
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != "completada",
            AccionCorrectiva.fecha_limite < datetime.utcnow()
        ).count()

    if acciones_vencidas > 0:
        alertas.append({
            "tipo": "accion_correctiva_vencida",
            "nivel": "critico",
            "mensaje": f"{acciones_vencidas} acción(es) correctiva(s) vencida(s)",
            "url_destino": "/acciones-correctivas"
        })

    # Acciones próximas a vencer (en los próximos 7 días)
    proxima_semana = datetime.utcnow() + timedelta(days=7)
    acciones_proximas = db.query(AccionCorrectiva)\
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)\
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != "completada",
            AccionCorrectiva.fecha_limite >= datetime.utcnow(),
            AccionCorrectiva.fecha_limite <= proxima_semana
        ).count()

    if acciones_proximas > 0:
        alertas.append({
            "tipo": "accion_correctiva_proxima",
            "nivel": "medio",
            "mensaje": f"{acciones_proximas} acción(es) correctiva(s) vence(n) en los próximos 7 días",
            "url_destino": "/acciones-correctivas"
        })

    return {"total_alertas": len(alertas), "alertas": alertas}