# app/schemas/usuario_schema.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from enum import Enum


class RolEnum(str, Enum):
    sst = "sst"
    gerencia = "gerencia"
    empleado = "empleado"


class UsuarioCreate(BaseModel):
    nombre: str
    email: EmailStr
    role: RolEnum
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