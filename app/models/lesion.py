# app/models/lesion.py
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Lesion(Base):
    __tablename__ = "lesiones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_lesion = Column(String(200))
    parte_afectada = Column(String(200))
    incapacidad_dias = Column(Integer, default=0)

    incidente_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidentes.id", ondelete="CASCADE"),
        nullable=False,
    )

    incidente = relationship("Incidente", back_populates="lesion")
