# app/models/auditoria.py
import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


class EstadoAuditoriaEnum(str, enum.Enum):
    planificada  = "planificada"
    en_ejecucion = "en_ejecucion"
    completada   = "completada"
    cancelada    = "cancelada"


class ClasificacionHallazgoEnum(str, enum.Enum):
    conformidad         = "conformidad"
    no_conformidad_menor = "no_conformidad_menor"
    no_conformidad_mayor = "no_conformidad_mayor"
    observacion         = "observacion"


class EstadoNCEnum(str, enum.Enum):
    abierta    = "abierta"
    en_proceso = "en_proceso"
    cerrada    = "cerrada"
    vencida    = "vencida"


class Auditoria(Base):
    __tablename__ = "auditorias"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    objetivos   = Column(Text)
    estado      = Column(Enum(EstadoAuditoriaEnum), default=EstadoAuditoriaEnum.planificada)
    fecha_programada = Column(DateTime, nullable=False)
    fecha_ejecucion  = Column(DateTime, nullable=True)
    fecha_creacion   = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    empresa_id  = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    area_id     = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=True)
    auditor_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    area     = relationship("Area", foreign_keys=[area_id])
    auditor  = relationship("User", foreign_keys=[auditor_id])
    hallazgos = relationship("Hallazgo", back_populates="auditoria")


class Hallazgo(Base):
    __tablename__ = "hallazgos"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descripcion    = Column(Text, nullable=False)
    clasificacion  = Column(Enum(ClasificacionHallazgoEnum), nullable=False)
    evidencia      = Column(Text, nullable=True)
    recomendacion  = Column(Text, nullable=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    auditoria_id = Column(UUID(as_uuid=True),
                          ForeignKey("auditorias.id", ondelete="CASCADE"),
                          nullable=False)

    auditoria        = relationship("Auditoria", back_populates="hallazgos")
    no_conformidades = relationship("NoConformidad", back_populates="hallazgo")


class NoConformidad(Base):
    __tablename__ = "no_conformidades"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descripcion    = Column(Text, nullable=False)
    estado         = Column(Enum(EstadoNCEnum), default=EstadoNCEnum.abierta)
    evidencia_cierre = Column(Text, nullable=True)
    fecha_limite   = Column(DateTime, nullable=False)
    fecha_cierre   = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    hallazgo_id    = Column(UUID(as_uuid=True),
                            ForeignKey("hallazgos.id", ondelete="CASCADE"),
                            nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    hallazgo    = relationship("Hallazgo", back_populates="no_conformidades")
    responsable = relationship("User", foreign_keys=[responsable_id])