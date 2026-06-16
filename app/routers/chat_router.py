# app/routers/chat_router.py
from datetime import datetime, timezone
from typing import Literal, Optional

import filetype
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.chat_historial import ChatHistorial
from app.models.incidente import (
    EstadoIncidenteEnum,
    Incidente,
    SeveridadEnum,
    TipoIncidenteEnum,
)
from app.models.user import RoleEnum, User
from app.services.ai_service import analizar_archivo_sasbot, chat_sasbot
from app.services.email_service import enviar_escalar_coordinador

router = APIRouter(prefix="/chat", tags=["SASBOT - Chat IA"])

limiter = Limiter(key_func=get_remote_address)


# ── Schemas ───────────────────────────────────────────────────────


class MensajeRequest(BaseModel):
    mensaje: str


class ReporteRapidoRequest(BaseModel):
    tipo: Literal[
        "accidente", "condicion_insegura", "cuasi_accidente", "casi_accidente"
    ]
    descripcion: str
    lugar: Optional[str] = "No especificado"


# ── Endpoints ─────────────────────────────────────────────────────


@router.post("/mensaje")
@limiter.limit("20/minute")
def enviar_mensaje(
    request: Request,
    datos: MensajeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Recibe un mensaje del empleado autenticado y retorna
    la respuesta del SASBOT personalizada según su cargo y área.
    Guarda cada conversación en el historial de la BD.
    """
    cargo = current_user.cargo.nombre if current_user.cargo else "empleado general"
    area = current_user.area.nombre if current_user.area else "área general"
    rol = current_user.role.value

    resultado = chat_sasbot(mensaje=datos.mensaje, cargo=cargo, area=area, rol=rol)

    historial_entrada = ChatHistorial(
        mensaje=datos.mensaje, respuesta=resultado["respuesta"], user_id=current_user.id
    )
    db.add(historial_entrada)
    db.commit()

    return {
        "respuesta": resultado["respuesta"],
        "modo_emergencia": resultado["modo_emergencia"],
    }


@router.get("/historial")
def obtener_historial(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retorna el historial de conversaciones del usuario autenticado.
    Paginado: página 1 trae los primeros 20 mensajes.
    Cada usuario solo puede ver SU propio historial.
    """
    offset = (pagina - 1) * limite

    historial = (
        db.query(ChatHistorial)
        .filter(ChatHistorial.user_id == current_user.id)
        .order_by(ChatHistorial.timestamp.desc())
        .offset(offset)
        .limit(limite)
        .all()
    )

    return [
        {"mensaje": h.mensaje, "respuesta": h.respuesta, "timestamp": h.timestamp}
        for h in historial
    ]


@router.post("/escalar")
def escalar_coordinador(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Notifica al coordinador SST con el historial de conversación del empleado."""
    coordinador = (
        db.query(User)
        .filter(
            User.empresa_id == current_user.empresa_id,
            User.role == RoleEnum.sst,
            User.activo == True,
        )
        .first()
    )
    if not coordinador:
        raise HTTPException(
            status_code=404, detail="No existe coordinador SST activo en la empresa"
        )

    historial = (
        db.query(ChatHistorial)
        .filter(ChatHistorial.user_id == current_user.id)
        .order_by(ChatHistorial.timestamp.asc())
        .limit(20)
        .all()
    )

    historial_dict = [
        {
            "mensaje": h.mensaje,
            "respuesta": h.respuesta,
            "timestamp": h.timestamp.strftime("%Y-%m-%d %H:%M") if h.timestamp else "",
        }
        for h in historial
    ]

    enviado = enviar_escalar_coordinador(
        email_coordinador=coordinador.email,
        nombre_coordinador=coordinador.nombre,
        nombre_empleado=current_user.nombre,
        email_empleado=current_user.email,
        historial=historial_dict,
    )

    if not enviado:
        raise HTTPException(
            status_code=500, detail="Error al enviar el correo de escalamiento"
        )

    registro = ChatHistorial(
        mensaje="[ESCALAMIENTO AL COORDINADOR SST]",
        respuesta=f"Historial enviado al coordinador {coordinador.nombre}",
        user_id=current_user.id,
    )
    db.add(registro)
    db.commit()

    return {
        "mensaje": "Escalamiento enviado exitosamente",
        "coordinador_email": coordinador.email,
        "coordinador_nombre": coordinador.nombre,
    }


MIME_PERMITIDOS = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
LIMITE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/archivo")
async def analizar_archivo(
    archivo: UploadFile = File(...),
    mensaje: Optional[str] = Form(default=""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recibe un archivo, lo analiza con Gemini y retorna la respuesta de SASBOT."""
    if archivo.content_type not in MIME_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no permitido: {archivo.content_type}",
        )

    contenido = await archivo.read()
    if len(contenido) > LIMITE_BYTES:
        raise HTTPException(
            status_code=413, detail="El archivo supera el límite de 10 MB"
        )

    tipo_real = filetype.guess(contenido)
    if not tipo_real or tipo_real.mime not in MIME_PERMITIDOS:
        raise HTTPException(status_code=422, detail="Tipo de archivo no permitido.")

    try:
        respuesta = analizar_archivo_sasbot(
            contenido_bytes=contenido,
            mime_type=archivo.content_type,
            nombre_archivo=archivo.filename,
            mensaje=mensaje or "",
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al analizar el archivo con SASBOT"
        )

    registro = ChatHistorial(
        mensaje=f"[ARCHIVO: {archivo.filename}] {mensaje or ''}".strip(),
        respuesta=respuesta,
        user_id=current_user.id,
    )
    db.add(registro)
    db.commit()

    return {
        "respuesta": respuesta,
        "modo_emergencia": False,
        "archivo_nombre": archivo.filename,
    }


@router.post("/reporte-rapido", status_code=201)
def reporte_rapido(
    datos: ReporteRapidoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permite al empleado reportar un incidente directamente desde el chat.
    Los datos del empleado se autocompletan desde su perfil autenticado.
    Crea un registro real en la tabla Incidente para que el SST lo vea.
    """
    # Validar tipo de reporte y mapear al enum correcto
    tipos_map = {
        "accidente": TipoIncidenteEnum.accidente,
        "condicion_insegura": TipoIncidenteEnum.condicion_insegura,
        "cuasi_accidente": TipoIncidenteEnum.cuasi_accidente,
        "casi_accidente": TipoIncidenteEnum.cuasi_accidente,  # alias
    }

    if datos.tipo not in tipos_map:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Debe ser uno de: {list(tipos_map.keys())}",
        )

    # ✅ Fix HU003 — Crear registro real en tabla Incidente
    nuevo_incidente = Incidente(
        tipo=tipos_map[datos.tipo],
        severidad=SeveridadEnum.sin_lesion,  # default, el SST puede actualizar
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
        lugar=datos.lugar,
        descripcion=datos.descripcion,
        estado=EstadoIncidenteEnum.borrador,
        empresa_id=current_user.empresa_id,
        reportado_por_id=current_user.id,
        trabajador_afectado_id=current_user.id,  # el empleado que reporta
    )
    db.add(nuevo_incidente)
    db.commit()
    db.refresh(nuevo_incidente)

    # También guardar en el historial del chat
    mensaje_reporte = f"[REPORTE {datos.tipo.upper()}]: {datos.descripcion}"
    respuesta_automatica = (
        f"Tu reporte de {datos.tipo.replace('_', ' ')} ha sido registrado exitosamente "
        f"con ID #{str(nuevo_incidente.id)[:8]}. "
        f"El Encargado SST ha sido notificado y se comunicará contigo pronto. "
        f"Recuerda: si es una emergencia llama al 123."
    )

    historial_entrada = ChatHistorial(
        mensaje=mensaje_reporte, respuesta=respuesta_automatica, user_id=current_user.id
    )
    db.add(historial_entrada)
    db.commit()

    return {
        "mensaje": "Reporte registrado exitosamente",
        "incidente_id": str(nuevo_incidente.id),
        "tipo": datos.tipo,
        "estado": "borrador",
        "notificado_sst": True,
    }
