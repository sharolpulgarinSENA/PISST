import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Area(Base):
    __tablename__ = "areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(String(500))
    activo = Column(Boolean, default=True)

    # FK: vincula esta área con una empresa específica
    # ondelete="CASCADE": si se borra la empresa, se borran sus áreas
    empresa_id = Column(
        UUID(as_uuid=True),
        ForeignKey("empresas.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relación: desde un objeto Area puedo acceder a sus Cargos con area.cargos
    cargos = relationship("Cargo", back_populates="area")
