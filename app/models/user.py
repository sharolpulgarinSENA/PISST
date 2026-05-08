
import uuid
import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from app.core.database import Base

# RoleEnum: lista de valores permitidos para el campo role
# Solo puede ser uno de estos 3 valores, nada más
class RoleEnum(str, enum.Enum):
    sst      = "sst"
    gerencia = "gerencia"
    empleado = "empleado"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=False)

    # NUNCA guardar la contraseña real, solo su hash bcrypt
    password_hash = Column(String(255), nullable=False)

    # El rol determina qué puede ver y hacer este usuario
    role = Column(Enum(RoleEnum), nullable=False)

    empresa_id = Column(UUID(as_uuid=True),
                        ForeignKey("empresas.id"),
                        nullable=False)
    area_id = Column(UUID(as_uuid=True),
                     ForeignKey("areas.id"),
                     nullable=True)   # nullable=True porque Gerencia puede no tener área
    cargo_id = Column(UUID(as_uuid=True),
                      ForeignKey("cargos.id"),
                      nullable=True)

    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Para recuperación de contraseña
    reset_token = Column(String(255), nullable=True)
    reset_token_expira = Column(DateTime, nullable=True)

