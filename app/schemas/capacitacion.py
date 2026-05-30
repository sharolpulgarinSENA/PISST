# app/schemas/capacitacion.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ── Área (respuesta embebida) ─────────────────────────────────────


class AreaSimple(BaseModel):
    id: UUID
    nombre: str

    model_config = ConfigDict(from_attributes=True)


# ── Capacitación ──────────────────────────────────────────────────


class CapacitacionCreate(BaseModel):
    titulo: str
    objetivos: Optional[str] = None
    duracion_horas: Optional[int] = 1
    facilitador_id: Optional[UUID] = None
    area_ids: Optional[List[UUID]] = []  # ✅ nuevo


class CapacitacionUpdate(BaseModel):
    activo: Optional[bool] = None
    titulo: Optional[str] = None  # ✅ nuevo
    objetivos: Optional[str] = None  # ✅ nuevo
    duracion_horas: Optional[int] = (
        None  # ✅ nuevo         # ✅ nuevo — para suspender/activar
    )


class CapacitacionResponse(BaseModel):
    id: UUID
    titulo: str
    objetivos: Optional[str]
    duracion_horas: int
    activo: bool
    empresa_id: UUID
    areas: List[AreaSimple] = []  # ✅ nuevo

    model_config = ConfigDict(from_attributes=True)


# ── Sesión ────────────────────────────────────────────────────────


class SesionCreate(BaseModel):
    fecha: datetime
    lugar: Optional[str] = None
    capacitacion_id: UUID


class SesionResponse(BaseModel):
    id: UUID
    fecha: datetime
    lugar: Optional[str]
    activa: bool
    capacitacion_id: UUID

    model_config = ConfigDict(from_attributes=True)


class SesionUpdate(BaseModel):
    fecha: Optional[datetime] = None
    lugar: Optional[str] = None


# ── Asistencia ────────────────────────────────────────────────────


class AsistenciaCreate(BaseModel):
    sesion_id: UUID
    empleado_id: UUID
    estado: Optional[str] = "presente"


class AsistenciaResponse(BaseModel):
    id: UUID
    estado: str
    sesion_id: UUID
    empleado_id: UUID
    fecha_registro: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Evaluación ────────────────────────────────────────────────────


class PreguntaCreate(BaseModel):
    texto: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str
    respuesta_correcta: str


class PreguntaResponse(BaseModel):
    id: UUID
    texto: str
    opcion_a: str
    opcion_b: str
    opcion_c: str
    opcion_d: str

    model_config = ConfigDict(from_attributes=True)


class EvaluacionCreate(BaseModel):
    titulo: str
    puntaje_minimo: Optional[int] = 60
    sesion_id: UUID
    preguntas: List[PreguntaCreate]


class EvaluacionResponse(BaseModel):
    id: UUID
    titulo: str
    puntaje_minimo: int
    sesion_id: UUID
    preguntas: List[PreguntaResponse]

    model_config = ConfigDict(from_attributes=True)


# ── Respuesta del Empleado ────────────────────────────────────────


class RespuestaCreate(BaseModel):
    pregunta_id: UUID
    respuesta_dada: str


class ResponderEvaluacionRequest(BaseModel):
    evaluacion_id: UUID
    respuestas: List[RespuestaCreate]


class ResultadoEvaluacionResponse(BaseModel):
    evaluacion_id: UUID
    empleado_id: UUID
    puntaje_final: int
    aprobado: bool
    total_preguntas: int
    respuestas_correctas: int
