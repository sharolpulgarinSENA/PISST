# tests/test_api_keys.py
import pytest

from app.services.api_key_service import crear_api_key, generar_clave, validar_clave

# ── generar_clave ────────────────────────────────────────────────────


def test_generar_clave_formato():
    clave = generar_clave()
    assert clave.startswith("sk_")
    assert len(clave) == 63


def test_generar_clave_unica():
    claves = {generar_clave() for _ in range(50)}
    assert len(claves) == 50


# ── crear_api_key ────────────────────────────────────────────────────


def test_crear_api_key_basica(db):
    key = crear_api_key(db, descripcion="Cron job render")
    assert key.clave.startswith("sk_")
    assert key.activo is True
    assert key.rol == "cron"
    assert key.descripcion == "Cron job render"
    assert key.empresa_id is None


def test_crear_api_key_con_empresa(db, empresa):
    key = crear_api_key(db, descripcion="Key empresa", empresa_id=empresa.id)
    assert key.empresa_id == empresa.id


# ── validar_clave ────────────────────────────────────────────────────


def test_validar_clave_valida(db):
    key = crear_api_key(db)
    resultado = validar_clave(db, key.clave)
    assert resultado.id == key.id


def test_validar_clave_inexistente_falla(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        validar_clave(db, "sk_clave_inexistente_000000000000000")
    assert exc.value.status_code == 401


def test_validar_clave_inactiva_falla(db):
    from fastapi import HTTPException

    key = crear_api_key(db)
    key.activo = False
    db.commit()

    with pytest.raises(HTTPException) as exc:
        validar_clave(db, key.clave)
    assert exc.value.status_code == 401


# ── POST /auth/api-keys ──────────────────────────────────────────────


def test_crear_api_key_endpoint_ok(client, admin_headers):
    resp = client.post(
        "/auth/api-keys",
        json={"descripcion": "Cron render", "rol": "cron"},
        headers=admin_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["clave"].startswith("sk_")
    assert data["activo"] is True
    assert data["rol"] == "cron"


def test_crear_api_key_sin_auth_falla(client):
    resp = client.post("/auth/api-keys", json={"descripcion": "Test"})
    assert resp.status_code in (401, 403)


def test_crear_api_key_rol_no_admin_falla(client, usuario_sst):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(usuario_sst.id)})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/auth/api-keys",
        json={"descripcion": "Test"},
        headers=headers,
    )
    assert resp.status_code == 403


# ── /auditorias/verificar-vencidas con X-API-Key ─────────────────────


def test_verificar_vencidas_con_api_key(client, db):
    key = crear_api_key(db, descripcion="Cron job test")
    resp = client.post(
        "/auditorias/verificar-vencidas",
        headers={"X-API-Key": key.clave},
    )
    assert resp.status_code == 200
    assert "auditorias_vencidas" in resp.json()
    assert "nc_vencidas" in resp.json()


def test_verificar_vencidas_con_api_key_invalida(client):
    resp = client.post(
        "/auditorias/verificar-vencidas",
        headers={"X-API-Key": "sk_clave_falsa_000000000000000000000"},
    )
    assert resp.status_code == 401


def test_verificar_vencidas_con_jwt_admin(client, admin_headers):
    resp = client.post(
        "/auditorias/verificar-vencidas",
        headers=admin_headers,
    )
    assert resp.status_code == 200


def test_verificar_vencidas_sin_auth(client):
    resp = client.post("/auditorias/verificar-vencidas")
    assert resp.status_code == 401
