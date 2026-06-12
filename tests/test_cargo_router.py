# tests/test_cargo_router.py
import uuid

from app.core.security import create_access_token, get_password_hash
from app.models.area import Area
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


def crear_area(db, empresa, nombre="Área Test"):
    area = Area(nombre=nombre, empresa_id=empresa.id)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


# ── GET /cargos/ ───────────────────────────────────────────────────


def test_listar_cargos_vacio(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get("/cargos/", headers=auth(sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_listar_cargos_sin_auth(client):
    resp = client.get("/cargos/")
    assert resp.status_code == 401


def test_listar_cargos_empleado_denegado(client, db, empresa):
    emp = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.get("/cargos/", headers=auth(emp))
    assert resp.status_code == 403


# ── POST /cargos/ ──────────────────────────────────────────────────


def test_crear_cargo_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    area = crear_area(db, empresa)
    resp = client.post(
        "/cargos/",
        json={"nombre": "Operario", "area_id": str(area.id)},
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["nombre"] == "Operario"
    assert resp.json()["area_id"] == str(area.id)


def test_crear_cargo_area_inexistente(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/cargos/",
        json={"nombre": "Supervisor", "area_id": str(uuid.uuid4())},
        headers=auth(sst),
    )
    assert resp.status_code == 404


def test_crear_cargo_area_otra_empresa(client, db, empresa):
    from app.models.empresa import Empresa

    sst = crear_usuario(db, empresa)
    emp2 = Empresa(nombre="Otra Empresa", nit=uuid.uuid4().hex[:10], sector="X")
    db.add(emp2)
    db.commit()
    db.refresh(emp2)
    area_ajena = crear_area(db, emp2, nombre="Área Ajena")

    resp = client.post(
        "/cargos/",
        json={"nombre": "Cargo X", "area_id": str(area_ajena.id)},
        headers=auth(sst),
    )
    assert resp.status_code == 404


def test_crear_cargo_duplicado(client, db, empresa):
    sst = crear_usuario(db, empresa)
    area = crear_area(db, empresa, nombre="Área Dup")
    client.post(
        "/cargos/",
        json={"nombre": "Técnico", "area_id": str(area.id)},
        headers=auth(sst),
    )
    resp = client.post(
        "/cargos/",
        json={"nombre": "Técnico", "area_id": str(area.id)},
        headers=auth(sst),
    )
    assert resp.status_code == 400


def test_crear_cargo_sin_auth(client):
    resp = client.post("/cargos/", json={"nombre": "X", "area_id": str(uuid.uuid4())})
    assert resp.status_code == 401


def test_listar_cargos_con_datos(client, db, empresa):
    sst = crear_usuario(db, empresa)
    area = crear_area(db, empresa, nombre="Área Lista")
    client.post(
        "/cargos/",
        json={"nombre": "Analista", "area_id": str(area.id)},
        headers=auth(sst),
    )
    resp = client.get("/cargos/", headers=auth(sst))
    assert resp.status_code == 200
    nombres = [c["nombre"] for c in resp.json()]
    assert "Analista" in nombres
