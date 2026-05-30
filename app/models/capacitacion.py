# app/models/capacitacion.py
import uuid
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Integer,
    Boolean,
    ForeignKey,
    Table,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base


# ✅ Tabla intermedia capacitacion_areas (muchos a muchos)
capacitacion_areas = Table(
    "capacitacion_areas",
    Base.metadata,
    Column(
        "capacitacion_id",
        UUID(as_uuid=True),
        ForeignKey("capacitaciones.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "area_id",
        UUID(as_uuid=True),
        ForeignKey("areas.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Capacitacion(Base):
    __tablename__ = "capacitaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = Column(String(300), nullable=False)
    objetivos = Column(Text)
    duracion_horas = Column(Integer, default=1)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    empresa_id = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    facilitador_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    facilitador = relationship("User", foreign_keys=[facilitador_id])
    sesiones = relationship("SesionCapacitacion", back_populates="capacitacion")

    # ✅ Relación muchos a muchos con areas
    areas = relationship("Area", secondary=capacitacion_areas, lazy="joined")


class SesionCapacitacion(Base):
    __tablename__ = "sesiones_capacitacion"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fecha = Column(DateTime, nullable=False)
    lugar = Column(String(300))
    activa = Column(Boolean, default=True)
    fecha_creacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    capacitacion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("capacitaciones.id", ondelete="CASCADE"),
        nullable=False,
    )

    capacitacion = relationship("Capacitacion", back_populates="sesiones")
    asistencias = relationship("Asistencia", back_populates="sesion")
    evaluaciones = relationship("Evaluacion", back_populates="sesion")


class Asistencia(Base):
    __tablename__ = "asistencias"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estado = Column(String(20), default="presente")
    fecha_registro = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    sesion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sesiones_capacitacion.id", ondelete="CASCADE"),
        nullable=False,
    )
    empleado_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    sesion = relationship("SesionCapacitacion", back_populates="asistencias")
    empleado = relationship("User", foreign_keys=[empleado_id])


class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo = Column(String(300), nullable=False)
    puntaje_minimo = Column(Integer, default=60)
    fecha_creacion = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    sesion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sesiones_capacitacion.id", ondelete="CASCADE"),
        nullable=False,
    )

    sesion = relationship("SesionCapacitacion", back_populates="evaluaciones")
    preguntas = relationship("Pregunta", back_populates="evaluacion")


class Pregunta(Base):
    __tablename__ = "preguntas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    texto = Column(Text, nullable=False)
    opcion_a = Column(String(500), nullable=False)
    opcion_b = Column(String(500), nullable=False)
    opcion_c = Column(String(500), nullable=False)
    opcion_d = Column(String(500), nullable=False)
    respuesta_correcta = Column(String(1), nullable=False)

    evaluacion_id = Column(
        UUID(as_uuid=True),
        ForeignKey("evaluaciones.id", ondelete="CASCADE"),
        nullable=False,
    )

    evaluacion = relationship("Evaluacion", back_populates="preguntas")


class RespuestaEmpleado(Base):
    __tablename__ = "respuestas_empleado"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    respuesta_dada = Column(String(1), nullable=False)
    es_correcta = Column(Boolean, default=False)
    puntaje_final = Column(Integer, default=0)
    aprobado = Column(Boolean, default=False)
    fecha_respuesta = Column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )

    evaluacion_id = Column(
        UUID(as_uuid=True), ForeignKey("evaluaciones.id"), nullable=False
    )
    empleado_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    pregunta_id = Column(UUID(as_uuid=True), ForeignKey("preguntas.id"), nullable=False)

    empleado = relationship("User", foreign_keys=[empleado_id])
    evaluacion = relationship("Evaluacion", foreign_keys=[evaluacion_id])
    pregunta = relationship("Pregunta", foreign_keys=[pregunta_id])
