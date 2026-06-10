# app/services/auditoria_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
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
    NoConformidadCreate,
    NoConformidadUpdate,
)

# ── Auditorías ────────────────────────────────────────────────────


def get_all_auditorias(db: Session, empresa_id: UUID, skip: int = 0, limit: int = 50):
    return (
        db.query(Auditoria)
        .filter(Auditoria.empresa_id == empresa_id)
        .order_by(Auditoria.fecha_programada.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


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


def create_no_conformidad(db: Session, hallazgo_id: UUID, datos: NoConformidadCreate):
    hallazgo = db.query(Hallazgo).filter(Hallazgo.id == hallazgo_id).first()
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
    """Detecta auditorías vencidas y NC vencidas, crea notificaciones por empresa."""
    from app.services import notificacion_service

    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    # Auditorías cuya fecha_programada ya pasó y no están cerradas
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

    empresas_notificadas = set()
    for auditoria in auditorias_vencidas:
        if auditoria.empresa_id not in empresas_notificadas:
            notificacion_service.crear_notificacion(
                db,
                empresa_id=auditoria.empresa_id,
                tipo="auditoria_vencida",
                titulo="Auditoría vencida sin cerrar",
                descripcion=f"Auditoría programada para el {auditoria.fecha_programada.strftime('%d/%m/%Y')} no ha sido completada.",
                modulo="auditorias",
                url_destino="/auditorias",
            )
            empresas_notificadas.add(auditoria.empresa_id)

    # NC cuya fecha_limite ya pasó y siguen abiertas o en proceso
    ncs_vencidas = (
        db.query(NoConformidad)
        .filter(
            NoConformidad.fecha_limite < ahora,
            NoConformidad.estado.notin_([EstadoNCEnum.cerrada, EstadoNCEnum.vencida]),
        )
        .all()
    )

    for nc in ncs_vencidas:
        nc.estado = EstadoNCEnum.vencida

    db.commit()

    return {
        "auditorias_vencidas": len(auditorias_vencidas),
        "nc_marcadas_vencidas": len(ncs_vencidas),
    }


def update_no_conformidad(db: Session, nc_id: UUID, datos: NoConformidadUpdate):
    nc = db.query(NoConformidad).filter(NoConformidad.id == nc_id).first()
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
