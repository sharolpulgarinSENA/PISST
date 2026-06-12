# tests/test_ai_service.py
from unittest.mock import MagicMock, patch

from app.services.ai_service import (
    analizar_archivo_sasbot,
    chat_sasbot,
    construir_system_prompt,
    detectar_emergencia,
)

# ── detectar_emergencia ────────────────────────────────────────────


def test_detectar_emergencia_positivo():
    assert detectar_emergencia("me caí y me lastimé") is True


def test_detectar_emergencia_con_accidente():
    assert detectar_emergencia("Hubo un accidente en la planta") is True


def test_detectar_emergencia_negativo():
    assert detectar_emergencia("¿Cuál es el EPP requerido?") is False


def test_detectar_emergencia_mayusculas():
    assert detectar_emergencia("EMERGENCIA en el piso 3") is True


# ── construir_system_prompt ────────────────────────────────────────


def test_construir_system_prompt_empleado():
    prompt = construir_system_prompt("Operario", "Producción", "empleado")
    assert "Operario" in prompt
    assert "Producción" in prompt
    assert "Puede reportar incidentes" in prompt


def test_construir_system_prompt_gerencia():
    prompt = construir_system_prompt("Gerente", "Dirección", "gerencia")
    assert "reportes ejecutivos" in prompt


def test_construir_system_prompt_sst():
    prompt = construir_system_prompt("Encargado SST", "SST", "sst")
    assert "experto técnico" in prompt


def test_construir_system_prompt_rol_invalido():
    prompt = construir_system_prompt("Cargo", "Área", "desconocido")
    assert "Puede reportar incidentes" in prompt


# ── chat_sasbot ────────────────────────────────────────────────────


def _mock_genai_response(texto: str):
    resp = MagicMock()
    resp.text = texto
    return resp


def test_chat_sasbot_respuesta_normal():
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "Debe usar casco y guantes."
        )
        resultado = chat_sasbot("¿Qué EPP debo usar?", "Operario", "Producción")
    assert resultado["respuesta"] == "Debe usar casco y guantes."
    assert resultado["modo_emergencia"] is False


def test_chat_sasbot_modo_emergencia():
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "Llama al 123 de inmediato."
        )
        resultado = chat_sasbot("me caí y tengo sangre", "Operario", "Bodega")
    assert resultado["modo_emergencia"] is True
    assert "respuesta" in resultado


def test_chat_sasbot_con_historial():
    historial = [
        {"role": "user", "content": "Hola"},
        {"role": "model", "content": "Hola, soy SASBOT"},
    ]
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "Claro, te ayudo."
        )
        resultado = chat_sasbot(
            "¿Me puedes ayudar?",
            historial=historial,
            rol="sst",
        )
    assert resultado["respuesta"] == "Claro, te ayudo."


def test_chat_sasbot_rol_gerencia():
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "El indicador de accidentes bajó un 20%."
        )
        resultado = chat_sasbot(
            "Dame el resumen de accidentes", cargo="Gerente", rol="gerencia"
        )
    assert "respuesta" in resultado


# ── analizar_archivo_sasbot ────────────────────────────────────────


def test_analizar_archivo_word_devuelve_mensaje():
    resultado = analizar_archivo_sasbot(
        b"contenido",
        "application/msword",
        "reporte.doc",
    )
    assert "Word" in resultado
    assert "PDF" in resultado


def test_analizar_archivo_docx_devuelve_mensaje():
    resultado = analizar_archivo_sasbot(
        b"contenido",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "reporte.docx",
    )
    assert "Word" in resultado


def test_analizar_archivo_pdf():
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "El documento muestra riesgos en altura."
        )
        resultado = analizar_archivo_sasbot(
            b"%PDF-fake",
            "application/pdf",
            "matriz.pdf",
            mensaje="Analiza los riesgos",
        )
    assert resultado == "El documento muestra riesgos en altura."


def test_analizar_archivo_imagen_sin_mensaje():
    with patch("app.services.ai_service.client") as mock_client:
        mock_client.models.generate_content.return_value = _mock_genai_response(
            "La imagen muestra falta de EPP."
        )
        resultado = analizar_archivo_sasbot(
            b"\xff\xd8\xff",
            "image/jpeg",
            "foto.jpg",
        )
    assert "EPP" in resultado
