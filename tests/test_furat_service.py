# tests/test_furat_service.py
from datetime import datetime, timezone

import pytest

from app.schemas.incidente import IncidenteCreate, InvestigacionCreate, LesionCreate
from app.services import furat_service, incidente_service


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


# ── generar_furat ───────────────────────────────────────────────────


def test_furat_basico_retorna_bytes(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    resultado = furat_service.generar_furat(db, inc.id, empresa.id)
    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


def test_furat_empieza_con_pdf(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    resultado = furat_service.generar_furat(db, inc.id, empresa.id)
    assert resultado[:4] == b"%PDF"


def test_furat_con_lesion(db, empresa, usuario_sst):
    datos = IncidenteCreate(
        tipo="accidente",
        severidad="moderada",
        fecha=datetime.now(timezone.utc),
        lugar="Bodega",
        descripcion="Golpe en mano",
        lesion=LesionCreate(
            tipo_lesion="contusion", parte_afectada="mano derecha", incapacidad_dias=5
        ),
    )
    inc = incidente_service.create_incidente(db, datos, empresa.id, usuario_sst.id)
    resultado = furat_service.generar_furat(db, inc.id, empresa.id)
    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


def test_furat_con_investigacion(db, empresa, usuario_sst):
    inc = make_incidente(db, empresa, usuario_sst)
    incidente_service.create_investigacion(
        db,
        inc.id,
        empresa.id,
        InvestigacionCreate(
            causas_inmediatas="Piso mojado",
            causas_basicas="Falta de señalización",
            lecciones_aprendidas="Instalar avisos de piso húmedo",
        ),
    )
    resultado = furat_service.generar_furat(db, inc.id, empresa.id)
    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


def test_furat_con_trabajador_afectado(db, empresa, usuario_sst):
    inc = make_incidente(
        db, empresa, usuario_sst, trabajador_afectado_id=usuario_sst.id
    )
    resultado = furat_service.generar_furat(db, inc.id, empresa.id)
    assert isinstance(resultado, bytes)
    assert len(resultado) > 0


def test_furat_incidente_inexistente(db, empresa):
    import uuid

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        furat_service.generar_furat(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404
