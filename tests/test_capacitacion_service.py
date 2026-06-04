# tests/test_capacitacion_service.py
import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.capacitacion import (
    AsistenciaCreate,
    CapacitacionCreate,
    CapacitacionUpdate,
    EvaluacionCreate,
    PreguntaCreate,
    ResponderEvaluacionRequest,
    RespuestaCreate,
    SesionCreate,
    SesionUpdate,
)
from app.services import capacitacion_service


def make_capacitacion(db, empresa, **kwargs):
    datos = CapacitacionCreate(
        titulo="Seguridad en alturas", duracion_horas=4, **kwargs
    )
    return capacitacion_service.create_capacitacion(db, datos, empresa.id)


def make_sesion(db, empresa, capacitacion=None):
    if capacitacion is None:
        from app.schemas.capacitacion import CapacitacionCreate

        cap = capacitacion_service.create_capacitacion(
            db, CapacitacionCreate(titulo="Cap test"), empresa.id
        )
    else:
        cap = capacitacion
    datos = SesionCreate(
        fecha=datetime.now(timezone.utc), lugar="Sala A", capacitacion_id=cap.id
    )
    return capacitacion_service.create_sesion(db, datos, empresa.id)


def make_evaluacion(db, sesion):
    datos = EvaluacionCreate(
        titulo="Evaluación básica",
        puntaje_minimo=60,
        sesion_id=sesion.id,
        preguntas=[
            PreguntaCreate(
                texto="¿Cuál es el color del casco de seguridad?",
                opcion_a="Rojo",
                opcion_b="Azul",
                opcion_c="Amarillo",
                opcion_d="Verde",
                respuesta_correcta="c",
            )
        ],
    )
    return capacitacion_service.create_evaluacion(db, datos)


# ── capacitaciones ──────────────────────────────────────────────────


def test_get_all_capacitaciones_vacio(db, empresa):
    resultado = capacitacion_service.get_all_capacitaciones(db, empresa.id)
    assert isinstance(resultado, list)


def test_get_all_capacitaciones_devuelve_activas_e_inactivas(db, empresa):
    cap = make_capacitacion(db, empresa)
    capacitacion_service.toggle_capacitacion(db, cap.id, empresa.id, False)
    make_capacitacion(db, empresa)
    todas = capacitacion_service.get_all_capacitaciones(db, empresa.id)
    activas = [c for c in todas if c.activo]
    inactivas = [c for c in todas if not c.activo]
    assert len(activas) >= 1
    assert len(inactivas) >= 1


def test_get_all_capacitaciones_filtro_activo(db, empresa):
    cap = make_capacitacion(db, empresa)
    capacitacion_service.toggle_capacitacion(db, cap.id, empresa.id, False)
    make_capacitacion(db, empresa)
    solo_activas = capacitacion_service.get_all_capacitaciones(
        db, empresa.id, activo=True
    )
    solo_inactivas = capacitacion_service.get_all_capacitaciones(
        db, empresa.id, activo=False
    )
    assert all(c.activo for c in solo_activas)
    assert all(not c.activo for c in solo_inactivas)


def test_create_capacitacion(db, empresa):
    cap = make_capacitacion(db, empresa)
    assert cap.titulo == "Seguridad en alturas"
    assert cap.empresa_id == empresa.id


def test_update_capacitacion_exitosa(db, empresa):
    cap = make_capacitacion(db, empresa)
    actualizada = capacitacion_service.update_capacitacion(
        db, cap.id, empresa.id, CapacitacionUpdate(titulo="Nuevo título")
    )
    assert actualizada.titulo == "Nuevo título"


def test_update_capacitacion_no_encontrada(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.update_capacitacion(
            db, uuid.uuid4(), empresa.id, CapacitacionUpdate(titulo="X")
        )
    assert exc.value.status_code == 404


def test_toggle_capacitacion_desactivar(db, empresa):
    cap = make_capacitacion(db, empresa)
    actualizada = capacitacion_service.toggle_capacitacion(
        db, cap.id, empresa.id, False
    )
    assert actualizada.activo is False


def test_toggle_capacitacion_no_encontrada(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.toggle_capacitacion(db, uuid.uuid4(), empresa.id, False)
    assert exc.value.status_code == 404


# ── sesiones ────────────────────────────────────────────────────────


def test_create_sesion_exitosa(db, empresa):
    cap = make_capacitacion(db, empresa)
    datos = SesionCreate(
        fecha=datetime.now(timezone.utc), lugar="Sala B", capacitacion_id=cap.id
    )
    sesion = capacitacion_service.create_sesion(db, datos, empresa.id)
    assert sesion.capacitacion_id == cap.id


def test_create_sesion_capacitacion_inexistente(db, empresa):
    from fastapi import HTTPException

    datos = SesionCreate(
        fecha=datetime.now(timezone.utc), lugar="Sala B", capacitacion_id=uuid.uuid4()
    )
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.create_sesion(db, datos, empresa.id)
    assert exc.value.status_code == 404


def test_get_sesiones_by_capacitacion(db, empresa):
    cap = make_capacitacion(db, empresa)
    make_sesion(db, empresa, cap)
    sesiones = capacitacion_service.get_sesiones_by_capacitacion(db, cap.id, empresa.id)
    assert len(sesiones) >= 1


def test_get_sesiones_capacitacion_inexistente(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.get_sesiones_by_capacitacion(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


def test_reprogramar_sesion(db, empresa):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    nueva_fecha = datetime(2025, 12, 1, 9, 0, tzinfo=timezone.utc)
    actualizada = capacitacion_service.reprogramar_sesion(
        db, sesion.id, empresa.id, SesionUpdate(fecha=nueva_fecha, lugar="Sala C")
    )
    assert actualizada.lugar == "Sala C"


def test_reprogramar_sesion_no_encontrada(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.reprogramar_sesion(
            db, uuid.uuid4(), empresa.id, SesionUpdate(lugar="Sala X")
        )
    assert exc.value.status_code == 404


# ── asistencia ──────────────────────────────────────────────────────


def test_registrar_asistencia_nueva(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    datos = AsistenciaCreate(
        sesion_id=sesion.id, empleado_id=usuario_sst.id, estado="presente"
    )
    asistencia = capacitacion_service.registrar_asistencia(db, datos)
    assert asistencia.empleado_id == usuario_sst.id


def test_registrar_asistencia_duplicada_actualiza(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    datos = AsistenciaCreate(
        sesion_id=sesion.id, empleado_id=usuario_sst.id, estado="presente"
    )
    capacitacion_service.registrar_asistencia(db, datos)
    datos.estado = "ausente"
    actualizada = capacitacion_service.registrar_asistencia(db, datos)
    assert actualizada.estado == "ausente"


def test_get_asistencia_by_sesion(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.registrar_asistencia(
        db, AsistenciaCreate(sesion_id=sesion.id, empleado_id=usuario_sst.id)
    )
    resultado = capacitacion_service.get_asistencia_by_sesion(db, sesion.id)
    assert len(resultado) >= 1


def test_get_historial_empleado(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.registrar_asistencia(
        db, AsistenciaCreate(sesion_id=sesion.id, empleado_id=usuario_sst.id)
    )
    historial = capacitacion_service.get_historial_empleado(db, usuario_sst.id)
    assert len(historial) >= 1


# ── evaluaciones ────────────────────────────────────────────────────


def test_create_evaluacion(db, empresa):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)
    assert evaluacion.sesion_id == sesion.id
    assert len(evaluacion.preguntas) == 1


def test_responder_evaluacion_aprobado(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)
    pregunta = evaluacion.preguntas[0]

    request = ResponderEvaluacionRequest(
        evaluacion_id=evaluacion.id,
        respuestas=[RespuestaCreate(pregunta_id=pregunta.id, respuesta_dada="c")],
    )
    resultado = capacitacion_service.responder_evaluacion(db, request, usuario_sst.id)
    assert resultado["aprobado"] is True
    assert resultado["puntaje_final"] == 100


def test_responder_evaluacion_reprobado(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)
    pregunta = evaluacion.preguntas[0]

    request = ResponderEvaluacionRequest(
        evaluacion_id=evaluacion.id,
        respuestas=[RespuestaCreate(pregunta_id=pregunta.id, respuesta_dada="a")],
    )
    resultado = capacitacion_service.responder_evaluacion(db, request, usuario_sst.id)
    assert resultado["aprobado"] is False
    assert resultado["puntaje_final"] == 0


def test_responder_evaluacion_no_encontrada(db, empresa, usuario_sst):
    from fastapi import HTTPException

    request = ResponderEvaluacionRequest(evaluacion_id=uuid.uuid4(), respuestas=[])
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.responder_evaluacion(db, request, usuario_sst.id)
    assert exc.value.status_code == 404


# ── cobertura ────────────────────────────────────────────────────────


def test_get_cobertura_sin_capacitaciones(db, empresa):
    resultado = capacitacion_service.get_cobertura_capacitaciones(db, empresa.id)
    assert resultado["total"] == 0
    assert resultado["porcentaje"] == 0


def test_get_cobertura_con_sesion(db, empresa):
    cap = make_capacitacion(db, empresa)
    make_sesion(db, empresa, cap)
    resultado = capacitacion_service.get_cobertura_capacitaciones(db, empresa.id)
    assert resultado["total"] >= 1
    assert resultado["con_sesiones"] >= 1
