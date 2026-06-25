# app/services/incidente_service.py
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.accion_correctiva import AccionCorrectiva
from app.models.incidente import EstadoIncidenteEnum, Incidente
from app.models.investigacion import Investigacion
from app.models.lesion import Lesion
from app.models.testigo import Testigo
from app.schemas.incidente import (
    AccionCorrectivaCreate,
    AccionCorrectivaUpdate,
    IncidenteCreate,
    InvestigacionCreate,
)
from app.services.audit_service import registrar_auditoria

# ── Incidentes ────────────────────────────────────────────────────


def get_all_incidentes(
    db: Session,
    empresa_id: UUID,
    estado: str = None,
    tipo: str = None,
    skip: int = 0,
    limit: int = 50,
):
    query = (
        db.query(Incidente)
        .options(joinedload(Incidente.reportado_por))
        .filter(Incidente.empresa_id == empresa_id)
    )
    if estado:
        query = query.filter(Incidente.estado == estado)
    if tipo:
        query = query.filter(Incidente.tipo == tipo)
    return (
        query.order_by(Incidente.fecha_creacion.desc()).offset(skip).limit(limit).all()
    )


def get_incidente_by_id(db: Session, incidente_id: UUID, empresa_id: UUID):
    """Retorna un incidente específico verificando que pertenece a la empresa."""
    incidente = (
        db.query(Incidente)
        .options(joinedload(Incidente.reportado_por))
        .filter(Incidente.id == incidente_id, Incidente.empresa_id == empresa_id)
        .first()
    )
    if not incidente:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")
    return incidente


def create_incidente(
    db: Session, datos: IncidenteCreate, empresa_id: UUID, reportado_por_id: UUID
):
    """Crea un nuevo incidente con su lesión y testigos si los hay."""
    incidente = Incidente(
        tipo=datos.tipo,
        severidad=datos.severidad,
        fecha=datos.fecha,
        lugar=datos.lugar,
        descripcion=datos.descripcion,
        empresa_id=empresa_id,
        reportado_por_id=reportado_por_id,
        trabajador_afectado_id=datos.trabajador_afectado_id or reportado_por_id,
    )
    db.add(incidente)
    db.flush()  # obtener el id sin hacer commit

    # Crear lesión si se proporcionó
    if datos.lesion:
        lesion = Lesion(
            tipo_lesion=datos.lesion.tipo_lesion,
            parte_afectada=datos.lesion.parte_afectada,
            incapacidad_dias=datos.lesion.incapacidad_dias,
            incidente_id=incidente.id,
        )
        db.add(lesion)

    # Crear testigos si se proporcionaron
    for t in datos.testigos:
        testigo = Testigo(nombre=t.nombre, relato=t.relato, incidente_id=incidente.id)
        db.add(testigo)

    db.commit()
    db.refresh(incidente)
    return incidente


def update_estado_incidente(
    db: Session, incidente_id: UUID, empresa_id: UUID, nuevo_estado: str
):
    """
    Cambia el estado de un incidente.
    No permite cerrar un incidente sin investigación completada.
    """
    incidente = get_incidente_by_id(db, incidente_id, empresa_id)

    # Validar: no cerrar sin investigación
    if nuevo_estado == "cerrado":
        if not incidente.investigacion:
            raise HTTPException(
                status_code=400,
                detail="No se puede cerrar un incidente sin investigación de causas documentada",
            )

    incidente.estado = nuevo_estado
    incidente.fecha_actualizacion = datetime.now(timezone.utc).replace(tzinfo=None)
    registrar_auditoria(
        db,
        accion="cambiar_estado_incidente",
        entidad="incidentes",
        entidad_id=str(incidente_id),
        detalle=f"Estado cambiado a {nuevo_estado}",
    )
    db.commit()
    db.refresh(incidente)
    return incidente


# ── Investigación ─────────────────────────────────────────────────


def get_investigacion(db: Session, incidente_id: UUID, empresa_id: UUID):
    """Retorna la investigación de un incidente. 404 si no existe."""
    incidente = get_incidente_by_id(db, incidente_id, empresa_id)
    if not incidente.investigacion:
        raise HTTPException(
            status_code=404, detail="Este incidente no tiene investigación registrada"
        )
    return incidente.investigacion


def get_acciones_correctivas(db: Session, incidente_id: UUID, empresa_id: UUID):
    """Retorna todas las acciones correctivas de un incidente."""
    get_incidente_by_id(db, incidente_id, empresa_id)
    return (
        db.query(AccionCorrectiva)
        .filter(AccionCorrectiva.incidente_id == incidente_id)
        .all()
    )


def update_investigacion(db: Session, incidente_id: UUID, empresa_id: UUID, datos):
    """Actualiza los campos enviados de una investigación existente. 404 si no existe."""
    investigacion = get_investigacion(db, incidente_id, empresa_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(investigacion, campo, valor)
    db.commit()
    db.refresh(investigacion)
    return investigacion


def create_investigacion(
    db: Session, incidente_id: UUID, empresa_id: UUID, datos: InvestigacionCreate
):
    """Crea la investigación de causas de un incidente."""
    # Verificar que el incidente existe y pertenece a la empresa
    incidente = get_incidente_by_id(db, incidente_id, empresa_id)

    # Verificar que no tenga ya una investigación
    if incidente.investigacion:
        raise HTTPException(
            status_code=400,
            detail="Este incidente ya tiene una investigación registrada",
        )

    investigacion = Investigacion(
        metodo_analisis=datos.metodo_analisis,
        causas_inmediatas=datos.causas_inmediatas,
        causas_basicas=datos.causas_basicas,
        factores_contribuyentes=datos.factores_contribuyentes,
        descripcion_evento=datos.descripcion_evento,
        lecciones_aprendidas=datos.lecciones_aprendidas,
        incidente_id=incidente_id,
    )
    db.add(investigacion)

    # Cambiar estado del incidente a "en_investigacion"
    incidente.estado = EstadoIncidenteEnum.en_investigacion
    db.commit()
    db.refresh(investigacion)
    return investigacion


# ── Acciones Correctivas ──────────────────────────────────────────


def create_accion_correctiva(
    db: Session, incidente_id: UUID, empresa_id: UUID, datos: AccionCorrectivaCreate
):
    """Crea una acción correctiva para un incidente."""
    get_incidente_by_id(db, incidente_id, empresa_id)

    accion = AccionCorrectiva(
        descripcion=datos.descripcion,
        prioridad=datos.prioridad,
        fecha_limite=datos.fecha_limite,
        responsable_id=datos.responsable_id,
        incidente_id=incidente_id,
    )
    db.add(accion)
    db.commit()
    db.refresh(accion)
    return accion


def update_accion_correctiva(
    db: Session, accion_id: UUID, empresa_id: UUID, datos: AccionCorrectivaUpdate
):
    """
    Actualiza una acción correctiva.
    No permite cerrarla sin evidencia documentada.
    """
    accion = (
        db.query(AccionCorrectiva)
        .join(AccionCorrectiva.incidente)
        .filter(
            AccionCorrectiva.id == accion_id,
            Incidente.empresa_id == empresa_id,
        )
        .first()
    )

    if not accion:
        raise HTTPException(status_code=404, detail="Acción correctiva no encontrada")

    # Validar: no cerrar sin evidencia
    if datos.estado == "completada" and not datos.evidencia:
        raise HTTPException(
            status_code=400,
            detail="No se puede cerrar una acción correctiva sin evidencia de implementación",
        )

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(accion, campo, valor)

    if datos.estado == "completada":
        accion.fecha_cierre = datetime.now(timezone.utc).replace(tzinfo=None)
        registrar_auditoria(
            db,
            accion="completar_accion_correctiva",
            entidad="acciones_correctivas",
            entidad_id=str(accion_id),
            detalle="Acción correctiva marcada como completada",
        )

    db.commit()
    db.refresh(accion)
    return accion


def get_progreso_incidente(db: Session, incidente_id: UUID, empresa_id: UUID):
    """Calcula el % de acciones correctivas completadas del incidente."""
    get_incidente_by_id(db, incidente_id, empresa_id)

    total = (
        db.query(AccionCorrectiva)
        .filter(AccionCorrectiva.incidente_id == incidente_id)
        .count()
    )

    if total == 0:
        return {"total": 0, "completadas": 0, "porcentaje": 0}

    completadas = (
        db.query(AccionCorrectiva)
        .filter(
            AccionCorrectiva.incidente_id == incidente_id,
            AccionCorrectiva.estado == "completada",
        )
        .count()
    )

    return {
        "total": total,
        "completadas": completadas,
        "porcentaje": round((completadas / total) * 100),
    }
