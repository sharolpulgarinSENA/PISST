# tests/test_auth.py


def test_login_correcto(client, usuario_sst):
    resp = client.post("/auth/login", json={
        "email": usuario_sst.email,
        "password": "password123",
        "recaptcha_token": "test"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "sst"


def test_login_password_incorrecta(client, usuario_sst):
    resp = client.post("/auth/login", json={
        "email": usuario_sst.email,
        "password": "wrongpassword",
        "recaptcha_token": "test"
    })
    assert resp.status_code == 401


def test_login_email_inexistente(client):
    resp = client.post("/auth/login", json={
        "email": "noexiste@test.com",
        "password": "cualquier",
        "recaptcha_token": "test"
    })
    assert resp.status_code == 401


def test_bloqueo_por_intentos_fallidos(client, usuario_sst):
    for _ in range(5):
        client.post("/auth/login", json={
            "email": usuario_sst.email,
            "password": "wrongpassword",
            "recaptcha_token": "test"
        })
    resp = client.post("/auth/login", json={
        "email": usuario_sst.email,
        "password": "wrongpassword",
        "recaptcha_token": "test"
    })
    assert resp.status_code == 429


def test_refresh_token_invalido(client):
    resp = client.post("/auth/refresh", json={"refresh_token": "token-falso"})
    assert resp.status_code == 401
