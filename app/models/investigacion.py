# app/models/investigacion.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Investigacion(Base):
    __tablename__ = "investigaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Método de análisis usado
    metodo_analisis = Column(String(100), default="5_por_que")

    # Causas identificadas
    causas_inmediatas = Column(Text)  # técnicas y humanas
    causas_basicas    = Column(Text)  # gestión, capacitación, procedimientos
    factores_contribuyentes = Column(Text)

    # Conclusiones
    descripcion_evento = Column(Text)
    lecciones_aprendidas = Column(Text)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Un incidente tiene una sola investigación
    incidente_id = Column(UUID(as_uuid=True),
                          ForeignKey("incidentes.id", ondelete="CASCADE"),
                          nullable=False)

    incidente = relationship("Incidente", back_populates="investigacion")