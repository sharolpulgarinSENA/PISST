# app/schemas/usuario_schema.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from app.models.user import RoleEnum


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    role: RoleEnum
    area_id: Optional[UUID] = None
    cargo_id: Optional[UUID] = None


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    area_id: Optional[UUID] = None
    cargo_id: Optional[UUID] = None
    activo: Optional[bool] = None


class UsuarioResponse(BaseModel):
    id: UUID
    nombre: str
    email: str
    role: str
    activo: bool
    area_id: Optional[UUID] = None
    cargo_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        