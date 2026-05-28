# app/schemas/riesgo.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── Peligro ───────────────────────────────────────────────────────

class PeligroCreate(BaseModel):
    descripcion: str
    tipo: str  # fisico, quimico, biologico, ergonomico, etc.
    actividad: Optional[str] = None
    trabajadores_expuestos: Optional[int] = 0
    area_id: Optional[UUID] = None

class PeligroResponse(BaseModel):
    id: UUID
    descripcion: str
    tipo: str
    actividad: Optional[str]
    trabajadores_expuestos: int
    activo: bool
    empresa_id: UUID
    area_id: Optional[UUID]

    model_config = ConfigDict(from_attributes=True)


# ── Evaluación de Riesgo ──────────────────────────────────────────

class EvaluacionRiesgoCreate(BaseModel):
    probabilidad: int  # 1 a 5
    severidad: int     # 1 a 5
    es_residual: Optional[bool] = False

class EvaluacionRiesgoResponse(BaseModel):
    id: UUID
    probabilidad: int
    severidad: int
    nivel_riesgo: str
    es_residual: bool
    fecha_evaluacion: datetime
    peligro_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ── Medida de Control ─────────────────────────────────────────────

class MedidaControlCreate(BaseModel):
    descripcion: str
    tipo: str  # eliminacion, sustitucion, ingenieria, administrativo, epp
    fecha_limite: Optional[datetime] = None
    responsable_id: Optional[UUID] = None

class MedidaControlUpdate(BaseModel):
    estado: Optional[str] = None
    evidencia: Optional[str] = None
    descripcion: Optional[str] = None

class MedidaControlResponse(BaseModel):
    id: UUID
    descripcion: str
    tipo: str
    estado: str
    evidencia: Optional[str]
    fecha_limite: Optional[datetime]
    peligro_id: UUID

    model_config = ConfigDict(from_attributes=True)