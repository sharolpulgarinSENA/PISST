from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AreaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None


class AreaResponse(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)
