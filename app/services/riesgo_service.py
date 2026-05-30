# app/services/riesgo_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from uuid import UUID

from app.models.riesgo import Peligro, EvaluacionRiesgo, MedidaControl, NivelRiesgoEnum
from app.schemas.riesgo import (
    PeligroCreate,
    EvaluacionRiesgoCreate,
    MedidaControlCreate,
    MedidaControlUpdate,
)


def calcular_nivel_riesgo(probabilidad: int, severidad: int) -> NivelRiesgoEnum:
    """
    Calcula el nivel de riesgo automáticamente.
    probabilidad x severidad:
    1-4   → Bajo
    5-9   → Medio
    10-16 → Alto
    17-25 → Crítico
    """
    nivel = probabilidad * severidad
    if nivel <= 4:
        return NivelRiesgoEnum.bajo
    if nivel <= 9:
        return NivelRiesgoEnum.medio
    if nivel <= 16:
        return NivelRiesgoEnum.alto
    return NivelRiesgoEnum.critico


# ── Peligros ──────────────────────────────────────────────────────


def get_all_peligros(
    db: Session,
    empresa_id: UUID,
    tipo: str = None,
    area_id: UUID = None,
    skip: int = 0,
    limit: int = 50,
):
    query = db.query(Peligro).filter(
        Peligro.empresa_id == empresa_id, Peligro.activo == True
    )
    if tipo:
        query = query.filter(Peligro.tipo == tipo)
    if area_id:
        query = query.filter(Peligro.area_id == area_id)
    return query.order_by(Peligro.fecha_creacion.desc()).offset(skip).limit(limit).all()


def create_peligro(db: Session, datos: PeligroCreate, empresa_id: UUID):
    peligro = Peligro(
        descripcion=datos.descripcion,
        tipo=datos.tipo,
        actividad=datos.actividad,
        trabajadores_expuestos=datos.trabajadores_expuestos,
        area_id=datos.area_id,
        empresa_id=empresa_id,
    )
    db.add(peligro)
    db.commit()
    db.refresh(peligro)
    return peligro


def get_peligro_by_id(db: Session, peligro_id: UUID, empresa_id: UUID):
    peligro = (
        db.query(Peligro)
        .filter(Peligro.id == peligro_id, Peligro.empresa_id == empresa_id)
        .first()
    )
    if not peligro:
        raise HTTPException(status_code=404, detail="Peligro no encontrado")
    return peligro


# ── Evaluaciones de Riesgo ────────────────────────────────────────


def create_evaluacion_riesgo(
    db: Session, peligro_id: UUID, empresa_id: UUID, datos: EvaluacionRiesgoCreate
):
    # Verificar que el peligro existe
    get_peligro_by_id(db, peligro_id, empresa_id)

    # Calcular nivel de riesgo automáticamente
    nivel = calcular_nivel_riesgo(datos.probabilidad, datos.severidad)

    evaluacion = EvaluacionRiesgo(
        probabilidad=datos.probabilidad,
        severidad=datos.severidad,
        nivel_riesgo=nivel,
        es_residual=datos.es_residual,
        peligro_id=peligro_id,
    )
    db.add(evaluacion)
    db.commit()
    db.refresh(evaluacion)
    return evaluacion


def get_matriz_riesgos(db: Session, empresa_id: UUID):
    """
    Retorna los datos para renderizar la matriz de calor.
    Agrupa los peligros por nivel de riesgo.
    """
    peligros = get_all_peligros(db, empresa_id)

    matriz = {"bajo": [], "medio": [], "alto": [], "critico": []}

    for peligro in peligros:
        if not peligro.evaluaciones:
            continue
        # Tomar la última evaluación
        ultima_eval = sorted(
            peligro.evaluaciones, key=lambda e: e.fecha_evaluacion, reverse=True
        )[0]
        nivel = ultima_eval.nivel_riesgo.value
        matriz[nivel].append(
            {
                "peligro_id": str(peligro.id),
                "descripcion": peligro.descripcion,
                "tipo": peligro.tipo.value,
                "probabilidad": ultima_eval.probabilidad,
                "severidad": ultima_eval.severidad,
                "nivel_riesgo": nivel,
            }
        )

    return {
        "total_peligros": len(peligros),
        "criticos": len(matriz["critico"]),
        "altos": len(matriz["alto"]),
        "medios": len(matriz["medio"]),
        "bajos": len(matriz["bajo"]),
        "matriz": matriz,
    }


# ── Medidas de Control ────────────────────────────────────────────


def create_medida_control(
    db: Session, peligro_id: UUID, empresa_id: UUID, datos: MedidaControlCreate
):
    get_peligro_by_id(db, peligro_id, empresa_id)

    medida = MedidaControl(
        descripcion=datos.descripcion,
        tipo=datos.tipo,
        fecha_limite=datos.fecha_limite,
        responsable_id=datos.responsable_id,
        peligro_id=peligro_id,
    )
    db.add(medida)
    db.commit()
    db.refresh(medida)
    return medida


def update_medida_control(db: Session, medida_id: UUID, datos: MedidaControlUpdate):
    medida = db.query(MedidaControl).filter(MedidaControl.id == medida_id).first()
    if not medida:
        raise HTTPException(status_code=404, detail="Medida de control no encontrada")

    # No cerrar sin evidencia
    if datos.estado == "completada" and not datos.evidencia:
        raise HTTPException(
            status_code=400,
            detail="No se puede completar una medida sin evidencia de implementación",
        )

    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(medida, campo, valor)

    db.commit()
    db.refresh(medida)
    return medida
