# app/models/api_key.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clave = Column(String(70), unique=True, nullable=False, index=True)
    descripcion = Column(String(200), nullable=True)
    rol = Column(String(20), nullable=False, default="cron")
    activo = Column(Boolean, default=True, nullable=False)
    fecha_creacion = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)
