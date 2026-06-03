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
