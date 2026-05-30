# app/models/audit_log.py
import uuid
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accion = Column(String(100), nullable=False)
    entidad = Column(String(100), nullable=False)
    entidad_id = Column(String(255), nullable=True)
    detalle = Column(Text, nullable=True)
    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
