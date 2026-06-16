# tests/test_perfil_notificaciones.py
import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.security import create_access_token, get_password_hash
from app.models.notificacion import Notificacion
from app.models.user import RoleEnum, User


def _crear_empleado(db, empresa):
    import uuid as _uuid

    email = f"emp_{_uuid.uuid4().hex[:8]}@test.com"
    user = User(
        nombre="Empleado Test",
        email=email,
        password_hash=get_password_hash("password123"),
        role=RoleEnum.empleado,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _tokens_para(db, usuario):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    session_id = secrets.token_hex(16)
    refresh = secrets.token_hex(40)
    usuario.session_token = session_id
    usuario.refresh_token = refresh
    usuario.refresh_token_expira = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(days=7)
    db.commit()
    return create_access_token(
        {"sub": str(usuario.id), "role": usuario.role.value, "sid": session_id}
    )


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── PATCH /usuarios/me ────────────────────────────────────────────


def test_actualizar_perfil_nombre(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    resp = client.patch(
        "/usuarios/me",
        json={"nombre": "Nuevo Nombre SST"},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Nuevo Nombre SST"


def test_actualizar_perfil_telefono(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    resp = client.patch(
        "/usuarios/me",
        json={"telefono": "+57 310 000 0000"},
        headers=_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["telefono"] == "+57 310 000 0000"


def test_actualizar_perfil_sin_token(client):
    resp = client.patch("/usuarios/me", json={"nombre": "Hack"})
    assert resp.status_code == 401


# ── PUT /usuarios/me/foto ─────────────────────────────────────────


PNG_BYTES = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + b"\x00" * 20


def test_subir_foto_exitoso(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    with patch(
        "app.routers.usuario_router.subir_foto_perfil",
        return_value="https://res.cloudinary.com/fake/foto.webp",
    ):
        resp = client.put(
            "/usuarios/me/foto",
            files={"foto": ("foto.png", PNG_BYTES, "image/png")},
            headers=_headers(token),
        )
    assert resp.status_code == 200
    assert "foto_url" in resp.json()
    assert resp.json()["foto_url"].startswith("https://")


def test_subir_foto_tipo_invalido(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    resp = client.put(
        "/usuarios/me/foto",
        files={"foto": ("doc.pdf", b"fake-pdf", "application/pdf")},
        headers=_headers(token),
    )
    assert resp.status_code == 400


def test_subir_foto_sin_token(client):
    resp = client.put(
        "/usuarios/me/foto",
        files={"foto": ("foto.jpg", b"bytes", "image/jpeg")},
    )
    assert resp.status_code == 401


# ── GET /usuarios/me/actividad ────────────────────────────────────


def test_actividad_retorna_estructura(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    resp = client.get("/usuarios/me/actividad", headers=_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "registros" in data
    assert isinstance(data["registros"], list)


def test_actividad_sin_token(client):
    resp = client.get("/usuarios/me/actividad")
    assert resp.status_code == 401


# ── GET /notificaciones/feed ──────────────────────────────────────


def test_feed_retorna_estructura(client, db, empresa, usuario_sst):
    # Insertar una notificación de prueba
    notif = Notificacion(
        empresa_id=empresa.id,
        tipo="reporte_nuevo",
        titulo="Test notif",
        descripcion="Descripción test",
        modulo="reportes",
        url_destino="/incidentes",
    )
    db.add(notif)
    db.commit()

    token = _tokens_para(db, usuario_sst)
    resp = client.get("/notificaciones/feed", headers=_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "eventos" in data
    assert data["total"] >= 1
    evento = data["eventos"][0]
    assert "id" in evento
    assert "tipo" in evento
    assert "leido" in evento


def test_feed_paginacion(client, db, usuario_sst):
    token = _tokens_para(db, usuario_sst)
    resp = client.get("/notificaciones/feed?limit=5&offset=0", headers=_headers(token))
    assert resp.status_code == 200
    assert len(resp.json()["eventos"]) <= 5


def test_feed_sin_token(client):
    resp = client.get("/notificaciones/feed")
    assert resp.status_code == 401


# ── PATCH /notificaciones/{id}/leido ─────────────────────────────


def test_marcar_leido(client, db, empresa, usuario_sst):
    notif = Notificacion(
        empresa_id=empresa.id,
        tipo="capacitacion_nueva",
        titulo="Cap nueva",
        descripcion="Desc",
        modulo="capacitaciones",
        url_destino="/capacitaciones",
        leido=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    token = _tokens_para(db, usuario_sst)
    resp = client.patch(f"/notificaciones/{notif.id}/leido", headers=_headers(token))
    assert resp.status_code == 200
    assert resp.json()["leido"] is True


def test_marcar_leido_inexistente(client, db, usuario_sst):
    import uuid

    token = _tokens_para(db, usuario_sst)
    resp = client.patch(
        f"/notificaciones/{uuid.uuid4()}/leido", headers=_headers(token)
    )
    assert resp.status_code == 404


# ── PATCH /notificaciones/leer-todas ─────────────────────────────


def test_leer_todas(client, db, empresa, usuario_sst):
    for i in range(3):
        db.add(
            Notificacion(
                empresa_id=empresa.id,
                tipo="riesgo_nuevo",
                titulo=f"Riesgo {i}",
                descripcion="Desc",
                modulo="riesgos",
                url_destino="/riesgos",
                leido=False,
            )
        )
    db.commit()

    token = _tokens_para(db, usuario_sst)
    resp = client.patch("/notificaciones/leer-todas", headers=_headers(token))
    assert resp.status_code == 200
    assert "actualizadas" in resp.json()
    assert resp.json()["actualizadas"] >= 3


def test_leer_todas_sin_token(client):
    resp = client.patch("/notificaciones/leer-todas")
    assert resp.status_code == 401
