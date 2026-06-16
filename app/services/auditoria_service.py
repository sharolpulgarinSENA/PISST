# app/services/auditoria_service.py
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auditoria import (
    Auditoria,
    EstadoAuditoriaEnum,
    EstadoNCEnum,
    Hallazgo,
    NoConformidad,
)
from app.schemas.auditoria import (
    AuditoriaCreate,
    HallazgoCreate,
    HallazgoUpdate,
    NoConformidadCreate,
    NoConformidadUpdate,
)

# ── Auditorías ────────────────────────────────────────────────────


def get_all_auditorias(db: Session, empresa_id: UUID, skip: int = 0, limit: int = 50):
    auditorias = (
        db.query(Auditoria)
        .filter(Auditoria.empresa_id == empresa_id)
        .order_by(Auditoria.fecha_programada.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    for auditoria in auditorias:
        auditoria.nc_abiertas = (
            db.query(func.count(NoConformidad.id))
            .join(Hallazgo, Hallazgo.id == NoConformidad.hallazgo_id)
            .filter(
                Hallazgo.auditoria_id == auditoria.id,
                NoConformidad.estado == EstadoNCEnum.abierta,
            )
            .scalar()
            or 0
        )

    return auditorias


def create_auditoria(db: Session, datos: AuditoriaCreate, empresa_id: UUID):
    auditoria = Auditoria(
        objetivos=datos.objetivos,
        fecha_programada=datos.fecha_programada,
        area_id=datos.area_id,
        auditor_id=datos.auditor_id,
        empresa_id=empresa_id,
    )
    db.add(auditoria)
    db.commit()
    db.refresh(auditoria)
    return auditoria


def get_auditoria_by_id(db: Session, auditoria_id: UUID, empresa_id: UUID):
    auditoria = (
        db.query(Auditoria)
        .filter(Auditoria.id == auditoria_id, Auditoria.empresa_id == empresa_id)
        .first()
    )
    if not auditoria:
        raise HTTPException(status_code=404, detail="Auditoría no encontrada")
    return auditoria


def cambiar_estado_auditoria(
    db: Session, auditoria_id: UUID, empresa_id: UUID, nuevo_estado: str
):
    auditoria = get_auditoria_by_id(db, auditoria_id, empresa_id)
    auditoria.estado = nuevo_estado
    if nuevo_estado == "en_ejecucion":
        auditoria.fecha_ejecucion = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(auditoria)
    return auditoria


# ── Hallazgos ─────────────────────────────────────────────────────


def create_hallazgo(
    db: Session, auditoria_id: UUID, empresa_id: UUID, datos: HallazgoCreate
):
    get_auditoria_by_id(db, auditoria_id, empresa_id)

    hallazgo = Hallazgo(
        descripcion=datos.descripcion,
        clasificacion=datos.clasificacion,
        evidencia=datos.evidencia,
        recomendacion=datos.recomendacion,
        auditoria_id=auditoria_id,
    )
    db.add(hallazgo)
    db.commit()
    db.refresh(hallazgo)
    return hallazgo


def get_hallazgos_by_auditoria(db: Session, auditoria_id: UUID, empresa_id: UUID):
    get_auditoria_by_id(db, auditoria_id, empresa_id)
    return db.query(Hallazgo).filter(Hallazgo.auditoria_id == auditoria_id).all()


def get_hallazgo_by_id(db: Session, hallazgo_id: UUID, empresa_id: UUID):
    hallazgo = (
        db.query(Hallazgo)
        .join(Hallazgo.auditoria)
        .filter(
            Hallazgo.id == hallazgo_id,
            Auditoria.empresa_id == empresa_id,
        )
        .first()
    )
    if not hallazgo:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")
    return hallazgo


def update_hallazgo(
    db: Session, hallazgo_id: UUID, empresa_id: UUID, datos: HallazgoUpdate
):
    hallazgo = get_hallazgo_by_id(db, hallazgo_id, empresa_id)

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(hallazgo, campo, valor)

    db.commit()
    db.refresh(hallazgo)
    return hallazgo


def delete_hallazgo(db: Session, hallazgo_id: UUID, empresa_id: UUID):
    hallazgo = get_hallazgo_by_id(db, hallazgo_id, empresa_id)

    if hallazgo.no_conformidades:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar un hallazgo con No Conformidades asociadas",
        )

    db.delete(hallazgo)
    db.commit()


def get_progreso_auditoria(db: Session, auditoria_id: UUID, empresa_id: UUID):
    """Calcula el % de no conformidades cerradas."""
    get_auditoria_by_id(db, auditoria_id, empresa_id)

    hallazgos = db.query(Hallazgo).filter(Hallazgo.auditoria_id == auditoria_id).all()

    total_nc = 0
    nc_cerradas = 0

    for hallazgo in hallazgos:
        for nc in hallazgo.no_conformidades:
            total_nc += 1
            if nc.estado == "cerrada":
                nc_cerradas += 1

    return {
        "total_no_conformidades": total_nc,
        "cerradas": nc_cerradas,
        "porcentaje_cierre": (
            round((nc_cerradas / total_nc) * 100) if total_nc > 0 else 100
        ),
    }


# ── No Conformidades ──────────────────────────────────────────────


def create_no_conformidad(
    db: Session, hallazgo_id: UUID, datos: NoConformidadCreate, empresa_id: UUID
):
    hallazgo = (
        db.query(Hallazgo)
        .join(Hallazgo.auditoria)
        .filter(
            Hallazgo.id == hallazgo_id,
            Auditoria.empresa_id == empresa_id,
        )
        .first()
    )
    if not hallazgo:
        raise HTTPException(status_code=404, detail="Hallazgo no encontrado")

    nc = NoConformidad(
        descripcion=datos.descripcion,
        fecha_limite=datos.fecha_limite,
        responsable_id=datos.responsable_id,
        hallazgo_id=hallazgo_id,
    )
    db.add(nc)
    db.commit()
    db.refresh(nc)
    return nc


def verificar_auditorias_vencidas(db: Session):
    """
    Cron diario. Detecta registros vencidos y próximos a vencer (24h) en todos
    los módulos con fecha límite: auditorías, acciones correctivas, sesiones de
    capacitación, controles de riesgo y hallazgos/NC.
    Genera notificaciones en el feed y actualiza estados.
    """
    from app.models.accion_correctiva import AccionCorrectiva, EstadoAccionEnum
    from app.models.capacitacion import Capacitacion, SesionCapacitacion
    from app.models.incidente import Incidente
    from app.models.riesgo import EstadoControlEnum, MedidaControl, Peligro
    from app.services import notificacion_service

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    manana = ahora + timedelta(hours=24)

    resumen = {
        "auditorias_vencidas": 0,
        "auditorias_proximas": 0,
        "acciones_vencidas": 0,
        "acciones_proximas": 0,
        "sesiones_vencidas": 0,
        "sesiones_proximas": 0,
        "controles_vencidos": 0,
        "controles_proximos": 0,
        "nc_vencidas": 0,
        "nc_proximas": 0,
    }

    # ── 1. Auditorías ──────────────────────────────────────────────
    auditorias_vencidas = (
        db.query(Auditoria)
        .filter(
            Auditoria.fecha_programada < ahora,
            Auditoria.estado.notin_(
                [EstadoAuditoriaEnum.completada, EstadoAuditoriaEnum.cancelada]
            ),
        )
        .all()
    )
    for auditoria in auditorias_vencidas:
        notificacion_service.crear_notificacion(
            db,
            empresa_id=auditoria.empresa_id,
            tipo="auditoria_vencida",
            titulo="Auditoría vencida sin cerrar",
            descripcion=f"Auditoría programada para el {auditoria.fecha_programada.strftime('%d/%m/%Y')} no ha sido completada.",
            modulo="auditorias",
            url_destino=f"/auditorias?auditoria={auditoria.id}",
        )
    resumen["auditorias_vencidas"] = len(auditorias_vencidas)

    auditorias_proximas = (
        db.query(Auditoria)
        .filter(
            Auditoria.fecha_programada >= ahora,
            Auditoria.fecha_programada <= manana,
            Auditoria.estado.notin_(
                [EstadoAuditoriaEnum.completada, EstadoAuditoriaEnum.cancelada]
            ),
        )
        .all()
    )
    for auditoria in auditorias_proximas:
        notificacion_service.crear_notificacion(
            db,
            empresa_id=auditoria.empresa_id,
            tipo="auditoria_proxima_vencer",
            titulo="Auditoría próxima a vencer",
            descripcion=f"La auditoría del {auditoria.fecha_programada.strftime('%d/%m/%Y')} vence mañana.",
            modulo="auditorias",
            url_destino=f"/auditorias?auditoria={auditoria.id}",
        )
    resumen["auditorias_proximas"] = len(auditorias_proximas)

    # ── 2. Acciones correctivas ────────────────────────────────────
    acciones_vencidas = (
        db.query(AccionCorrectiva)
        .filter(
            AccionCorrectiva.fecha_limite < ahora,
            AccionCorrectiva.estado != EstadoAccionEnum.completada,
        )
        .all()
    )
    for accion in acciones_vencidas:
        incidente = db.query(Incidente).filter_by(id=accion.incidente_id).first()
        if incidente:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=incidente.empresa_id,
                tipo="accion_correctiva_vencida",
                titulo="Acción correctiva vencida",
                descripcion=f"Acción correctiva sin completar desde {accion.fecha_limite.strftime('%d/%m/%Y')}.",
                modulo="incidentes",
                url_destino=f"/incidentes?reporte={accion.incidente_id}&tab=acciones",
            )
    resumen["acciones_vencidas"] = len(acciones_vencidas)

    acciones_proximas = (
        db.query(AccionCorrectiva)
        .filter(
            AccionCorrectiva.fecha_limite >= ahora,
            AccionCorrectiva.fecha_limite <= manana,
            AccionCorrectiva.estado != EstadoAccionEnum.completada,
        )
        .all()
    )
    for accion in acciones_proximas:
        incidente = db.query(Incidente).filter_by(id=accion.incidente_id).first()
        if incidente:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=incidente.empresa_id,
                tipo="accion_correctiva_proxima_vencer",
                titulo="Acción correctiva próxima a vencer",
                descripcion=f"Acción correctiva vence mañana ({accion.fecha_limite.strftime('%d/%m/%Y')}).",
                modulo="incidentes",
                url_destino=f"/incidentes?reporte={accion.incidente_id}&tab=acciones",
            )
    resumen["acciones_proximas"] = len(acciones_proximas)

    # ── 3. Sesiones de capacitación ────────────────────────────────
    sesiones_vencidas = (
        db.query(SesionCapacitacion)
        .filter(
            SesionCapacitacion.fecha < ahora,
            SesionCapacitacion.estado == "programada",
        )
        .all()
    )
    for sesion in sesiones_vencidas:
        notificacion_service.crear_notificacion(
            db,
            empresa_id=db.query(Capacitacion)
            .filter_by(id=sesion.capacitacion_id)
            .first()
            .empresa_id,
            tipo="capacitacion_sesion_vencida",
            titulo="Sesión de capacitación no realizada",
            descripcion=f"La sesión programada para el {sesion.fecha.strftime('%d/%m/%Y')} no fue marcada como realizada.",
            modulo="capacitaciones",
            url_destino=f"/capacitaciones?capacitacion={sesion.capacitacion_id}",
        )
        sesion.estado = "no_realizada"
    resumen["sesiones_vencidas"] = len(sesiones_vencidas)

    sesiones_proximas = (
        db.query(SesionCapacitacion)
        .filter(
            SesionCapacitacion.fecha >= ahora,
            SesionCapacitacion.fecha <= manana,
            SesionCapacitacion.estado == "programada",
        )
        .all()
    )
    for sesion in sesiones_proximas:
        cap = db.query(Capacitacion).filter_by(id=sesion.capacitacion_id).first()
        if cap:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=cap.empresa_id,
                tipo="capacitacion_sesion_proxima_vencer",
                titulo="Sesión de capacitación mañana",
                descripcion=f"Sesión programada para mañana {sesion.fecha.strftime('%d/%m/%Y')}.",
                modulo="capacitaciones",
                url_destino=f"/capacitaciones?capacitacion={sesion.capacitacion_id}",
            )
    resumen["sesiones_proximas"] = len(sesiones_proximas)

    # ── 4. Controles de riesgo ─────────────────────────────────────
    controles_vencidos = (
        db.query(MedidaControl)
        .filter(
            MedidaControl.fecha_limite < ahora,
            MedidaControl.fecha_limite.isnot(None),
            MedidaControl.estado != EstadoControlEnum.completada,
        )
        .all()
    )
    for control in controles_vencidos:
        peligro = db.query(Peligro).filter_by(id=control.peligro_id).first()
        if peligro:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=peligro.empresa_id,
                tipo="riesgo_control_vencido",
                titulo="Control de riesgo vencido",
                descripcion=f"Medida de control sin implementar desde {control.fecha_limite.strftime('%d/%m/%Y')}.",
                modulo="riesgos",
                url_destino=f"/riesgos?riesgo={control.peligro_id}&control=1",
            )
    resumen["controles_vencidos"] = len(controles_vencidos)

    controles_proximos = (
        db.query(MedidaControl)
        .filter(
            MedidaControl.fecha_limite >= ahora,
            MedidaControl.fecha_limite <= manana,
            MedidaControl.fecha_limite.isnot(None),
            MedidaControl.estado != EstadoControlEnum.completada,
        )
        .all()
    )
    for control in controles_proximos:
        peligro = db.query(Peligro).filter_by(id=control.peligro_id).first()
        if peligro:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=peligro.empresa_id,
                tipo="riesgo_control_proximo_vencer",
                titulo="Control de riesgo próximo a vencer",
                descripcion=f"Medida de control vence mañana ({control.fecha_limite.strftime('%d/%m/%Y')}).",
                modulo="riesgos",
                url_destino=f"/riesgos?riesgo={control.peligro_id}&control=1",
            )
    resumen["controles_proximos"] = len(controles_proximos)

    # ── 5. Hallazgos / No Conformidades ───────────────────────────
    ncs_vencidas = (
        db.query(NoConformidad)
        .filter(
            NoConformidad.fecha_limite < ahora,
            NoConformidad.estado.notin_([EstadoNCEnum.cerrada, EstadoNCEnum.vencida]),
        )
        .all()
    )
    for nc in ncs_vencidas:
        hallazgo = db.query(Hallazgo).filter_by(id=nc.hallazgo_id).first()
        if hallazgo:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=db.query(Auditoria)
                .filter_by(id=hallazgo.auditoria_id)
                .first()
                .empresa_id,
                tipo="hallazgo_vencido",
                titulo="Hallazgo/NC vencido sin cerrar",
                descripcion=f"No conformidad sin cerrar desde {nc.fecha_limite.strftime('%d/%m/%Y')}.",
                modulo="auditorias",
                url_destino=f"/auditorias?auditoria={hallazgo.auditoria_id}&hallazgo=1",
            )
        nc.estado = EstadoNCEnum.vencida
    resumen["nc_vencidas"] = len(ncs_vencidas)

    ncs_proximas = (
        db.query(NoConformidad)
        .filter(
            NoConformidad.fecha_limite >= ahora,
            NoConformidad.fecha_limite <= manana,
            NoConformidad.estado.notin_([EstadoNCEnum.cerrada, EstadoNCEnum.vencida]),
        )
        .all()
    )
    for nc in ncs_proximas:
        hallazgo = db.query(Hallazgo).filter_by(id=nc.hallazgo_id).first()
        if hallazgo:
            auditoria = db.query(Auditoria).filter_by(id=hallazgo.auditoria_id).first()
            if auditoria:
                notificacion_service.crear_notificacion(
                    db,
                    empresa_id=auditoria.empresa_id,
                    tipo="hallazgo_proximo_vencer",
                    titulo="Hallazgo/NC próximo a vencer",
                    descripcion=f"No conformidad vence mañana ({nc.fecha_limite.strftime('%d/%m/%Y')}).",
                    modulo="auditorias",
                    url_destino=f"/auditorias?auditoria={hallazgo.auditoria_id}&hallazgo=1",
                )
    resumen["nc_proximas"] = len(ncs_proximas)

    db.commit()
    return resumen


def update_no_conformidad(
    db: Session, nc_id: UUID, datos: NoConformidadUpdate, empresa_id: UUID
):
    nc = (
        db.query(NoConformidad)
        .join(NoConformidad.hallazgo)
        .join(Hallazgo.auditoria)
        .filter(
            NoConformidad.id == nc_id,
            Auditoria.empresa_id == empresa_id,
        )
        .first()
    )
    if not nc:
        raise HTTPException(status_code=404, detail="No conformidad no encontrada")

    # No cerrar sin evidencia
    if datos.estado == "cerrada" and not datos.evidencia_cierre:
        raise HTTPException(
            status_code=400,
            detail="No se puede cerrar una NC sin evidencia de la acción tomada",
        )

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(nc, campo, valor)

    if datos.estado == "cerrada":
        nc.fecha_cierre = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(nc)
    return nc
