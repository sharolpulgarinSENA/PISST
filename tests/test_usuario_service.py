# tests/test_usuario_service.py
import secrets
import uuid
from unittest.mock import patch

import pytest

from app.models.area import Area
from app.models.cargo import Cargo
from app.models.user import RoleEnum
from app.schemas.usuario_schema import UsuarioCreate, UsuarioUpdate
from app.services import usuario_service


def make_area(db, empresa, nombre="Producción"):
    area = Area(nombre=nombre, empresa_id=empresa.id, activo=True)
    db.add(area)
    db.commit()
    db.refresh(area)
    return area


def make_cargo(db, empresa, area, nombre="Operario"):
    cargo = Cargo(nombre=nombre, empresa_id=empresa.id, area_id=area.id, activo=True)
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return cargo


def make_empleado(db, empresa, **kwargs):
    datos = UsuarioCreate(
        nombre="Empleado Test",
        email=f"emp_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.empleado,
        **kwargs,
    )
    with patch(
        "app.services.usuario_service.enviar_correo_bienvenida", return_value=True
    ):
        return usuario_service.create_user(db, datos, empresa.id)


# ── generar_password_temporal ───────────────────────────────────────


def test_generar_password_temporal_longitud():
    pwd = usuario_service.generar_password_temporal()
    assert len(pwd) == 10


def test_generar_password_temporal_longitud_custom():
    pwd = usuario_service.generar_password_temporal(longitud=16)
    assert len(pwd) == 16


# ── get_all_users ───────────────────────────────────────────────────


def test_get_all_users_vacio(db, empresa):
    resultado = usuario_service.get_all_users(db, empresa.id)
    assert isinstance(resultado, list)


def test_get_all_users_con_datos(db, empresa):
    make_empleado(db, empresa)
    resultado = usuario_service.get_all_users(db, empresa.id)
    assert len(resultado) >= 1


# ── get_user_by_id ──────────────────────────────────────────────────


def test_get_user_by_id_encontrado(db, empresa):
    empleado = make_empleado(db, empresa)
    encontrado = usuario_service.get_user_by_id(db, empleado.id, empresa.id)
    assert encontrado.id == empleado.id


def test_get_user_by_id_no_encontrado(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        usuario_service.get_user_by_id(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404


# ── create_user ─────────────────────────────────────────────────────


def test_create_user_exitoso(db, empresa):
    empleado = make_empleado(db, empresa)
    assert empleado.role == RoleEnum.empleado
    assert empleado.debe_cambiar_password is True
    assert empleado.empresa_id == empresa.id


def test_create_user_rol_no_empleado_falla(db, empresa):
    from fastapi import HTTPException

    datos = UsuarioCreate(
        nombre="SST Nuevo",
        email=f"sst_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.sst,
    )
    with pytest.raises(HTTPException) as exc:
        usuario_service.create_user(db, datos, empresa.id)
    assert exc.value.status_code == 403


def test_create_user_email_duplicado_falla(db, empresa):
    from fastapi import HTTPException

    email = f"dup_{secrets.token_hex(4)}@test.com"
    datos = UsuarioCreate(nombre="Emp1", email=email, role=RoleEnum.empleado)
    with patch(
        "app.services.usuario_service.enviar_correo_bienvenida", return_value=True
    ):
        usuario_service.create_user(db, datos, empresa.id)

    with pytest.raises(HTTPException) as exc:
        usuario_service.create_user(db, datos, empresa.id)
    assert exc.value.status_code == 400


def test_create_user_con_area_y_cargo(db, empresa):
    area = make_area(db, empresa)
    cargo = make_cargo(db, empresa, area)
    datos = UsuarioCreate(
        nombre="Empleado Completo",
        email=f"ec_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.empleado,
        area_nombre=area.nombre,
        cargo_nombre=cargo.nombre,
    )
    with patch(
        "app.services.usuario_service.enviar_correo_bienvenida", return_value=True
    ):
        empleado = usuario_service.create_user(db, datos, empresa.id)
    assert empleado.area_id == area.id
    assert empleado.cargo_id == cargo.id


def test_create_user_area_inexistente_falla(db, empresa):
    from fastapi import HTTPException

    datos = UsuarioCreate(
        nombre="Emp X",
        email=f"ex_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.empleado,
        area_nombre="Área que no existe",
    )
    with pytest.raises(HTTPException) as exc:
        usuario_service.create_user(db, datos, empresa.id)
    assert exc.value.status_code == 404


def test_create_user_cargo_inexistente_falla(db, empresa):
    from fastapi import HTTPException

    datos = UsuarioCreate(
        nombre="Emp Y",
        email=f"ey_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.empleado,
        cargo_nombre="Cargo que no existe",
    )
    with pytest.raises(HTTPException) as exc:
        usuario_service.create_user(db, datos, empresa.id)
    assert exc.value.status_code == 404


def test_create_user_correo_falla_no_explota(db, empresa):
    datos = UsuarioCreate(
        nombre="Emp Z",
        email=f"ez_{secrets.token_hex(4)}@test.com",
        role=RoleEnum.empleado,
    )
    with patch(
        "app.services.usuario_service.enviar_correo_bienvenida", return_value=False
    ):
        empleado = usuario_service.create_user(db, datos, empresa.id)
    assert empleado is not None


# ── update_user ─────────────────────────────────────────────────────


def test_update_user_nombre(db, empresa):
    empleado = make_empleado(db, empresa)
    actualizado = usuario_service.update_user(
        db, empleado.id, UsuarioUpdate(nombre="Nombre Nuevo"), empresa.id
    )
    assert actualizado.nombre == "Nombre Nuevo"


def test_update_user_desactivar(db, empresa):
    empleado = make_empleado(db, empresa)
    actualizado = usuario_service.update_user(
        db, empleado.id, UsuarioUpdate(activo=False), empresa.id
    )
    assert actualizado.activo is False


def test_update_user_area_y_cargo(db, empresa):
    area = make_area(db, empresa, nombre="Logística")
    cargo = make_cargo(db, empresa, area, nombre="Conductor")
    empleado = make_empleado(db, empresa)
    actualizado = usuario_service.update_user(
        db, empleado.id, UsuarioUpdate(area_id=area.id, cargo_id=cargo.id), empresa.id
    )
    assert actualizado.area_id == area.id
    assert actualizado.cargo_id == cargo.id
