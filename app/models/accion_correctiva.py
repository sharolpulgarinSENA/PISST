# app/models/accion_correctiva.py
import uuid
import enum
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class EstadoAccionEnum(str, enum.Enum):
    planificada  = "planificada"
    en_ejecucion = "en_ejecucion"
    completada   = "completada"
    vencida      = "vencida"


class PrioridadAccionEnum(str, enum.Enum):
    alta   = "alta"
    media  = "media"
    baja   = "baja"


class AccionCorrectiva(Base):
    __tablename__ = "acciones_correctivas"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    descripcion = Column(Text, nullable=False)
    evidencia   = Column(Text)  # descripción de la evidencia de cierre

    estado    = Column(Enum(EstadoAccionEnum), default=EstadoAccionEnum.planificada)
    prioridad = Column(Enum(PrioridadAccionEnum), default=PrioridadAccionEnum.media)

    fecha_limite  = Column(DateTime, nullable=False)
    fecha_cierre  = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    incidente_id   = Column(UUID(as_uuid=True), ForeignKey("incidentes.id"), nullable=False)
    responsable_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    incidente   = relationship("Incidente", back_populates="acciones_correctivas")
    responsable = relationship("User", foreign_keys=[responsable_id])