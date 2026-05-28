# app/models/user.py
import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class RoleEnum(str, enum.Enum):
    admin    = "admin"     # ✅ nuevo
    sst      = "sst"
    gerencia = "gerencia"
    empleado = "empleado"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    empresa_id = Column(UUID(as_uuid=True),
                        ForeignKey("empresas.id"),
                        nullable=True)  # ✅ nullable=True para el admin
    area_id = Column(UUID(as_uuid=True),
                     ForeignKey("areas.id"),
                     nullable=True)
    cargo_id = Column(UUID(as_uuid=True),
                      ForeignKey("cargos.id"),
                      nullable=True)

    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    reset_token = Column(String(255), nullable=True)
    reset_token_expira = Column(DateTime, nullable=True)
    refresh_token = Column(String(255), nullable=True)
    refresh_token_expira = Column(DateTime, nullable=True)

    intentos_fallidos = Column(Integer, default=0, nullable=False)
    bloqueado_hasta = Column(DateTime, nullable=True)
    session_token = Column(String(64), nullable=True)
    debe_cambiar_password = Column(Boolean, default=False, nullable=False)

    area  = relationship("Area",  foreign_keys=[area_id])
    cargo = relationship("Cargo", foreign_keys=[cargo_id])

    __table_args__ = (
        Index("ix_users_empresa_activo", "empresa_id", "activo"),
    )