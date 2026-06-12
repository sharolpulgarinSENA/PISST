# tests/test_incidente_router.py
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.security import create_access_token, get_password_hash
from app.models.user import RoleEnum, User

# ── Helpers ────────────────────────────────────────────────────────


def crear_usuario(db, empresa, role=RoleEnum.sst):
    email = f"{role.value}_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        nombre="Test User",
        email=email,
        password_hash=get_password_hash("password123"),
        role=role,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth(user):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def payload_incidente(**kwargs):
    base = {
        "tipo": "accidente",
        "severidad": "leve",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "lugar": "Planta A",
        "descripcion": "Caída en escaleras",
    }
    base.update(kwargs)
    return base


def crear_incidente_via_api(client, headers, **kwargs):
    resp = client.post(
        "/incidentes/", json=payload_incidente(**kwargs), headers=headers
    )
    assert resp.status_code == 201
    return resp.json()


# ── GET /incidentes/ ───────────────────────────────────────────────


def test_listar_incidentes_vacio(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get("/incidentes/", headers=auth(sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_incidentes_con_filtros(client, db, empresa):
    sst = crear_usuario(db, empresa)
    crear_incidente_via_api(client, auth(sst))
    resp = client.get(
        "/incidentes/",
        params={"estado": "borrador", "tipo": "accidente"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_listar_incidentes_sin_auth(client):
    resp = client.get("/incidentes/")
    assert resp.status_code == 401


# ── POST /incidentes/ ──────────────────────────────────────────────


def test_crear_incidente_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post("/incidentes/", json=payload_incidente(), headers=auth(sst))
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo"] == "accidente"
    assert data["estado"] == "borrador"


def test_crear_incidente_con_lesion(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/incidentes/",
        json=payload_incidente(
            lesion={"tipo_lesion": "contusion", "parte_afectada": "rodilla"}
        ),
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["lesion"]["tipo_lesion"] == "contusion"


def test_crear_incidente_con_testigos(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/incidentes/",
        json=payload_incidente(
            testigos=[{"nombre": "Juan Pérez", "relato": "Vi todo"}]
        ),
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert len(resp.json()["testigos"]) == 1


def test_crear_incidente_empleado_puede(client, db, empresa):
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.post("/incidentes/", json=payload_incidente(), headers=auth(emp))
    assert resp.status_code == 201


def test_crear_incidente_sin_auth(client):
    resp = client.post("/incidentes/", json=payload_incidente())
    assert resp.status_code == 401


# ── GET /incidentes/{id} ───────────────────────────────────────────


def test_obtener_incidente_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.get(f"/incidentes/{inc['id']}", headers=auth(sst))
    assert resp.status_code == 200
    assert resp.json()["id"] == inc["id"]


def test_obtener_incidente_no_encontrado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get(f"/incidentes/{uuid.uuid4()}", headers=auth(sst))
    assert resp.status_code == 404


# ── PATCH /incidentes/{id}/estado ─────────────────────────────────


def test_cambiar_estado_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.patch(
        f"/incidentes/{inc['id']}/estado",
        json={"estado": "en_investigacion"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "en_investigacion"


def test_cambiar_estado_empleado_denegado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.patch(
        f"/incidentes/{inc['id']}/estado",
        json={"estado": "en_investigacion"},
        headers=auth(emp),
    )
    assert resp.status_code == 403


# ── GET /incidentes/{id}/progreso ─────────────────────────────────


def test_progreso_incidente(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.get(f"/incidentes/{inc['id']}/progreso", headers=auth(sst))
    assert resp.status_code == 200
    assert "porcentaje" in resp.json()


# ── POST /incidentes/{id}/investigacion ───────────────────────────


def test_crear_investigacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.post(
        f"/incidentes/{inc['id']}/investigacion",
        json={
            "causas_inmediatas": "Piso mojado",
            "causas_basicas": "Falta de señalización",
        },
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["causas_inmediatas"] == "Piso mojado"


def test_crear_investigacion_empleado_denegado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.post(
        f"/incidentes/{inc['id']}/investigacion",
        json={"causas_inmediatas": "X"},
        headers=auth(emp),
    )
    assert resp.status_code == 403


# ── GET /incidentes/{id}/investigacion ────────────────────────────


def test_obtener_investigacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    client.post(
        f"/incidentes/{inc['id']}/investigacion",
        json={"lecciones_aprendidas": "Limpiar el piso"},
        headers=auth(sst),
    )
    resp = client.get(f"/incidentes/{inc['id']}/investigacion", headers=auth(sst))
    assert resp.status_code == 200
    assert resp.json()["lecciones_aprendidas"] == "Limpiar el piso"


def test_obtener_investigacion_no_existe(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.get(f"/incidentes/{inc['id']}/investigacion", headers=auth(sst))
    assert resp.status_code == 404


# ── PATCH /incidentes/{id}/investigacion ──────────────────────────


def test_actualizar_investigacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    client.post(
        f"/incidentes/{inc['id']}/investigacion",
        json={"causas_inmediatas": "Original"},
        headers=auth(sst),
    )
    resp = client.patch(
        f"/incidentes/{inc['id']}/investigacion",
        json={"causas_inmediatas": "Actualizado"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["causas_inmediatas"] == "Actualizado"


# ── GET /incidentes/{id}/acciones ─────────────────────────────────


def test_listar_acciones_vacio(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.get(f"/incidentes/{inc['id']}/acciones", headers=auth(sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── POST /incidentes/{id}/acciones ────────────────────────────────


def test_crear_accion_correctiva_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    fecha_limite = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    resp = client.post(
        f"/incidentes/{inc['id']}/acciones",
        json={
            "descripcion": "Instalar señalización",
            "fecha_limite": fecha_limite,
            "responsable_id": str(sst.id),
        },
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["descripcion"] == "Instalar señalización"
    assert resp.json()["estado"] == "planificada"


def test_crear_accion_empleado_denegado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    inc = crear_incidente_via_api(client, auth(sst))
    fecha_limite = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    resp = client.post(
        f"/incidentes/{inc['id']}/acciones",
        json={
            "descripcion": "Acción no autorizada",
            "fecha_limite": fecha_limite,
            "responsable_id": str(sst.id),
        },
        headers=auth(emp),
    )
    assert resp.status_code == 403


# ── PATCH /incidentes/acciones/{id} ───────────────────────────────


def test_actualizar_accion_pendiente_a_en_progreso(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    fecha_limite = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    accion = client.post(
        f"/incidentes/{inc['id']}/acciones",
        json={
            "descripcion": "Acción test",
            "fecha_limite": fecha_limite,
            "responsable_id": str(sst.id),
        },
        headers=auth(sst),
    ).json()

    resp = client.patch(
        f"/incidentes/acciones/{accion['id']}",
        json={"estado": "en_ejecucion"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "en_ejecucion"


def test_completar_accion_con_evidencia(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    fecha_limite = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    accion = client.post(
        f"/incidentes/{inc['id']}/acciones",
        json={
            "descripcion": "Acción a completar",
            "fecha_limite": fecha_limite,
            "responsable_id": str(sst.id),
        },
        headers=auth(sst),
    ).json()

    resp = client.patch(
        f"/incidentes/acciones/{accion['id']}",
        json={"estado": "completada", "evidencia": "Foto adjunta"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "completada"


# ── GET /incidentes/{id}/furat ────────────────────────────────────


def test_descargar_furat_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    inc = crear_incidente_via_api(client, auth(sst))
    with patch("app.routers.incidente_router.furat_service.generar_furat") as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4 fake content"
        resp = client.get(f"/incidentes/{inc['id']}/furat", headers=auth(sst))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"


def test_descargar_furat_empleado_denegado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    inc = crear_incidente_via_api(client, auth(sst))
    resp = client.get(f"/incidentes/{inc['id']}/furat", headers=auth(emp))
    assert resp.status_code == 403
