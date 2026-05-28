from pydantic import BaseModel, ConfigDict
from uuid import UUID

class CargoCreate(BaseModel):
    nombre: str
    area_id: UUID

class CargoResponse(BaseModel):
    id: UUID
    nombre: str

    model_config = ConfigDict(from_attributes=True)