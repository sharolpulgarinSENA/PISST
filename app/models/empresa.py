
import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from app.core.database import Base

class Empresa(Base):
    __tablename__ = "empresas"

    # UUID: identificador único universal, más seguro que números 1, 2, 3
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = Column(String(200), nullable=False)   # nullable=False = campo obligatorio
    nit = Column(String(20), unique=True, nullable=False)  # unique = no duplicados
    sector = Column(String(100))
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


