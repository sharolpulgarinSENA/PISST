# app/models/testigo.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Testigo(Base):
    __tablename__ = "testigos"

    id     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(200), nullable=False)
    relato = Column(Text)

    incidente_id = Column(UUID(as_uuid=True),
                          ForeignKey("incidentes.id", ondelete="CASCADE"),
                          nullable=False)

    incidente = relationship("Incidente", back_populates="testigos")
    