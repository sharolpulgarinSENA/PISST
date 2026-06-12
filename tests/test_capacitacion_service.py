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


def test_reprogramar_sesion_no_programada_falla(db, empresa):
    from fastapi import HTTPException

    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.cambiar_estado_sesion(db, sesion.id, empresa.id, "realizada")
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.reprogramar_sesion(
            db, sesion.id, empresa.id, SesionUpdate(lugar="Sala X")
        )
    assert exc.value.status_code == 400


# ── cambiar_estado_sesion ────────────────────────────────────────────


def test_cambiar_estado_sesion_valido(db, empresa):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    assert sesion.estado == "programada"
    actualizada = capacitacion_service.cambiar_estado_sesion(
        db, sesion.id, empresa.id, "realizada"
    )
    assert actualizada.estado == "realizada"


def test_cambiar_estado_todos_los_valores(db, empresa):
    cap = make_capacitacion(db, empresa)
    for estado in ["realizada", "no_realizada", "cancelada", "programada"]:
        sesion = make_sesion(db, empresa, cap)
        resultado = capacitacion_service.cambiar_estado_sesion(
            db, sesion.id, empresa.id, estado
        )
        assert resultado.estado == estado


def test_cambiar_estado_invalido_422(db, empresa):
    from fastapi import HTTPException

    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.cambiar_estado_sesion(
            db, sesion.id, empresa.id, "estado_inventado"
        )
    assert exc.value.status_code == 422


def test_cambiar_estado_sesion_inexistente_404(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.cambiar_estado_sesion(
            db, uuid.uuid4(), empresa.id, "realizada"
        )
    assert exc.value.status_code == 404


# ── asistencia ──────────────────────────────────────────────────────


def test_registrar_asistencia_nueva(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    datos = AsistenciaCreate(
        sesion_id=sesion.id, empleado_id=usuario_sst.id, estado="presente"
    )
    asistencia = capacitacion_service.registrar_asistencia(db, datos, empresa.id)
    assert asistencia.empleado_id == usuario_sst.id


def test_registrar_asistencia_duplicada_actualiza(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    datos = AsistenciaCreate(
        sesion_id=sesion.id, empleado_id=usuario_sst.id, estado="presente"
    )
    capacitacion_service.registrar_asistencia(db, datos, empresa.id)
    datos.estado = "ausente"
    actualizada = capacitacion_service.registrar_asistencia(db, datos, empresa.id)
    assert actualizada.estado == "ausente"


def test_get_asistencia_by_sesion(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.registrar_asistencia(
        db,
        AsistenciaCreate(sesion_id=sesion.id, empleado_id=usuario_sst.id),
        empresa.id,
    )
    resultado = capacitacion_service.get_asistencia_by_sesion(db, sesion.id, empresa.id)
    assert len(resultado) >= 1


def test_get_historial_empleado(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.registrar_asistencia(
        db,
        AsistenciaCreate(sesion_id=sesion.id, empleado_id=usuario_sst.id),
        empresa.id,
    )
    historial = capacitacion_service.get_historial_empleado(
        db, usuario_sst.id, empresa.id
    )
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
    resultado = capacitacion_service.responder_evaluacion(
        db, request, usuario_sst.id, empresa.id
    )
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
    resultado = capacitacion_service.responder_evaluacion(
        db, request, usuario_sst.id, empresa.id
    )
    assert resultado["aprobado"] is False
    assert resultado["puntaje_final"] == 0


def test_responder_evaluacion_no_encontrada(db, empresa, usuario_sst):
    from fastapi import HTTPException

    request = ResponderEvaluacionRequest(evaluacion_id=uuid.uuid4(), respuestas=[])
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.responder_evaluacion(
            db, request, usuario_sst.id, empresa.id
        )
    assert exc.value.status_code == 404


# ── cobertura ────────────────────────────────────────────────────────


def test_get_cobertura_sin_capacitaciones(db, empresa):
    resultado = capacitacion_service.get_cobertura_capacitaciones(db, empresa.id)
    assert resultado["total"] == 0
    assert resultado["porcentaje"] == 0


def test_get_cobertura_sesion_programada_no_cuenta(db, empresa):
    cap = make_capacitacion(db, empresa)
    make_sesion(db, empresa, cap)  # estado="programada" por defecto
    resultado = capacitacion_service.get_cobertura_capacitaciones(db, empresa.id)
    assert resultado["total"] >= 1
    assert resultado["completadas"] == 0
    assert resultado["porcentaje"] == 0


def test_get_cobertura_sesion_realizada_cuenta(db, empresa):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.cambiar_estado_sesion(db, sesion.id, empresa.id, "realizada")
    resultado = capacitacion_service.get_cobertura_capacitaciones(db, empresa.id)
    assert resultado["total"] >= 1
    assert resultado["completadas"] >= 1
    assert resultado["porcentaje"] > 0


# ── create_capacitacion con area_ids (líneas 48-49) ────────────────


def test_create_capacitacion_con_area_ids(db, empresa):
    from app.models.area import Area

    area = Area(nombre="Área test cov", empresa_id=empresa.id)
    db.add(area)
    db.commit()
    db.refresh(area)

    cap = make_capacitacion(db, empresa, area_ids=[area.id])
    assert len(cap.areas) == 1
    assert cap.areas[0].id == area.id


# ── update_capacitacion — ramas activo / objetivos / duracion (líneas 69, 73, 75) ──


def test_update_capacitacion_activo(db, empresa):
    cap = make_capacitacion(db, empresa)
    actualizada = capacitacion_service.update_capacitacion(
        db, cap.id, empresa.id, CapacitacionUpdate(activo=False)
    )
    assert actualizada.activo is False


def test_update_capacitacion_objetivos_y_duracion(db, empresa):
    cap = make_capacitacion(db, empresa)
    actualizada = capacitacion_service.update_capacitacion(
        db,
        cap.id,
        empresa.id,
        CapacitacionUpdate(objetivos="Nuevos objetivos", duracion_horas=8),
    )
    assert actualizada.objetivos == "Nuevos objetivos"
    assert actualizada.duracion_horas == 8


# ── registrar_asistencia — sesión y empleado no encontrados (líneas 214, 223) ──


def test_registrar_asistencia_sesion_inexistente(db, empresa, usuario_sst):
    from fastapi import HTTPException

    datos = AsistenciaCreate(
        sesion_id=uuid.uuid4(), empleado_id=usuario_sst.id, estado="presente"
    )
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.registrar_asistencia(db, datos, empresa.id)
    assert exc.value.status_code == 404


def test_registrar_asistencia_empleado_inexistente(db, empresa):
    from fastapi import HTTPException

    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    datos = AsistenciaCreate(
        sesion_id=sesion.id, empleado_id=uuid.uuid4(), estado="presente"
    )
    with pytest.raises(HTTPException) as exc:
        capacitacion_service.registrar_asistencia(db, datos, empresa.id)
    assert exc.value.status_code == 404


# ── get_asistencia_by_sesion — sesión no encontrada (línea 260) ────


def test_get_asistencia_sesion_inexistente(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.get_asistencia_by_sesion(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── get_historial_empleado — empleado no encontrado (línea 271) ────


def test_get_historial_empleado_inexistente(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.get_historial_empleado(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── get_historial_empleado con evaluacion respondida (líneas 290-319) ──


def test_get_historial_empleado_con_evaluacion_aprobada(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    capacitacion_service.registrar_asistencia(
        db,
        AsistenciaCreate(
            sesion_id=sesion.id, empleado_id=usuario_sst.id, estado="presente"
        ),
        empresa.id,
    )
    evaluacion = make_evaluacion(db, sesion)
    pregunta = evaluacion.preguntas[0]
    capacitacion_service.responder_evaluacion(
        db,
        ResponderEvaluacionRequest(
            evaluacion_id=evaluacion.id,
            respuestas=[RespuestaCreate(pregunta_id=pregunta.id, respuesta_dada="c")],
        ),
        usuario_sst.id,
        empresa.id,
    )
    historial = capacitacion_service.get_historial_empleado(
        db, usuario_sst.id, empresa.id
    )
    assert len(historial) >= 1
    entrada = next(h for h in historial if h["evaluacion_id"] == str(evaluacion.id))
    assert entrada["evaluacion"] is not None
    assert entrada["resultado"]["aprobado"] is True


# ── responder_evaluacion — pregunta_id inválido salta continue (línea 390) ──


def test_responder_evaluacion_pregunta_inexistente_se_salta(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)

    resultado = capacitacion_service.responder_evaluacion(
        db,
        ResponderEvaluacionRequest(
            evaluacion_id=evaluacion.id,
            respuestas=[RespuestaCreate(pregunta_id=uuid.uuid4(), respuesta_dada="a")],
        ),
        usuario_sst.id,
        empresa.id,
    )
    assert resultado["puntaje_final"] == 0


# ── generar_certificado (líneas 468-581) ──────────────────────────


def test_generar_certificado_ok(db, empresa, usuario_sst):
    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)
    pregunta = evaluacion.preguntas[0]
    capacitacion_service.responder_evaluacion(
        db,
        ResponderEvaluacionRequest(
            evaluacion_id=evaluacion.id,
            respuestas=[RespuestaCreate(pregunta_id=pregunta.id, respuesta_dada="c")],
        ),
        usuario_sst.id,
        empresa.id,
    )
    buffer = capacitacion_service.generar_certificado(db, evaluacion.id, usuario_sst.id)
    contenido = buffer.read()
    assert contenido[:4] == b"%PDF"


def test_generar_certificado_no_aprobado_lanza_404(db, empresa, usuario_sst):
    from fastapi import HTTPException

    cap = make_capacitacion(db, empresa)
    sesion = make_sesion(db, empresa, cap)
    evaluacion = make_evaluacion(db, sesion)

    with pytest.raises(HTTPException) as exc:
        capacitacion_service.generar_certificado(db, evaluacion.id, usuario_sst.id)
    assert exc.value.status_code == 404
