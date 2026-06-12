# tests/test_area_router.py
import uuid

from app.core.security import create_access_token, get_password_hash
from app.models.user import RoleEnum, User


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


# ── GET /areas/ ────────────────────────────────────────────────────


def test_listar_areas_vacio(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get("/areas/", headers=auth(sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_areas_sin_auth(client):
    resp = client.get("/areas/")
    assert resp.status_code == 401


def test_listar_areas_empleado_denegado(client, db, empresa):
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.get("/areas/", headers=auth(emp))
    assert resp.status_code == 403


# ── POST /areas/ ───────────────────────────────────────────────────


def test_crear_area_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/areas/",
        json={"nombre": "Producción", "descripcion": "Área de producción"},
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Producción"


def test_crear_area_sin_descripcion(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/areas/",
        json={"nombre": "Logística"},
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Logística"


def test_crear_area_duplicada(client, db, empresa):
    sst = crear_usuario(db, empresa)
    client.post("/areas/", json={"nombre": "Mantenimiento"}, headers=auth(sst))
    resp = client.post("/areas/", json={"nombre": "Mantenimiento"}, headers=auth(sst))
    assert resp.status_code == 400


def test_crear_area_sin_auth(client):
    resp = client.post("/areas/", json={"nombre": "X"})
    assert resp.status_code == 401


def test_crear_area_empleado_denegado(client, db, empresa):
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.post("/areas/", json={"nombre": "Ventas"}, headers=auth(emp))
    assert resp.status_code == 403


def test_listar_areas_con_datos(client, db, empresa):
    sst = crear_usuario(db, empresa)
    client.post("/areas/", json={"nombre": "Calidad"}, headers=auth(sst))
    resp = client.get("/areas/", headers=auth(sst))
    assert resp.status_code == 200
    nombres = [a["nombre"] for a in resp.json()]
    assert "Calidad" in nombres
