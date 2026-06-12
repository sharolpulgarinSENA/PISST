# tests/test_email_service.py
from unittest.mock import MagicMock, patch

from app.services.email_service import (
    enviar_correo_bienvenida,
    enviar_correo_reset,
    enviar_correo_reset_admin,
    enviar_escalar_coordinador,
)


def _mock_response(status_code: int, json_data: dict = None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"id": "abc123"}
    resp.text = "error"
    return resp


# ── enviar_correo_reset ────────────────────────────────────────────


def test_correo_reset_exito():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(200)
        resultado = enviar_correo_reset("user@test.com", "Juan", "token123")
    assert resultado is True


def test_correo_reset_fallo_servidor():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(400)
        resultado = enviar_correo_reset("user@test.com", "Juan", "token123")
    assert resultado is False


def test_correo_reset_excepcion():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.side_effect = Exception("timeout")
        resultado = enviar_correo_reset("user@test.com", "Juan", "token123")
    assert resultado is False


# ── enviar_correo_reset_admin ──────────────────────────────────────


def test_correo_reset_admin_exito():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(201)
        resultado = enviar_correo_reset_admin("admin@test.com", "Admin", "token_admin")
    assert resultado is True


def test_correo_reset_admin_fallo():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(500)
        resultado = enviar_correo_reset_admin("admin@test.com", "Admin", "token_admin")
    assert resultado is False


def test_correo_reset_admin_excepcion():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.side_effect = ConnectionError("no internet")
        resultado = enviar_correo_reset_admin("admin@test.com", "Admin", "tok")
    assert resultado is False


# ── enviar_correo_bienvenida ───────────────────────────────────────


def test_correo_bienvenida_exito():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(200)
        resultado = enviar_correo_bienvenida("emp@test.com", "Empleado", "Pass1!")
    assert resultado is True


def test_correo_bienvenida_fallo():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(422)
        resultado = enviar_correo_bienvenida("emp@test.com", "Empleado", "Pass1!")
    assert resultado is False


def test_correo_bienvenida_excepcion():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.side_effect = Exception("error de red")
        resultado = enviar_correo_bienvenida("emp@test.com", "Empleado", "Pass1!")
    assert resultado is False


# ── enviar_escalar_coordinador ─────────────────────────────────────


def test_escalar_coordinador_exito():
    historial = [
        {"timestamp": "2026-01-01 10:00", "mensaje": "Hola", "respuesta": "Ok"}
    ]
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(200)
        resultado = enviar_escalar_coordinador(
            "coord@test.com", "Coordinador", "Empleado", "emp@test.com", historial
        )
    assert resultado is True


def test_escalar_coordinador_con_archivo():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(201)
        resultado = enviar_escalar_coordinador(
            "coord@test.com",
            "Coordinador",
            "Empleado",
            "emp@test.com",
            [],
            archivo_nombre="reporte.pdf",
        )
    assert resultado is True


def test_escalar_coordinador_fallo():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.return_value = _mock_response(503)
        resultado = enviar_escalar_coordinador(
            "coord@test.com", "Coordinador", "Empleado", "emp@test.com", []
        )
    assert resultado is False


def test_escalar_coordinador_excepcion():
    with patch("app.services.email_service.httpx.post") as mock_post:
        mock_post.side_effect = Exception("timeout")
        resultado = enviar_escalar_coordinador(
            "coord@test.com", "Coordinador", "Empleado", "emp@test.com", []
        )
    assert resultado is False
