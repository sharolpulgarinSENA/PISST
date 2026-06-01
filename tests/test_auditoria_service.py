# tests/test_auditoria_service.py
import uuid
from datetime import datetime, timezone

import pytest

from app.schemas.auditoria import (
    AuditoriaCreate,
    HallazgoCreate,
    NoConformidadCreate,
    NoConformidadUpdate,
)
from app.services import auditoria_service


def make_auditoria(db, empresa, **kwargs):
    datos = AuditoriaCreate(
        objetivos="Verificar cumplimiento SG-SST",
        fecha_programada=datetime(2026, 6, 15, 9, 0, tzinfo=timezone.utc),
        **kwargs,
    )
    return auditoria_service.create_auditoria(db, datos, empresa.id)


def make_hallazgo(db, auditoria, **kwargs):
    datos = HallazgoCreate(
        descripcion="Falta señalización de emergencia",
        clasificacion="no_conformidad_menor",
        **kwargs,
    )
    return auditoria_service.create_hallazgo(
        db, auditoria.id, auditoria.empresa_id, datos
    )


# ── get_all_auditorias ──────────────────────────────────────────────


def test_get_all_auditorias_vacio(db, empresa):
    resultado = auditoria_service.get_all_auditorias(db, empresa.id)
    assert isinstance(resultado, list)


def test_get_all_auditorias_con_datos(db, empresa):
    make_auditoria(db, empresa)
    resultado = auditoria_service.get_all_auditorias(db, empresa.id)
    assert len(resultado) >= 1


# ── create / get_by_id ──────────────────────────────────────────────


def test_create_auditoria(db, empresa):
    auditoria = make_auditoria(db, empresa)
    assert auditoria.empresa_id == empresa.id
    assert auditoria.estado == "planificada"


def test_get_auditoria_by_id_encontrada(db, empresa):
    auditoria = make_auditoria(db, empresa)
    encontrada = auditoria_service.get_auditoria_by_id(db, auditoria.id, empresa.id)
    assert encontrada.id == auditoria.id


def test_get_auditoria_by_id_no_encontrada(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auditoria_service.get_auditoria_by_id(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── cambiar_estado_auditoria ────────────────────────────────────────


def test_cambiar_estado_a_en_ejecucion(db, empresa):
    auditoria = make_auditoria(db, empresa)
    actualizada = auditoria_service.cambiar_estado_auditoria(
        db, auditoria.id, empresa.id, "en_ejecucion"
    )
    assert actualizada.estado == "en_ejecucion"
    assert actualizada.fecha_ejecucion is not None


def test_cambiar_estado_a_completada(db, empresa):
    auditoria = make_auditoria(db, empresa)
    actualizada = auditoria_service.cambiar_estado_auditoria(
        db, auditoria.id, empresa.id, "completada"
    )
    assert actualizada.estado == "completada"


# ── hallazgos ───────────────────────────────────────────────────────


def test_create_hallazgo(db, empresa):
    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    assert hallazgo.auditoria_id == auditoria.id
    assert hallazgo.clasificacion == "no_conformidad_menor"


def test_create_hallazgo_auditoria_inexistente(db, empresa):
    from fastapi import HTTPException

    datos = HallazgoCreate(descripcion="Hallazgo X", clasificacion="observacion")
    with pytest.raises(HTTPException) as exc:
        auditoria_service.create_hallazgo(db, uuid.uuid4(), empresa.id, datos)
    assert exc.value.status_code == 404


def test_get_hallazgos_by_auditoria(db, empresa):
    auditoria = make_auditoria(db, empresa)
    make_hallazgo(db, auditoria)
    hallazgos = auditoria_service.get_hallazgos_by_auditoria(
        db, auditoria.id, empresa.id
    )
    assert len(hallazgos) == 1


# ── no conformidades ────────────────────────────────────────────────


def test_create_no_conformidad(db, empresa, usuario_sst):
    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    datos = NoConformidadCreate(
        descripcion="Sin extintor en el área",
        fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
        responsable_id=usuario_sst.id,
    )
    nc = auditoria_service.create_no_conformidad(db, hallazgo.id, datos)
    assert nc.hallazgo_id == hallazgo.id


def test_create_no_conformidad_hallazgo_inexistente(db):
    from fastapi import HTTPException

    datos = NoConformidadCreate(
        descripcion="NC X",
        fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(HTTPException) as exc:
        auditoria_service.create_no_conformidad(db, uuid.uuid4(), datos)
    assert exc.value.status_code == 404


def test_update_no_conformidad_sin_evidencia_falla(db, empresa, usuario_sst):
    from fastapi import HTTPException

    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    nc = auditoria_service.create_no_conformidad(
        db,
        hallazgo.id,
        NoConformidadCreate(
            descripcion="NC sin evidencia",
            fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ),
    )
    with pytest.raises(HTTPException) as exc:
        auditoria_service.update_no_conformidad(
            db, nc.id, NoConformidadUpdate(estado="cerrada")
        )
    assert exc.value.status_code == 400


def test_update_no_conformidad_cerrada(db, empresa, usuario_sst):
    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    nc = auditoria_service.create_no_conformidad(
        db,
        hallazgo.id,
        NoConformidadCreate(
            descripcion="NC con evidencia",
            fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ),
    )
    actualizada = auditoria_service.update_no_conformidad(
        db,
        nc.id,
        NoConformidadUpdate(estado="cerrada", evidencia_cierre="Extintor instalado"),
    )
    assert actualizada.estado == "cerrada"
    assert actualizada.fecha_cierre is not None


def test_update_no_conformidad_no_encontrada(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auditoria_service.update_no_conformidad(
            db, uuid.uuid4(), NoConformidadUpdate(estado="en_proceso")
        )
    assert exc.value.status_code == 404


# ── get_progreso_auditoria ──────────────────────────────────────────


def test_get_progreso_sin_hallazgos(db, empresa):
    auditoria = make_auditoria(db, empresa)
    progreso = auditoria_service.get_progreso_auditoria(db, auditoria.id, empresa.id)
    assert progreso["total_no_conformidades"] == 0
    assert progreso["porcentaje_cierre"] == 100


def test_get_progreso_con_nc_abierta(db, empresa):
    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    auditoria_service.create_no_conformidad(
        db,
        hallazgo.id,
        NoConformidadCreate(
            descripcion="NC abierta",
            fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ),
    )
    progreso = auditoria_service.get_progreso_auditoria(db, auditoria.id, empresa.id)
    assert progreso["total_no_conformidades"] == 1
    assert progreso["cerradas"] == 0
    assert progreso["porcentaje_cierre"] == 0


def test_get_progreso_con_nc_cerrada(db, empresa):
    auditoria = make_auditoria(db, empresa)
    hallazgo = make_hallazgo(db, auditoria)
    nc = auditoria_service.create_no_conformidad(
        db,
        hallazgo.id,
        NoConformidadCreate(
            descripcion="NC a cerrar",
            fecha_limite=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ),
    )
    auditoria_service.update_no_conformidad(
        db,
        nc.id,
        NoConformidadUpdate(estado="cerrada", evidencia_cierre="Acción tomada"),
    )
    progreso = auditoria_service.get_progreso_auditoria(db, auditoria.id, empresa.id)
    assert progreso["porcentaje_cierre"] == 100
