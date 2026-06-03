# tests/test_deps.py
import secrets
import uuid

from jose import jwt as jose_jwt

from app.core.security import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_password_hash,
)
from app.models.user import RoleEnum, User

# ── Helpers ─────────────────────────────────────────────────────────


def make_user(db, empresa, role=RoleEnum.sst, **kwargs):
    session_tok = secrets.token_hex(32)
    user = User(
        nombre="Dep Test User",
        email=f"dep_{secrets.token_hex(4)}@test.com",
        password_hash=get_password_hash("Password1!"),
        role=role,
        empresa_id=empresa.id,
        activo=True,
        session_token=session_tok,
        **kwargs,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, session_tok


def token_para(user_id, role, session_id):
    return create_access_token({"sub": str(user_id), "role": role, "sid": session_id})


# ── Token inválido / expirado ───────────────────────────────────────


def test_token_malformado_401(client):
    resp = client.get(
        "/usuarios/", headers={"Authorization": "Bearer token_malformado_xyz"}
    )
    assert resp.status_code == 401


def test_token_expirado_401(client):
    token = jose_jwt.encode(
        {"sub": str(uuid.uuid4()), "role": "sst", "sid": "sid", "exp": 1},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_token_sin_sub_401(client):
    token = jose_jwt.encode(
        {"role": "sst", "sid": "sid", "exp": 9999999999},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# ── Usuario no existe en BD ─────────────────────────────────────────


def test_usuario_inexistente_401(client):
    token = token_para(uuid.uuid4(), "sst", "cualquier-session")
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Usuario no encontrado"


# ── debe_cambiar_password ───────────────────────────────────────────


def test_debe_cambiar_password_bloqueado_403(client, db, empresa):
    user, session_tok = make_user(db, empresa, debe_cambiar_password=True)
    token = token_para(user.id, "sst", session_tok)
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "debe_cambiar_password"


# ── Session token inválido ──────────────────────────────────────────


def test_session_invalida_401(client, db, empresa):
    user, session_tok = make_user(db, empresa)
    token = token_para(user.id, "sst", "session-incorrecta")
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert "dispositivo" in resp.json()["detail"].lower()


# ── Rol insuficiente ────────────────────────────────────────────────


def test_rol_insuficiente_403(client, db, empresa):
    empleado, session_tok = make_user(db, empresa, role=RoleEnum.empleado)
    token = token_para(empleado.id, "empleado", session_tok)
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert "Acceso denegado" in resp.json()["detail"]


# ── Acceso exitoso ──────────────────────────────────────────────────


def test_acceso_valido_devuelve_200(client, db, empresa):
    user, session_tok = make_user(db, empresa)
    token = token_para(user.id, "sst", session_tok)
    resp = client.get("/usuarios/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
