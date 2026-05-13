# app/models/user.py
import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class RoleEnum(str, enum.Enum):
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
                        nullable=False)
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

    # Relaciones — solo para Python, no crean columnas en la BD
    # Permiten hacer: current_user.area.nombre y current_user.cargo.nombre
    area  = relationship("Area",  foreign_keys=[area_id])
    cargo = relationship("Cargo", foreign_keys=[cargo_id])