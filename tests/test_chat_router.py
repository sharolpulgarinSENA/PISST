# tests/test_chat_router.py
import io
from unittest.mock import patch

from app.core.security import create_access_token, get_password_hash
from app.models.user import RoleEnum, User


def crear_usuario(db, empresa, role=RoleEnum.empleado):
    import uuid

    email = f"{role.value}_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        nombre="Usuario Test",
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


def headers_para(user):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# ── POST /chat/mensaje ─────────────────────────────────────────────


def test_enviar_mensaje_ok(client, db, empresa):
    user = crear_usuario(db, empresa)
    with patch("app.routers.chat_router.chat_sasbot") as mock_chat:
        mock_chat.return_value = {
            "respuesta": "Usa casco y guantes.",
            "modo_emergencia": False,
        }
        resp = client.post(
            "/chat/mensaje",
            json={"mensaje": "¿Qué EPP necesito?"},
            headers=headers_para(user),
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["respuesta"] == "Usa casco y guantes."
    assert data["modo_emergencia"] is False


def test_enviar_mensaje_emergencia(client, db, empresa):
    user = crear_usuario(db, empresa)
    with patch("app.routers.chat_router.chat_sasbot") as mock_chat:
        mock_chat.return_value = {
            "respuesta": "Llama al 123 ahora.",
            "modo_emergencia": True,
        }
        resp = client.post(
            "/chat/mensaje",
            json={"mensaje": "me caí y estoy herido"},
            headers=headers_para(user),
        )
    assert resp.status_code == 200
    assert resp.json()["modo_emergencia"] is True


def test_enviar_mensaje_sin_auth(client):
    resp = client.post("/chat/mensaje", json={"mensaje": "hola"})
    assert resp.status_code == 401


# ── GET /chat/historial ────────────────────────────────────────────


def test_obtener_historial_vacio(client, db, empresa):
    user = crear_usuario(db, empresa)
    resp = client.get("/chat/historial", headers=headers_para(user))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_obtener_historial_con_mensajes(client, db, empresa):
    user = crear_usuario(db, empresa)
    with patch("app.routers.chat_router.chat_sasbot") as mock_chat:
        mock_chat.return_value = {"respuesta": "Ok", "modo_emergencia": False}
        client.post(
            "/chat/mensaje",
            json={"mensaje": "Hola"},
            headers=headers_para(user),
        )
    resp = client.get("/chat/historial", headers=headers_para(user))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── POST /chat/escalar ─────────────────────────────────────────────


def test_escalar_coordinador_ok(client, db, empresa):
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    crear_usuario(db, empresa, RoleEnum.sst)

    with patch("app.routers.chat_router.enviar_escalar_coordinador") as mock_email:
        mock_email.return_value = True
        resp = client.post("/chat/escalar", headers=headers_para(empleado))
    assert resp.status_code == 200
    assert "coordinador_email" in resp.json()


def test_escalar_sin_coordinador(client, db, empresa):
    import uuid

    from app.models.empresa import Empresa

    emp2 = Empresa(nombre="Empresa Sin SST", nit=uuid.uuid4().hex[:10], sector="X")
    db.add(emp2)
    db.commit()
    db.refresh(emp2)

    empleado = crear_usuario(db, emp2, RoleEnum.empleado)
    resp = client.post("/chat/escalar", headers=headers_para(empleado))
    assert resp.status_code == 404


def test_escalar_error_email(client, db, empresa):
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    crear_usuario(db, empresa, RoleEnum.sst)

    with patch("app.routers.chat_router.enviar_escalar_coordinador") as mock_email:
        mock_email.return_value = False
        resp = client.post("/chat/escalar", headers=headers_para(empleado))
    assert resp.status_code == 500


# ── POST /chat/archivo ─────────────────────────────────────────────


def test_analizar_archivo_pdf_ok(client, db, empresa):
    user = crear_usuario(db, empresa)
    with patch("app.routers.chat_router.analizar_archivo_sasbot") as mock_ai:
        mock_ai.return_value = "El documento muestra riesgos."
        resp = client.post(
            "/chat/archivo",
            files={"archivo": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            data={"mensaje": "Analiza esto"},
            headers=headers_para(user),
        )
    assert resp.status_code == 200
    assert resp.json()["respuesta"] == "El documento muestra riesgos."
    assert resp.json()["modo_emergencia"] is False


def test_analizar_archivo_tipo_no_permitido(client, db, empresa):
    user = crear_usuario(db, empresa)
    resp = client.post(
        "/chat/archivo",
        files={
            "archivo": ("script.exe", io.BytesIO(b"MZ"), "application/octet-stream")
        },
        headers=headers_para(user),
    )
    assert resp.status_code == 400


def test_analizar_archivo_demasiado_grande(client, db, empresa):
    user = crear_usuario(db, empresa)
    contenido_grande = b"x" * (11 * 1024 * 1024)
    resp = client.post(
        "/chat/archivo",
        files={"archivo": ("big.pdf", io.BytesIO(contenido_grande), "application/pdf")},
        headers=headers_para(user),
    )
    assert resp.status_code == 413


def test_analizar_archivo_error_ia(client, db, empresa):
    user = crear_usuario(db, empresa)
    with patch("app.routers.chat_router.analizar_archivo_sasbot") as mock_ai:
        mock_ai.side_effect = Exception("fallo IA")
        resp = client.post(
            "/chat/archivo",
            files={"archivo": ("doc.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
            headers=headers_para(user),
        )
    assert resp.status_code == 500


# ── POST /chat/reporte-rapido ──────────────────────────────────────


def test_reporte_rapido_accidente(client, db, empresa):
    user = crear_usuario(db, empresa)
    resp = client.post(
        "/chat/reporte-rapido",
        json={
            "tipo": "accidente",
            "descripcion": "Caída en escaleras",
            "lugar": "Piso 2",
        },
        headers=headers_para(user),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tipo"] == "accidente"
    assert "incidente_id" in data


def test_reporte_rapido_condicion_insegura(client, db, empresa):
    user = crear_usuario(db, empresa)
    resp = client.post(
        "/chat/reporte-rapido",
        json={"tipo": "condicion_insegura", "descripcion": "Piso mojado sin señal"},
        headers=headers_para(user),
    )
    assert resp.status_code == 201


def test_reporte_rapido_tipo_invalido(client, db, empresa):
    user = crear_usuario(db, empresa)
    resp = client.post(
        "/chat/reporte-rapido",
        json={"tipo": "tipo_inexistente", "descripcion": "Algo"},
        headers=headers_para(user),
    )
    assert resp.status_code in (400, 422)


def test_reporte_rapido_sin_auth(client):
    resp = client.post(
        "/chat/reporte-rapido",
        json={"tipo": "accidente", "descripcion": "Caída"},
    )
    assert resp.status_code == 401
