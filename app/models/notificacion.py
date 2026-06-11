# app/models/notificacion.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    tipo = Column(String(60), nullable=False)
    titulo = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=False)
    modulo = Column(String(60), nullable=False)
    url_destino = Column(String(300), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    leido = Column(Boolean, default=False, nullable=False)
    fecha = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
