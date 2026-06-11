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


# ── tests datos reales (sin N/A) ────────────────────────────────────


def test_furat_contiene_datos_reales(db, empresa, usuario_sst):
    """El FURAT no debe contener el placeholder 'N/A'."""
    inc = make_incidente(db, empresa, usuario_sst)
    datos = furat_service._obtener_datos_furat(db, inc.id, empresa.id)
    assert "N/A" not in datos.values()


def test_furat_campos_obligatorios(db, empresa, usuario_sst):
    """Todos los campos obligatorios según Resolución 0156/2005 deben estar presentes."""
    inc = make_incidente(db, empresa, usuario_sst)
    datos = furat_service._obtener_datos_furat(db, inc.id, empresa.id)
    campos = [
        "razon_social",
        "nit",
        "ciudad",
        "direccion",
        "nombre_trabajador",
        "cargo_trabajador",
        "tipo_vinculacion",
        "fecha_accidente",
        "lugar",
        "tipo",
        "severidad",
        "descripcion",
        "tipo_lesion",
        "parte_afectada",
        "causas_inmediatas",
    ]
    for campo in campos:
        assert campo in datos, f"Campo obligatorio faltante: {campo}"


def test_furat_validacion_empresa(db, usuario_sst):
    """Los datos reales de empresa se reflejan en el dict FURAT."""
    import secrets as _sec

    from app.models.empresa import Empresa

    nit = _sec.token_hex(6)
    empresa = Empresa(
        nombre="Acería del Valle S.A.",
        nit=nit,
        sector="Manufactura",
        ciudad="Cali",
        direccion="Carrera 10 # 15-30",
        telefono="6022345678",
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)

    from app.core.security import get_password_hash
    from app.models.user import RoleEnum, User

    user = User(
        nombre="SST Cali",
        email=f"sst_{_sec.token_hex(4)}@test.com",
        password_hash=get_password_hash("Password1!"),
        role=RoleEnum.sst,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    inc = make_incidente(db, empresa, user)
    datos = furat_service._obtener_datos_furat(db, inc.id, empresa.id)

    assert datos["razon_social"] == "Acería del Valle S.A."
    assert datos["nit"] == nit
    assert datos["ciudad"] == "Cali"
    assert datos["direccion"] == "Carrera 10 # 15-30"
    assert datos["telefono_empresa"] == "6022345678"


def test_furat_validacion_incidente(db, empresa, usuario_sst):
    """Los datos del incidente y lesión se mapean correctamente al dict FURAT."""
    from app.schemas.incidente import LesionCreate

    datos_inc = IncidenteCreate(
        tipo="accidente",
        severidad="grave",
        fecha=datetime.now(timezone.utc),
        lugar="Zona de carga nivel 2",
        descripcion="Caída desde plataforma de trabajo",
        lesion=LesionCreate(
            tipo_lesion="fractura",
            parte_afectada="pierna izquierda",
            incapacidad_dias=30,
        ),
    )
    inc = incidente_service.create_incidente(db, datos_inc, empresa.id, usuario_sst.id)
    datos = furat_service._obtener_datos_furat(db, inc.id, empresa.id)

    assert datos["lugar"] == "Zona de carga nivel 2"
    assert datos["tipo"] == "accidente"
    assert datos["severidad"] == "grave"
    assert datos["tipo_lesion"] == "fractura"
    assert datos["parte_afectada"] == "pierna izquierda"
    assert datos["incapacidad_dias"] == "30"
