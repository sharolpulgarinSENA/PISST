# app/schemas/usuario_schema.py
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.user import RoleEnum


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    role: RoleEnum
    area_nombre: Optional[str] = None
    cargo_nombre: Optional[str] = None


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    area_id: Optional[UUID] = None
    cargo_id: Optional[UUID] = None
    activo: Optional[bool] = None


class PerfilUpdate(BaseModel):
    nombre: Optional[str] = None
    telefono: Optional[str] = None


class UsuarioResponse(BaseModel):
    id: UUID
    nombre: str
    email: str
    role: str
    activo: bool
    telefono: Optional[str] = None
    foto_url: Optional[str] = None
    area_id: Optional[UUID] = None
    cargo_id: Optional[UUID] = None
    area_nombre: Optional[str] = None
    cargo_nombre: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
