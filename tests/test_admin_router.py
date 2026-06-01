# tests/test_admin_router.py
import secrets
import uuid
from datetime import datetime
from unittest.mock import patch

import pytest

from app.core.security import get_password_hash
from app.models.user import RoleEnum, User

ADMIN_KEY = "test-admin-key-sprint7"


@pytest.fixture(autouse=True)
def set_admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET_KEY", ADMIN_KEY)


def h():
    return {"X-Admin-Key": ADMIN_KEY}


def nueva_empresa(client, nombre=None, nit=None):
    resp = client.post(
        "/admin/empresas",
        json={"nombre": nombre or "Empresa Test", "nit": nit or secrets.token_hex(6)},
        headers=h(),
    )
    return resp.json()["empresa_id"]


# ── /admin/empresas ──────────────────────────────────────────────────


def test_crear_empresa(client):
    resp = client.post(
        "/admin/empresas",
        json={
            "nombre": "Empresa A",
            "nit": secrets.token_hex(6),
            "sector": "Manufactura",
        },
        headers=h(),
    )
    assert resp.status_code == 201
    assert resp.json()["mensaje"] == "Empresa creada exitosamente"


def test_crear_empresa_nit_duplicado(client):
    nit = secrets.token_hex(6)
    client.post("/admin/empresas", json={"nombre": "Emp 1", "nit": nit}, headers=h())
    resp = client.post(
        "/admin/empresas", json={"nombre": "Emp 2", "nit": nit}, headers=h()
    )
    assert resp.status_code == 400


def test_crear_empresa_sin_header_falla(client):
    resp = client.post("/admin/empresas", json={"nombre": "X", "nit": "999"})
    assert resp.status_code == 422


def test_crear_empresa_clave_incorrecta(client):
    resp = client.post(
        "/admin/empresas",
        json={"nombre": "X", "nit": "999"},
        headers={"X-Admin-Key": "clave-incorrecta"},
    )
    assert resp.status_code == 403


def test_listar_empresas(client):
    nueva_empresa(client)
    resp = client.get("/admin/empresas", headers=h())
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_listar_empresas_clave_incorrecta(client):
    resp = client.get("/admin/empresas", headers={"X-Admin-Key": "mal"})
    assert resp.status_code == 403


# ── /admin/crear-sst ────────────────────────────────────────────────


def test_crear_sst_exitoso(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        resp = client.post(
            "/admin/crear-sst",
            json={
                "nombre": "SST Principal",
                "email": f"sst_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
    assert resp.status_code == 201
    assert "SST creado" in resp.json()["mensaje"]


def test_crear_sst_empresa_inexistente(client):
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        resp = client.post(
            "/admin/crear-sst",
            json={
                "nombre": "SST X",
                "email": f"sst_{secrets.token_hex(4)}@test.com",
                "empresa_id": str(uuid.uuid4()),
            },
            headers=h(),
        )
    assert resp.status_code == 404


def test_crear_sst_duplicado(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        client.post(
            "/admin/crear-sst",
            json={
                "nombre": "SST 1",
                "email": f"sst1_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
        resp = client.post(
            "/admin/crear-sst",
            json={
                "nombre": "SST 2",
                "email": f"sst2_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
    assert resp.status_code == 400


def test_crear_sst_email_duplicado(client):
    email = f"dup_{secrets.token_hex(4)}@test.com"
    empresa_id1 = nueva_empresa(client)
    empresa_id2 = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        client.post(
            "/admin/crear-sst",
            json={"nombre": "SST 1", "email": email, "empresa_id": empresa_id1},
            headers=h(),
        )
        resp = client.post(
            "/admin/crear-sst",
            json={"nombre": "SST 2", "email": email, "empresa_id": empresa_id2},
            headers=h(),
        )
    assert resp.status_code == 400


def test_crear_sst_correo_falla_no_explota(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=False):
        resp = client.post(
            "/admin/crear-sst",
            json={
                "nombre": "SST Sin Correo",
                "email": f"nc_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
    assert resp.status_code == 201


# ── /admin/crear-gerencia ────────────────────────────────────────────


def test_crear_gerencia_exitoso(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        resp = client.post(
            "/admin/crear-gerencia",
            json={
                "nombre": "Gerente Principal",
                "email": f"ger_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
    assert resp.status_code == 201
    assert "Gerencia creado" in resp.json()["mensaje"]


def test_crear_gerencia_duplicada(client):
    empresa_id = nueva_empresa(client)
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        client.post(
            "/admin/crear-gerencia",
            json={
                "nombre": "Ger 1",
                "email": f"ger1_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
        resp = client.post(
            "/admin/crear-gerencia",
            json={
                "nombre": "Ger 2",
                "email": f"ger2_{secrets.token_hex(4)}@test.com",
                "empresa_id": empresa_id,
            },
            headers=h(),
        )
    assert resp.status_code == 400


def test_crear_gerencia_empresa_inexistente(client):
    with patch("app.routers.admin_router.enviar_correo_bienvenida", return_value=True):
        resp = client.post(
            "/admin/crear-gerencia",
            json={
                "nombre": "Ger X",
                "email": f"ger_{secrets.token_hex(4)}@test.com",
                "empresa_id": str(uuid.uuid4()),
            },
            headers=h(),
        )
    assert resp.status_code == 404


# ── /admin/limpiar-tokens ────────────────────────────────────────────


def test_limpiar_tokens_sin_caducados(client):
    resp = client.post("/admin/limpiar-tokens", headers=h())
    assert resp.status_code == 200
    assert "Limpieza completada" in resp.json()["mensaje"]


def test_limpiar_tokens_con_caducados(client, db, empresa):
    user = User(
        nombre="User Expirado",
        email=f"exp_{secrets.token_hex(4)}@test.com",
        password_hash=get_password_hash("Password1!"),
        role=RoleEnum.sst,
        empresa_id=empresa.id,
        refresh_token="token-caducado",
        refresh_token_expira=datetime(2020, 1, 1),
        session_token="session-vieja",
    )
    db.add(user)
    db.commit()

    resp = client.post("/admin/limpiar-tokens", headers=h())
    assert resp.status_code == 200
    assert "1" in resp.json()["mensaje"]
