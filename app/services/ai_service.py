# app/services/ai_service.py
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Crear el cliente con la API key
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Modelo a usar — gemini-2.0-flash es gratuito y rápido
MODELO = "gemini-2.5-flash"

# Palabras que activan el modo emergencia automáticamente
PALABRAS_EMERGENCIA = [
    "me caí",
    "me cai",
    "accidente",
    "herido",
    "herida",
    "lesión",
    "lesion",
    "me lastimé",
    "me lastime",
    "emergencia",
    "auxilio",
    "ayuda urgente",
    "sangre",
    "no respira",
    "fractura",
    "inconsciente",
]


def detectar_emergencia(mensaje: str) -> bool:
    """
    Revisa si el mensaje contiene palabras de emergencia.
    Retorna True si es emergencia, False si es consulta normal.
    """
    mensaje_lower = mensaje.lower()
    return any(palabra in mensaje_lower for palabra in PALABRAS_EMERGENCIA)


def construir_system_prompt(cargo: str, area: str, rol: str = "empleado") -> str:
    """
    Construye el contexto que le damos a Gemini para que sepa
    quién es, a quién le habla y cómo debe responder.
    """
    _accesos_por_rol = {
        "gerencia": "Puede solicitar reportes ejecutivos, métricas consolidadas e informes de cumplimiento del SG-SST.",
        "sst": "Puede gestionar incidentes, riesgos, capacitaciones y auditorías. Es el experto técnico en SST de la empresa.",
        "empleado": "Puede reportar incidentes y consultar información sobre seguridad en su área de trabajo.",
    }
    accesos = _accesos_por_rol.get(rol, _accesos_por_rol["empleado"])

    return f"""Eres SASBOT, el asistente virtual de Seguridad y Salud en el
Trabajo (SST) de la plataforma PISST para empresas colombianas.

DATOS DEL USUARIO QUE TE CONSULTA:
- Cargo: {cargo}
- Área de trabajo: {area}
- Rol en el sistema: {rol}
- Accesos disponibles: {accesos}

TUS REGLAS:
1. Responde SIEMPRE en español claro y sencillo, sin tecnicismos innecesarios.
2. Personaliza tus respuestas según el cargo, área y rol del usuario.
3. Si el rol es "gerencia", puedes ofrecerle accesos rápidos a informes y métricas además de las consultas habituales.
4. Si el rol es "sst", puedes usar terminología técnica y asumir conocimiento del SG-SST.
5. Basa tus respuestas en normativa colombiana vigente:
   - Decreto 1072 de 2015 (Reglamento Único del Sector Trabajo)
   - Resolución 0312 de 2019 (Estándares mínimos del SG-SST)
   - Ley 1562 de 2012 (Sistema General de Riesgos Laborales)
6. Si no sabes algo con certeza, indícalo y sugiere consultar al Encargado SST.
7. NUNCA inventes normas, artículos o estadísticas.
8. Para preguntas sobre EPP, considera los riesgos específicos del cargo.
9. Sé empático y comprensivo.

TEMAS QUE PUEDES RESPONDER:
- Derechos y deberes del trabajador en SST
- EPP requerido según el cargo
- Qué hacer en caso de accidente o emergencia
- Normas de seguridad colombianas
- Prevención de riesgos laborales
- Cómo reportar un incidente

LO QUE NO DEBES HACER:
- Responder preguntas que no sean de SST
- Dar diagnósticos médicos
- Reemplazar la atención de un profesional SST
"""


def chat_sasbot(
    mensaje: str,
    cargo: str = "empleado general",
    area: str = "área general",
    rol: str = "empleado",
    historial: list = None,
) -> dict:
    """
    Función principal del SASBOT.
    Recibe el mensaje del empleado y retorna la respuesta de Gemini.
    """
    # 1. Detectar emergencia ANTES de llamar a la IA
    es_emergencia = detectar_emergencia(mensaje)

    # 2. Si es emergencia, agregar instrucción especial
    contenido = mensaje
    if es_emergencia:
        contenido += """

[MODO EMERGENCIA]:
El empleado reporta una emergencia. Debes:
1. Dar instrucciones inmediatas y claras de qué hacer AHORA
2. Indicar que llame a emergencias: 123
3. Decirle que notifique al Encargado SST inmediatamente
4. Recomendar no mover al herido si hay lesión grave
5. Usar un tono calmado pero urgente
"""

    # 3. Construir el historial para Gemini
    contents = []
    if historial:
        for msg in historial:
            contents.append(
                types.Content(role=msg["role"], parts=[types.Part(text=msg["content"])])
            )

    # 4. Agregar el mensaje actual
    contents.append(types.Content(role="user", parts=[types.Part(text=contenido)]))

    # 5. Llamar a Gemini
    response = client.models.generate_content(
        model=MODELO,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=construir_system_prompt(cargo, area, rol),
            max_output_tokens=8192,
            temperature=0.7,
        ),
    )

    return {"respuesta": response.text, "modo_emergencia": es_emergencia}


def analizar_archivo_sasbot(
    contenido_bytes: bytes,
    mime_type: str,
    nombre_archivo: str,
    mensaje: str = "",
) -> str:
    """
    Analiza un archivo (imagen o PDF) con Gemini y retorna la respuesta de SASBOT.
    Para DOC/DOCX retorna mensaje indicando que debe convertirse a PDF.
    """
    TIPOS_DOC = {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    if mime_type in TIPOS_DOC:
        return (
            f"El archivo '{nombre_archivo}' es un documento Word. "
            "SASBOT no puede leer documentos Word directamente. "
            "Por favor conviértelo a PDF y vuelve a enviarlo."
        )

    contexto = (
        mensaje
        if mensaje
        else "Analiza este documento en el contexto de Seguridad y Salud en el Trabajo (SST) según la normativa colombiana."
    )

    parte_archivo = types.Part.from_bytes(data=contenido_bytes, mime_type=mime_type)
    parte_texto = types.Part(text=contexto)

    response = client.models.generate_content(
        model=MODELO,
        contents=[types.Content(role="user", parts=[parte_archivo, parte_texto])],
        config=types.GenerateContentConfig(
            system_instruction=construir_system_prompt("empleado", "área general"),
            max_output_tokens=1500,
            temperature=0.5,
        ),
    )

    return response.text
