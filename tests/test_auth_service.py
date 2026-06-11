# tests/test_auth_service.py
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.core.security import get_password_hash
from app.models.user import RoleEnum, User
from app.services import auth_service

# ── Helper ─────────────────────────────────────────────────────────


def make_user(db, empresa, **kwargs):
    defaults = {
        "nombre": "Test User",
        "email": f"u_{secrets.token_hex(4)}@test.com",
        "password_hash": get_password_hash("Password1!"),
        "role": RoleEnum.sst,
        "empresa_id": empresa.id,
        "activo": True,
        "debe_cambiar_password": False,
    }
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ── login ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_exitoso(db, empresa):
    user = make_user(db, empresa)
    with patch("app.services.auth_service.validar_recaptcha", return_value=True):
        resultado = await auth_service.login(user.email, "Password1!", "tok", db)
    assert "access_token" in resultado
    assert "refresh_token" in resultado
    assert resultado["role"] == "sst"


@pytest.mark.asyncio
async def test_login_password_incorrecta(db, empresa):
    from fastapi import HTTPException

    user = make_user(db, empresa)
    with patch("app.services.auth_service.validar_recaptcha", return_value=True):
        with pytest.raises(HTTPException) as exc:
            await auth_service.login(user.email, "wrongpass", "tok", db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_usuario_inactivo(db, empresa):
    from fastapi import HTTPException

    user = make_user(db, empresa, activo=False)
    with patch("app.services.auth_service.validar_recaptcha", return_value=True):
        with pytest.raises(HTTPException) as exc:
            await auth_service.login(user.email, "Password1!", "tok", db)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_cuenta_bloqueada(db, empresa):
    from fastapi import HTTPException

    futuro = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    user = make_user(db, empresa, bloqueado_hasta=futuro)
    with patch("app.services.auth_service.validar_recaptcha", return_value=True):
        with pytest.raises(HTTPException) as exc:
            await auth_service.login(user.email, "Password1!", "tok", db)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_login_recaptcha_invalido(db, empresa):
    from fastapi import HTTPException

    user = make_user(db, empresa)
    with patch("app.services.auth_service.validar_recaptcha", return_value=False):
        with pytest.raises(HTTPException) as exc:
            await auth_service.login(user.email, "Password1!", "tok", db)
    assert exc.value.status_code == 400


# ── registrar_usuario ───────────────────────────────────────────────


def test_registrar_usuario_exitoso(db, empresa):
    resultado = auth_service.registrar_usuario(
        "Nuevo",
        f"n_{secrets.token_hex(4)}@test.com",
        "Password1!",
        "sst",
        empresa.id,
        db,
    )
    assert resultado["mensaje"] == "Usuario creado exitosamente"


def test_registrar_usuario_email_duplicado(db, empresa):
    from fastapi import HTTPException

    email = f"dup_{secrets.token_hex(4)}@test.com"
    auth_service.registrar_usuario("U1", email, "Password1!", "sst", empresa.id, db)
    with pytest.raises(HTTPException) as exc:
        auth_service.registrar_usuario("U2", email, "Password1!", "sst", empresa.id, db)
    assert exc.value.status_code == 400


def test_registrar_usuario_rol_invalido(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth_service.registrar_usuario(
            "X",
            f"x_{secrets.token_hex(4)}@test.com",
            "Password1!",
            "rolfalso",
            empresa.id,
            db,
        )
    assert exc.value.status_code == 400


def test_registrar_usuario_password_debil(db, empresa):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth_service.registrar_usuario(
            "X", f"x_{secrets.token_hex(4)}@test.com", "1234", "sst", empresa.id, db
        )
    assert exc.value.status_code == 400


# ── cambiar_password ────────────────────────────────────────────────


def test_cambiar_password_exitoso(db, empresa):
    token = secrets.token_hex(32)
    user = make_user(db, empresa, session_token=token)
    resultado = auth_service.cambiar_password(
        str(user.id), token, "Password1!", "NuevaPass2!", db
    )
    assert resultado["mensaje"] == "Contraseña cambiada exitosamente"


def test_cambiar_password_session_invalida(db, empresa):
    from fastapi import HTTPException

    user = make_user(db, empresa, session_token=secrets.token_hex(32))
    with pytest.raises(HTTPException) as exc:
        auth_service.cambiar_password(
            str(user.id), "token-incorrecto", "Password1!", "NuevaPass2!", db
        )
    assert exc.value.status_code == 401
    assert "dispositivo" in exc.value.detail.lower()


def test_cambiar_password_actual_incorrecta(db, empresa):
    from fastapi import HTTPException

    token = secrets.token_hex(32)
    user = make_user(db, empresa, session_token=token)
    with pytest.raises(HTTPException) as exc:
        auth_service.cambiar_password(
            str(user.id), token, "wrongpassword", "NuevaPass2!", db
        )
    assert exc.value.status_code == 400


def test_cambiar_password_nueva_debil(db, empresa):
    from fastapi import HTTPException

    token = secrets.token_hex(32)
    user = make_user(db, empresa, session_token=token)
    with pytest.raises(HTTPException) as exc:
        auth_service.cambiar_password(str(user.id), token, "Password1!", "1234", db)
    assert exc.value.status_code == 400


def test_cambiar_password_sin_session_token(db, empresa):
    """session_id=None se permite — usuario sin sesión activa registrada."""
    user = make_user(db, empresa, session_token=None)
    resultado = auth_service.cambiar_password(
        str(user.id), None, "Password1!", "NuevaPass2!", db
    )
    assert resultado["mensaje"] == "Contraseña cambiada exitosamente"


# ── refrescar_token ─────────────────────────────────────────────────


def test_refrescar_token_exitoso(db, empresa):
    refresh = secrets.token_hex(40)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    make_user(db, empresa, refresh_token=refresh, refresh_token_expira=expira)
    resultado = auth_service.refrescar_token(refresh, db)
    assert "access_token" in resultado


def test_refrescar_token_invalido(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token("token-falso", db)
    assert exc.value.status_code == 401


def test_refrescar_token_expirado(db, empresa):
    from fastapi import HTTPException

    refresh = secrets.token_hex(40)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    make_user(db, empresa, refresh_token=refresh, refresh_token_expira=expira)
    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token(refresh, db)
    assert exc.value.status_code == 401


def test_refrescar_token_usuario_inactivo(db, empresa):
    from fastapi import HTTPException

    refresh = secrets.token_hex(40)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    make_user(
        db, empresa, refresh_token=refresh, refresh_token_expira=expira, activo=False
    )
    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token(refresh, db)
    assert exc.value.status_code == 401


def test_refrescar_token_empresa_inactiva(db, empresa):
    from fastapi import HTTPException

    empresa.activo = False
    db.commit()

    refresh = secrets.token_hex(40)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    make_user(db, empresa, refresh_token=refresh, refresh_token_expira=expira)
    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token(refresh, db)
    assert exc.value.status_code == 401
    assert "empresa" in exc.value.detail.lower()


def test_refrescar_token_usuario_eliminado(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token("refresh-token-de-usuario-inexistente", db)
    assert exc.value.status_code == 401


def test_refrescar_token_max_age_7_dias(db, empresa):
    from fastapi import HTTPException

    refresh = secrets.token_hex(40)
    # Expiró hace 1 segundo (justo pasaron los 7 días del login original)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)
    make_user(db, empresa, refresh_token=refresh, refresh_token_expira=expira)
    with pytest.raises(HTTPException) as exc:
        auth_service.refrescar_token(refresh, db)
    assert exc.value.status_code == 401


# ── logout ──────────────────────────────────────────────────────────


def test_logout_exitoso(db, empresa):
    refresh = secrets.token_hex(40)
    user = make_user(
        db, empresa, refresh_token=refresh, session_token=secrets.token_hex(32)
    )
    resultado = auth_service.logout(refresh, db)
    assert resultado["mensaje"] == "Sesión cerrada exitosamente"
    db.refresh(user)
    assert user.refresh_token is None
    assert user.session_token is None


def test_logout_token_inexistente(db):
    resultado = auth_service.logout("token-inexistente", db)
    assert resultado["mensaje"] == "Sesión cerrada exitosamente"


# ── solicitar_reset / resetear_password ─────────────────────────────


def test_solicitar_reset_usuario_existe(db, empresa):
    user = make_user(db, empresa)
    with patch("app.services.email_service.enviar_correo_reset", return_value=True):
        resultado = auth_service.solicitar_reset(user.email, db)
    assert "mensaje" in resultado


def test_solicitar_reset_usuario_no_existe(db):
    resultado = auth_service.solicitar_reset("noexiste@test.com", db)
    assert "mensaje" in resultado


def test_resetear_password_exitoso(db, empresa):
    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    make_user(db, empresa, reset_token=token, reset_token_expira=expira)
    resultado = auth_service.resetear_password(token, "NuevaPass2!", db)
    assert resultado["mensaje"] == "Contraseña actualizada exitosamente"


def test_resetear_password_token_invalido(db):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        auth_service.resetear_password("token-falso", "NuevaPass2!", db)
    assert exc.value.status_code == 400


def test_resetear_password_token_expirado(db, empresa):
    from fastapi import HTTPException

    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    make_user(db, empresa, reset_token=token, reset_token_expira=expira)
    with pytest.raises(HTTPException) as exc:
        auth_service.resetear_password(token, "NuevaPass2!", db)
    assert exc.value.status_code == 400


def test_resetear_password_nueva_debil(db, empresa):
    from fastapi import HTTPException

    token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
    make_user(db, empresa, reset_token=token, reset_token_expira=expira)
    with pytest.raises(HTTPException) as exc:
        auth_service.resetear_password(token, "1234", db)
    assert exc.value.status_code == 400
