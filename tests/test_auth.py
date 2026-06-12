# tests/test_auth.py


def test_login_correcto(client, usuario_sst):
    resp = client.post(
        "/auth/login",
        json={
            "email": usuario_sst.email,
            "password": "password123",
            "recaptcha_token": "test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "sst"
    assert "debe_cambiar_password" in data
    assert data["debe_cambiar_password"] is False


def test_login_debe_cambiar_password_true(client, db, empresa):
    import secrets as _s

    from app.core.security import get_password_hash
    from app.models.user import RoleEnum, User

    email = f"nuevo_{_s.token_hex(4)}@test.com"
    user = User(
        nombre="SST Nuevo",
        email=email,
        password_hash=get_password_hash("Password1!"),
        role=RoleEnum.sst,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=True,
    )
    db.add(user)
    db.commit()

    resp = client.post(
        "/auth/login",
        json={"email": email, "password": "Password1!", "recaptcha_token": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["debe_cambiar_password"] is True


def test_login_password_incorrecta(client, usuario_sst):
    resp = client.post(
        "/auth/login",
        json={
            "email": usuario_sst.email,
            "password": "wrongpassword",
            "recaptcha_token": "test",
        },
    )
    assert resp.status_code == 401


def test_login_email_inexistente(client):
    resp = client.post(
        "/auth/login",
        json={
            "email": "noexiste@test.com",
            "password": "cualquier",
            "recaptcha_token": "test",
        },
    )
    assert resp.status_code == 401


def test_bloqueo_por_intentos_fallidos(client, usuario_sst):
    for _ in range(5):
        client.post(
            "/auth/login",
            json={
                "email": usuario_sst.email,
                "password": "wrongpassword",
                "recaptcha_token": "test",
            },
        )
    resp = client.post(
        "/auth/login",
        json={
            "email": usuario_sst.email,
            "password": "wrongpassword",
            "recaptcha_token": "test",
        },
    )
    assert resp.status_code == 429


def test_refresh_token_invalido(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "token-falso"})
    assert resp.status_code == 401


def _tokens_para(db, usuario):
    """Crea access + refresh token directamente en DB sin pasar por el rate-limited /login."""
    import os
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.core.security import create_access_token

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    session_id = secrets.token_hex(16)
    refresh = secrets.token_hex(40)
    usuario.session_token = session_id
    usuario.refresh_token = refresh
    usuario.refresh_token_expira = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(days=7)
    db.commit()
    access = create_access_token(
        {"sub": str(usuario.id), "role": usuario.role.value, "sid": session_id}
    )
    return {"access_token": access, "refresh_token": refresh}


# ── POST /auth/register ────────────────────────────────────────────


def test_register_ok(client, usuario_admin, empresa, admin_headers):
    import secrets as _s

    email = f"nuevo_{_s.token_hex(4)}@test.com"
    resp = client.post(
        "/auth/register",
        json={
            "nombre": "Nuevo SST",
            "email": email,
            "password": "Segura1!",
            "role": "sst",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    assert "mensaje" in resp.json()


def test_register_email_duplicado(client, usuario_sst, admin_headers):
    resp = client.post(
        "/auth/register",
        json={
            "nombre": "Duplicado",
            "email": usuario_sst.email,
            "password": "Segura1!",
            "role": "sst",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_register_rol_invalido(client, admin_headers):
    import secrets as _s

    resp = client.post(
        "/auth/register",
        json={
            "nombre": "X",
            "email": f"x_{_s.token_hex(4)}@test.com",
            "password": "Segura1!",
            "role": "rol_inexistente",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_register_sin_admin(client, usuario_sst):
    from app.core.security import create_access_token

    token = create_access_token({"sub": str(usuario_sst.id)})
    resp = client.post(
        "/auth/register",
        json={
            "nombre": "X",
            "email": "x@test.com",
            "password": "Segura1!",
            "role": "sst",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── POST /auth/forgot-password ─────────────────────────────────────


def test_forgot_password_email_existe(client, usuario_sst):
    from unittest.mock import patch

    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        resp = client.post("/auth/forgot-password", json={"email": usuario_sst.email})
    assert resp.status_code == 200
    assert "mensaje" in resp.json()


def test_forgot_password_email_inexistente(client):
    resp = client.post("/auth/forgot-password", json={"email": "noexiste@test.com"})
    assert resp.status_code == 200
    assert "mensaje" in resp.json()


# ── POST /auth/reset-password ──────────────────────────────────────


def test_reset_password_ok(client, db, usuario_sst):
    import secrets as _s
    from datetime import datetime, timedelta, timezone

    token = _s.token_urlsafe(32)
    usuario_sst.reset_token = token
    usuario_sst.reset_token_expira = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(minutes=30)
    db.commit()

    resp = client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NuevaPass1!"},
    )
    assert resp.status_code == 200
    assert "mensaje" in resp.json()


def test_reset_password_token_invalido(client):
    resp = client.post(
        "/auth/reset-password",
        json={"token": "token-falso-inexistente", "new_password": "NuevaPass1!"},
    )
    assert resp.status_code == 400


# ── POST /auth/cambiar-password ────────────────────────────────────


def test_cambiar_password_ok(client, db, usuario_sst):
    tokens = _tokens_para(db, usuario_sst)
    resp = client.post(
        "/auth/cambiar-password",
        json={"password_actual": "password123", "nueva_password": "NuevaPass1!"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200
    assert "mensaje" in resp.json()


def test_cambiar_password_actual_incorrecta(client, db, usuario_sst):
    tokens = _tokens_para(db, usuario_sst)
    resp = client.post(
        "/auth/cambiar-password",
        json={"password_actual": "incorrecta123", "nueva_password": "NuevaPass1!"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 400


def test_cambiar_password_token_invalido(client):
    resp = client.post(
        "/auth/cambiar-password",
        json={"password_actual": "cualquier", "nueva_password": "NuevaPass1!"},
        headers={"Authorization": "Bearer token-falso"},
    )
    assert resp.status_code == 401


# ── POST /auth/refresh ─────────────────────────────────────────────


def test_refresh_token_valido(client, db, usuario_sst):
    tokens = _tokens_para(db, usuario_sst)
    resp = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


# ── POST /auth/logout ──────────────────────────────────────────────


def test_logout_ok(client, db, usuario_sst):
    tokens = _tokens_para(db, usuario_sst)
    resp = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 200
    assert "mensaje" in resp.json()


def test_logout_token_invalido(client):
    resp = client.post("/auth/logout", json={"refresh_token": "token-falso"})
    assert resp.status_code == 200
