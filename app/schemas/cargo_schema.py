from pydantic import BaseModel
from uuid import UUID

class CargoResponse(BaseModel):
    id: UUID
    nombre: str

    class Config:
        from_attributes = True