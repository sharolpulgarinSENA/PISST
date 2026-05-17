# app/models/incidente.py
import uuid
import enum
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class TipoIncidenteEnum(str, enum.Enum):
    accidente          = "accidente"
    incidente          = "incidente"
    cuasi_accidente    = "cuasi_accidente"
    condicion_insegura = "condicion_insegura"


class SeveridadEnum(str, enum.Enum):
    sin_lesion = "sin_lesion"
    leve       = "leve"
    moderada   = "moderada"
    grave      = "grave"
    mortal     = "mortal"


class EstadoIncidenteEnum(str, enum.Enum):
    borrador         = "borrador"
    en_revision      = "en_revision"
    abierto          = "abierto"
    en_investigacion = "en_investigacion"
    cerrado          = "cerrado"


class Incidente(Base):
    __tablename__ = "incidentes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo        = Column(Enum(TipoIncidenteEnum), nullable=False)
    severidad   = Column(Enum(SeveridadEnum), nullable=False)
    fecha       = Column(DateTime, nullable=False)
    lugar       = Column(String(300), nullable=False)
    descripcion = Column(Text, nullable=False)
    estado      = Column(Enum(EstadoIncidenteEnum), default=EstadoIncidenteEnum.borrador)

    fecha_creacion      = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    empresa_id             = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    trabajador_afectado_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reportado_por_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    trabajador_afectado  = relationship("User", foreign_keys=[trabajador_afectado_id])
    reportado_por        = relationship("User", foreign_keys=[reportado_por_id])
    lesion               = relationship("Lesion", back_populates="incidente", uselist=False)
    testigos             = relationship("Testigo", back_populates="incidente")
    investigacion        = relationship("Investigacion", back_populates="incidente", uselist=False)
    acciones_correctivas = relationship("AccionCorrectiva", back_populates="incidente")
    
    # ✅ Fix Bug A — Relación con Empresa para el FURAT
    empresa              = relationship("Empresa", foreign_keys=[empresa_id])

    