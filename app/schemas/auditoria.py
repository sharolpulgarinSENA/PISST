# app/schemas/auditoria.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── Auditoría ─────────────────────────────────────────────────────

class AuditoriaCreate(BaseModel):
    objetivos: Optional[str] = None
    fecha_programada: datetime
    area_id: Optional[UUID] = None
    auditor_id: Optional[UUID] = None

class AuditoriaResponse(BaseModel):
    id: UUID
    objetivos: Optional[str]
    estado: str
    fecha_programada: datetime
    fecha_ejecucion: Optional[datetime]
    empresa_id: UUID
    area_id: Optional[UUID]
    auditor_id: Optional[UUID]

    class Config:
        from_attributes = True


# ── Hallazgo ──────────────────────────────────────────────────────

class HallazgoCreate(BaseModel):
    descripcion: str
    clasificacion: str  # conformidad, no_conformidad_menor, no_conformidad_mayor, observacion
    evidencia: Optional[str] = None
    recomendacion: Optional[str] = None

class HallazgoResponse(BaseModel):
    id: UUID
    descripcion: str
    clasificacion: str
    evidencia: Optional[str]
    recomendacion: Optional[str]
    auditoria_id: UUID

    class Config:
        from_attributes = True


# ── No Conformidad ────────────────────────────────────────────────

class NoConformidadCreate(BaseModel):
    descripcion: str
    fecha_limite: datetime
    responsable_id: Optional[UUID] = None

class NoConformidadUpdate(BaseModel):
    estado: Optional[str] = None
    evidencia_cierre: Optional[str] = None

class NoConformidadResponse(BaseModel):
    id: UUID
    descripcion: str
    estado: str
    evidencia_cierre: Optional[str]
    fecha_limite: datetime
    fecha_cierre: Optional[datetime]
    hallazgo_id: UUID

    class Config:
        from_attributes = True