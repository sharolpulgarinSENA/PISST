# app/schemas/incidente.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.accion_correctiva import EstadoAccionEnum, PrioridadAccionEnum
from app.models.incidente import EstadoIncidenteEnum, SeveridadEnum, TipoIncidenteEnum

# ── Schemas de Lesión ─────────────────────────────────────────────


class LesionCreate(BaseModel):
    tipo_lesion: Optional[str] = None
    parte_afectada: Optional[str] = None
    incapacidad_dias: Optional[int] = 0


class LesionResponse(BaseModel):
    id: UUID
    tipo_lesion: Optional[str]
    parte_afectada: Optional[str]
    incapacidad_dias: int

    model_config = ConfigDict(from_attributes=True)


# ── Schemas de Testigo ────────────────────────────────────────────


class TestigoCreate(BaseModel):
    nombre: str
    relato: Optional[str] = None


class TestigoResponse(BaseModel):
    id: UUID
    nombre: str
    relato: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ── Schemas de Incidente ──────────────────────────────────────────


class IncidenteCreate(BaseModel):
    tipo: TipoIncidenteEnum
    severidad: SeveridadEnum
    fecha: datetime
    lugar: str
    descripcion: str
    trabajador_afectado_id: Optional[UUID] = None
    lesion: Optional[LesionCreate] = None
    testigos: Optional[list[TestigoCreate]] = []


class IncidenteUpdate(BaseModel):
    lugar: Optional[str] = None
    descripcion: Optional[str] = None
    severidad: Optional[SeveridadEnum] = None


class IncidenteEstadoUpdate(BaseModel):
    estado: EstadoIncidenteEnum


class IncidenteResponse(BaseModel):
    id: UUID
    tipo: str
    severidad: str
    fecha: datetime
    lugar: str
    descripcion: str
    estado: str
    fecha_creacion: datetime
    empresa_id: UUID
    reportado_por_id: UUID
    trabajador_afectado_id: Optional[UUID]
    lesion: Optional[LesionResponse]
    testigos: list[TestigoResponse]
    creado_por_nombre: Optional[str] = None
    creado_por_rol: Optional[str] = None
    creado_por_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_with_creator(cls, incidente) -> "IncidenteResponse":
        obj = cls.model_validate(incidente)
        if incidente.reportado_por:
            obj.creado_por_nombre = incidente.reportado_por.nombre
            obj.creado_por_rol = incidente.reportado_por.role.value
            obj.creado_por_id = incidente.reportado_por.id
        return obj


# ── Schemas de Investigación ──────────────────────────────────────


class InvestigacionCreate(BaseModel):
    metodo_analisis: Optional[str] = "5_por_que"
    causas_inmediatas: Optional[str] = None
    causas_basicas: Optional[str] = None
    factores_contribuyentes: Optional[str] = None
    descripcion_evento: Optional[str] = None
    lecciones_aprendidas: Optional[str] = None


class InvestigacionUpdate(BaseModel):
    metodo_analisis: Optional[str] = None
    causas_inmediatas: Optional[str] = None
    causas_basicas: Optional[str] = None
    factores_contribuyentes: Optional[str] = None
    descripcion_evento: Optional[str] = None
    lecciones_aprendidas: Optional[str] = None


class InvestigacionResponse(BaseModel):
    id: UUID
    metodo_analisis: str
    causas_inmediatas: Optional[str]
    causas_basicas: Optional[str]
    factores_contribuyentes: Optional[str]
    descripcion_evento: Optional[str]
    lecciones_aprendidas: Optional[str]
    incidente_id: UUID

    model_config = ConfigDict(from_attributes=True)


# ── Schemas de Acción Correctiva ──────────────────────────────────


class AccionCorrectivaCreate(BaseModel):
    descripcion: str
    prioridad: Optional[PrioridadAccionEnum] = PrioridadAccionEnum.media
    fecha_limite: datetime
    responsable_id: UUID


class AccionCorrectivaUpdate(BaseModel):
    descripcion: Optional[str] = None
    prioridad: Optional[PrioridadAccionEnum] = None
    estado: Optional[EstadoAccionEnum] = None
    evidencia: Optional[str] = None
    fecha_limite: Optional[datetime] = None


class AccionCorrectivaResponse(BaseModel):
    id: UUID
    descripcion: str
    estado: str
    prioridad: str
    fecha_limite: datetime
    fecha_cierre: Optional[datetime]
    evidencia: Optional[str]
    incidente_id: UUID
    responsable_id: UUID

    model_config = ConfigDict(from_attributes=True)
