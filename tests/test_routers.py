# tests/test_routers.py
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
os.environ.setdefault("GEMINI_API_KEY", "fake")
os.environ.setdefault("RESEND_API_KEY", "fake")


def _token(user_id: str) -> str:
    from app.core.security import create_access_token

    return create_access_token({"sub": user_id})


def _auth(user) -> dict:
    return {"Authorization": f"Bearer {_token(str(user.id))}"}


# ── /chat/historial ───────────────────────────────────────────────


def test_chat_limit_excedido_422(client, usuario_sst):
    resp = client.get("/chat/historial?limite=1000", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_chat_limit_cero_422(client, usuario_sst):
    resp = client.get("/chat/historial?limite=0", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_chat_limit_valido_200(client, usuario_sst):
    resp = client.get("/chat/historial?limite=50", headers=_auth(usuario_sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_chat_limit_negativo_422(client, usuario_sst):
    resp = client.get("/chat/historial?limite=-1", headers=_auth(usuario_sst))
    assert resp.status_code == 422


# ── /usuarios/ ────────────────────────────────────────────────────


def test_usuario_limit_excedido_422(client, usuario_sst):
    resp = client.get("/usuarios/?limit=5000", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_usuario_limit_cero_422(client, usuario_sst):
    resp = client.get("/usuarios/?limit=0", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_usuario_limit_valido_200(client, usuario_sst):
    resp = client.get("/usuarios/?limit=30", headers=_auth(usuario_sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── /incidentes/ ──────────────────────────────────────────────────


def test_incidente_limit_excedido_422(client, usuario_sst):
    resp = client.get("/incidentes/?limit=9999", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_incidente_limit_valido_200(client, usuario_sst):
    resp = client.get("/incidentes/?limit=50", headers=_auth(usuario_sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── /riesgos/peligros ─────────────────────────────────────────────


def test_riesgo_limit_excedido_422(client, usuario_sst):
    resp = client.get("/riesgos/peligros?limit=501", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_riesgo_limit_valido_200(client, usuario_sst):
    resp = client.get("/riesgos/peligros?limit=50", headers=_auth(usuario_sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── /auditorias/ ──────────────────────────────────────────────────


def test_auditoria_limit_excedido_422(client, usuario_sst):
    resp = client.get("/auditorias/?limit=600", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_auditoria_limit_valido_200(client, usuario_sst):
    resp = client.get("/auditorias/?limit=50", headers=_auth(usuario_sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── /usuarios/me/actividad ────────────────────────────────────────


def test_actividad_limit_excedido_422(client, usuario_sst):
    resp = client.get("/usuarios/me/actividad?limit=999", headers=_auth(usuario_sst))
    assert resp.status_code == 422


def test_actividad_limit_valido_200(client, usuario_sst):
    resp = client.get("/usuarios/me/actividad?limit=10", headers=_auth(usuario_sst))
    assert resp.status_code == 200
