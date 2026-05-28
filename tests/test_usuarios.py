# tests/test_usuarios.py
from app.services.usuario_service import get_all_users, get_user_by_id
from fastapi import HTTPException
import pytest


def test_listar_usuarios_vacios(db, empresa):
    usuarios = get_all_users(db, empresa.id)
    assert isinstance(usuarios, list)


def test_listar_usuarios_solo_activos(db, empresa, usuario_sst):
    usuarios = get_all_users(db, empresa.id)
    assert all(u.activo for u in usuarios)


def test_get_user_by_id_existente(db, empresa, usuario_sst):
    user = get_user_by_id(db, usuario_sst.id, empresa.id)
    assert user.email == usuario_sst.email


def test_get_user_by_id_inexistente(db, empresa):
    import uuid
    with pytest.raises(HTTPException) as exc:
        get_user_by_id(db, uuid.uuid4(), empresa.id)
    assert exc.value.status_code == 404
