import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from app.core.database import Base


class ChatHistorial(Base):
    __tablename__ = "chat_historial"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Text permite textos muy largos (mensajes del chat pueden ser extensos)
    mensaje = Column(Text, nullable=False)
    respuesta = Column(Text, nullable=False)

    timestamp = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    # Cada conversación pertenece a un usuario específico
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
