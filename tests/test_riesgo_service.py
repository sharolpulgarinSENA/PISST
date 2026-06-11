# tests/test_riesgo_service.py
import uuid

import pytest

from app.schemas.riesgo import (
    EvaluacionRiesgoCreate,
    MedidaControlCreate,
    MedidaControlUpdate,
    PeligroCreate,
)
from app.services import riesgo_service


def make_peligro(db, empresa, **kwargs):
    datos = PeligroCreate(
        descripcion="Ruido excesivo en planta",
        tipo="fisico",
        trabajadores_expuestos=10,
        **kwargs,
    )
    return riesgo_service.create_peligro(db, datos, empresa.id)


# ── calcular_nivel_riesgo ───────────────────────────────────────────


def test_nivel_bajo():
    assert riesgo_service.calcular_nivel_riesgo(1, 1).value == "bajo"


def test_nivel_medio():
    assert riesgo_service.calcular_nivel_riesgo(3, 3).value == "medio"


def test_nivel_alto():
    assert riesgo_service.calcular_nivel_riesgo(4, 4).value == "alto"


def test_nivel_critico():
    assert riesgo_service.calcular_nivel_riesgo(5, 5).value == "critico"


# ── peligros ────────────────────────────────────────────────────────


def test_get_all_peligros_vacio(db, empresa):
    resultado = riesgo_service.get_all_peligros(db, empresa.id)
    assert isinstance(resultado, list)


def test_create_peligro(db, empresa):
    peligro = make_peligro(db, empresa)
    assert peligro.descripcion == "Ruido excesivo en planta"
    assert peligro.empresa_id == empresa.id


def test_get_all_peligros_con_filtro_tipo(db, empresa):
    make_peligro(db, empresa)
    resultado = riesgo_service.get_all_peligros(db, empresa.id, tipo="fisico")
    assert len(resultado) >= 1


def test_get_peligro_by_id_encontrado(db, empresa):
    peligro = make_peligro(db, empresa)
    encontrado = riesgo_service.get_peligro_by_id(db, peligro.id, empresa.id)
    assert encontrado.id == peligro.id


def test_get_peligro_by_id_no_encontrado(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        riesgo_service.get_peligro_by_id(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── evaluaciones de riesgo ──────────────────────────────────────────


def test_create_evaluacion_riesgo(db, empresa):
    peligro = make_peligro(db, empresa)
    datos = EvaluacionRiesgoCreate(probabilidad=4, severidad=4)
    evaluacion = riesgo_service.create_evaluacion_riesgo(
        db, peligro.id, empresa.id, datos
    )
    assert evaluacion.peligro_id == peligro.id
    assert evaluacion.nivel_riesgo.value == "alto"


def test_create_evaluacion_peligro_inexistente(db, empresa):
    from fastapi import HTTPException

    datos = EvaluacionRiesgoCreate(probabilidad=2, severidad=2)
    with pytest.raises(HTTPException) as exc:
        riesgo_service.create_evaluacion_riesgo(db, uuid.uuid4(), empresa.id, datos)
    assert exc.value.status_code == 404


# ── matriz de riesgos ───────────────────────────────────────────────


def test_get_matriz_riesgos_vacia(db, empresa):
    resultado = riesgo_service.get_matriz_riesgos(db, empresa.id)
    assert "total_peligros" in resultado
    assert resultado["total_peligros"] == 0


def test_get_matriz_riesgos_con_datos(db, empresa):
    peligro = make_peligro(db, empresa)
    riesgo_service.create_evaluacion_riesgo(
        db, peligro.id, empresa.id, EvaluacionRiesgoCreate(probabilidad=5, severidad=5)
    )
    resultado = riesgo_service.get_matriz_riesgos(db, empresa.id)
    assert resultado["criticos"] >= 1


# ── medidas de control ──────────────────────────────────────────────


def test_create_medida_control(db, empresa):
    peligro = make_peligro(db, empresa)
    datos = MedidaControlCreate(descripcion="Usar protectores auditivos", tipo="epp")
    medida = riesgo_service.create_medida_control(db, peligro.id, empresa.id, datos)
    assert medida.peligro_id == peligro.id
    assert medida.tipo == "epp"


def test_create_medida_peligro_inexistente(db, empresa):
    from fastapi import HTTPException

    datos = MedidaControlCreate(descripcion="Medida X", tipo="administrativo")
    with pytest.raises(HTTPException) as exc:
        riesgo_service.create_medida_control(db, uuid.uuid4(), empresa.id, datos)
    assert exc.value.status_code == 404


def test_update_medida_control_sin_evidencia_falla(db, empresa):
    from fastapi import HTTPException

    peligro = make_peligro(db, empresa)
    medida = riesgo_service.create_medida_control(
        db,
        peligro.id,
        empresa.id,
        MedidaControlCreate(descripcion="Rotular zona", tipo="administrativo"),
    )
    with pytest.raises(HTTPException) as exc:
        riesgo_service.update_medida_control(
            db, medida.id, empresa.id, MedidaControlUpdate(estado="completada")
        )
    assert exc.value.status_code == 400


def test_update_medida_control_completada(db, empresa):
    peligro = make_peligro(db, empresa)
    medida = riesgo_service.create_medida_control(
        db,
        peligro.id,
        empresa.id,
        MedidaControlCreate(descripcion="Rotular zona", tipo="administrativo"),
    )
    actualizada = riesgo_service.update_medida_control(
        db,
        medida.id,
        empresa.id,
        MedidaControlUpdate(estado="completada", evidencia="Foto del letrero"),
    )
    assert actualizada.estado == "completada"


def test_update_medida_control_no_encontrada(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        riesgo_service.update_medida_control(
            db, uuid.uuid4(), empresa.id, MedidaControlUpdate(descripcion="X")
        )
    assert exc.value.status_code == 404
