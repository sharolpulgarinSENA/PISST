from pydantic import BaseModel
from typing import Optional
from uuid import UUID

class AreaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class AreaResponse(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None = None

    class Config:
        from_attributes = True