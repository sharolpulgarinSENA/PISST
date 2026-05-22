from pydantic import BaseModel
from uuid import UUID

class CargoCreate(BaseModel):
    nombre: str
    area_id: UUID

class CargoResponse(BaseModel):
    id: UUID
    nombre: str

    class Config:
        from_attributes = True