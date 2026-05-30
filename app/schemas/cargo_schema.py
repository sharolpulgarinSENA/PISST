from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID


class CargoCreate(BaseModel):
    nombre: str
    area_id: UUID


class CargoResponse(BaseModel):
    id: UUID
    nombre: str
    area_id: UUID
    area_nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
