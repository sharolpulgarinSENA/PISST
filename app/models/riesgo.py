# app/models/riesgo.py
import uuid
import enum
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    ForeignKey,
    Enum,
    DateTime,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class TipoPeligroEnum(str, enum.Enum):
    fisico = "fisico"
    quimico = "quimico"
    biologico = "biologico"
    ergonomico = "ergonomico"
    psicosocial = "psicosocial"
    mecanico = "mecanico"
    electrico = "electrico"
    locativo = "locativo"
    fenomeno_natural = "fenomeno_natural"


class NivelRiesgoEnum(str, enum.Enum):
    bajo = "bajo"
    medio = "medio"
    alto = "alto"
    critico = "critico"


class TipoControlEnum(str, enum.Enum):
    eliminacion = "eliminacion"
    sustitucion = "sustitucion"
    ingenieria = "ingenieria"
    administrativo = "administrativo"
    epp = "epp"


class EstadoControlEnum(str, enum.Enum):
    planificada = "planificada"
    en_ejecucion = "en_ejecucion"
    completada = "completada"


class Peligro(Base):
    __tablename__ = "peligros"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descripcion = Column(Text, nullable=False)
    tipo = Column(Enum(TipoPeligroEnum), nullable=False)
    actividad = Column(String(300))
    trabajadores_expuestos = Column(Integer, default=0)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True)

    area = relationship("Area", foreign_keys=[area_id])
    evaluaciones = relationship("EvaluacionRiesgo", back_populates="peligro")
    medidas_control = relationship("MedidaControl", back_populates="peligro")


class EvaluacionRiesgo(Base):
    __tablename__ = "evaluaciones_riesgo"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    probabilidad = Column(Integer, nullable=False)  # 1 a 5
    severidad = Column(Integer, nullable=False)  # 1 a 5
    nivel_riesgo = Column(Enum(NivelRiesgoEnum), nullable=False)
    es_residual = Column(Boolean, default=False)  # True = revaluación post-control
    fecha_evaluacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    peligro_id = Column(
        UUID(as_uuid=True),
        ForeignKey("peligros.id", ondelete="CASCADE"),
        nullable=False,
    )

    peligro = relationship("Peligro", back_populates="evaluaciones")


class MedidaControl(Base):
    __tablename__ = "medidas_control"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descripcion = Column(Text, nullable=False)
    tipo = Column(Enum(TipoControlEnum), nullable=False)
    estado = Column(Enum(EstadoControlEnum), default=EstadoControlEnum.planificada)
    evidencia = Column(Text, nullable=True)
    fecha_limite = Column(DateTime, nullable=True)
    fecha_creacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    peligro_id = Column(UUID(as_uuid=True), ForeignKey("peligros.id"), nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    peligro = relationship("Peligro", back_populates="medidas_control")
    responsable = relationship("User", foreign_keys=[responsable_id])
