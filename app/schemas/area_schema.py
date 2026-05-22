from pydantic import BaseModel
from uuid import UUID

class AreaResponse(BaseModel):
    id: UUID
    nombre: str
    descripcion: str | None = None

    class Config:
        from_attributes = True