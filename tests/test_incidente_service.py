# tests/test_incidente_service.py
from datetime import datetime, timezone

import pytest

from app.schemas.incidente import (
    AccionCorrectivaCreate,
    AccionCorrectivaUpdate,
    IncidenteCreate,
    InvestigacionCreate,
    LesionCreate,
    TestigoCreate,
)
from app.services import incidente_service


def make_incidente(db, empresa, usuario_sst, **kwargs):
    datos = IncidenteCreate(
        tipo="accidente",
        severidad="leve",
        fecha=datetime.now(timezone.utc),
        lugar="Planta A",
        descripcion="Caída en escaleras",
        **kwargs,
    )
    return incidente_service.create_incidente(db, datos, empresa.id, usuario_sst.id)


# ── get_all_incidentes ──────────────────────────────────────────────


def test_get_all_incidentes_vacio(db, empresa):
    resultado = incidente_service.get_all_incidentes(db, empresa.id)
    assert isinstance(resultado, list)


def test_get_all_incidentes_con_filtros(db, empresa, usuario_sst):
    make_incidente(db, empresa, usuario_sst)
    resultado = incidente_service.get_all_incidentes(
        db, empresa.id, estado="abierto", tipo="accidente"
    )
    assert isinstance(resultado, list)


# ── get_incidente_by_id ─────────────────────────────────────────────


def test_get_incidente_by_id_encontrado(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    encontrado = incidente_service.get_incidente_by_id(db, inc.id, empresa.id)
    assert encontrado.id == inc.id


def test_get_incidente_by_id_no_encontrado(db, empresa):
    import uuid

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        incidente_service.get_incidente_by_id(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── create_incidente ────────────────────────────────────────────────


def test_create_incidente_basico(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    assert inc.tipo == "accidente"
    assert inc.empresa_id == empresa.id


def test_create_incidente_con_lesion(db, empresa, usuario_sst):
    datos = IncidenteCreate(
        tipo="accidente",
        severidad="moderada",
        fecha=datetime.now(timezone.utc),
        lugar="Bodega",
        descripcion="Golpe en la cabeza",
        lesion=LesionCreate(
            tipo_lesion="contusion", parte_afectada="cabeza", incapacidad_dias=3
        ),
    )
    inc = incidente_service.create_incidente(db, datos, empresa.id, usuario_sst.id)
    assert inc.lesion is not None
    assert inc.lesion.tipo_lesion == "contusion"


def test_create_incidente_con_testigos(db, empresa, usuario_sst):
    datos = IncidenteCreate(
        tipo="incidente",
        severidad="sin_lesion",
        fecha=datetime.now(timezone.utc),
        lugar="Oficina",
        descripcion="Derrame de químicos",
        testigos=[TestigoCreate(nombre="Juan Pérez", relato="Vi todo")],
    )
    inc = incidente_service.create_incidente(db, datos, empresa.id, usuario_sst.id)
    assert len(inc.testigos) == 1


# ── update_estado_incidente ─────────────────────────────────────────


def test_update_estado_incidente(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    actualizado = incidente_service.update_estado_incidente(
        db, inc.id, empresa.id, "en_revision"
    )
    assert actualizado.estado == "en_revision"


def test_cerrar_incidente_sin_investigacion_falla(db, empresa, usuario_sst):
    from fastapi import HTTPException

    inc = make_incidente(db, empresa, usuario_sst)
    with pytest.raises(HTTPException) as exc:
        incidente_service.update_estado_incidente(db, inc.id, empresa.id, "cerrado")
    assert exc.value.status_code == 400


def test_cerrar_incidente_con_investigacion(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    incidente_service.create_investigacion(
        db, inc.id, empresa.id, InvestigacionCreate(causas_inmediatas="Piso mojado")
    )
    actualizado = incidente_service.update_estado_incidente(
        db, inc.id, empresa.id, "cerrado"
    )
    assert actualizado.estado == "cerrado"


# ── create_investigacion ────────────────────────────────────────────


def test_create_investigacion_exitosa(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    inv = incidente_service.create_investigacion(
        db, inc.id, empresa.id, InvestigacionCreate(causas_inmediatas="Falta de EPP")
    )
    assert inv.incidente_id == inc.id


def test_create_investigacion_duplicada_falla(db, empresa, usuario_sst):
    from fastapi import HTTPException

    inc = make_incidente(db, empresa, usuario_sst)
    incidente_service.create_investigacion(
        db, inc.id, empresa.id, InvestigacionCreate(causas_inmediatas="Falta de EPP")
    )
    with pytest.raises(HTTPException) as exc:
        incidente_service.create_investigacion(
            db, inc.id, empresa.id, InvestigacionCreate(causas_inmediatas="Otra causa")
        )
    assert exc.value.status_code == 400


# ── acciones correctivas ────────────────────────────────────────────


def test_create_accion_correctiva(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    datos = AccionCorrectivaCreate(
        descripcion="Instalar baranda",
        prioridad="alta",
        fecha_limite=datetime.now(timezone.utc),
        responsable_id=usuario_sst.id,
    )
    accion = incidente_service.create_accion_correctiva(db, inc.id, empresa.id, datos)
    assert accion.incidente_id == inc.id


def test_update_accion_correctiva_sin_evidencia_falla(db, empresa, usuario_sst):
    from fastapi import HTTPException

    inc = make_incidente(db, empresa, usuario_sst)
    datos_create = AccionCorrectivaCreate(
        descripcion="Señalizar área",
        fecha_limite=datetime.now(timezone.utc),
        responsable_id=usuario_sst.id,
    )
    accion = incidente_service.create_accion_correctiva(
        db, inc.id, empresa.id, datos_create
    )
    with pytest.raises(HTTPException) as exc:
        incidente_service.update_accion_correctiva(
            db, accion.id, empresa.id, AccionCorrectivaUpdate(estado="completada")
        )
    assert exc.value.status_code == 400


def test_update_accion_correctiva_completada(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    datos_create = AccionCorrectivaCreate(
        descripcion="Señalizar área",
        fecha_limite=datetime.now(timezone.utc),
        responsable_id=usuario_sst.id,
    )
    accion = incidente_service.create_accion_correctiva(
        db, inc.id, empresa.id, datos_create
    )
    actualizada = incidente_service.update_accion_correctiva(
        db,
        accion.id,
        empresa.id,
        AccionCorrectivaUpdate(estado="completada", evidencia="Foto adjunta"),
    )
    assert actualizada.estado == "completada"
    assert actualizada.fecha_cierre is not None


def test_update_accion_correctiva_no_encontrada(db, empresa):
    import uuid

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        incidente_service.update_accion_correctiva(
            db, uuid.uuid4(), empresa.id, AccionCorrectivaUpdate(descripcion="X")
        )
    assert exc.value.status_code == 404


# ── get_progreso_incidente ──────────────────────────────────────────


def test_get_progreso_sin_acciones(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    progreso = incidente_service.get_progreso_incidente(db, inc.id, empresa.id)
    assert progreso["total"] == 0
    assert progreso["porcentaje"] == 0


def test_get_progreso_con_acciones(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    datos_create = AccionCorrectivaCreate(
        descripcion="Acción 1",
        fecha_limite=datetime.now(timezone.utc),
        responsable_id=usuario_sst.id,
    )
    accion = incidente_service.create_accion_correctiva(
        db, inc.id, empresa.id, datos_create
    )
    incidente_service.update_accion_correctiva(
        db,
        accion.id,
        empresa.id,
        AccionCorrectivaUpdate(estado="completada", evidencia="Evidencia"),
    )
    progreso = incidente_service.get_progreso_incidente(db, inc.id, empresa.id)
    assert progreso["total"] == 1
    assert progreso["completadas"] == 1
    assert progreso["porcentaje"] == 100
