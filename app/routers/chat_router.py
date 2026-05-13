# app/routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.chat_historial import ChatHistorial
from app.services.ai_service import chat_sasbot

router = APIRouter(prefix="/chat", tags=["SASBOT - Chat IA"])


# ── Schemas ───────────────────────────────────────────────────────

class MensajeRequest(BaseModel):
    mensaje: str

class ReporteRapidoRequest(BaseModel):
    tipo: str  # "accidente", "condicion_insegura", "casi_accidente"
    descripcion: str


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/mensaje")
def enviar_mensaje(
    datos: MensajeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recibe un mensaje del empleado autenticado y retorna
    la respuesta del SASBOT personalizada según su cargo y área.
    Guarda cada conversación en el historial de la BD.
    """
    # Obtener cargo y área del usuario autenticado
    # Si no tiene cargo o área asignada, usar valores por defecto
    cargo = current_user.cargo.nombre if current_user.cargo else "empleado general"
    area  = current_user.area.nombre  if current_user.area  else "área general"

    # Llamar al SASBOT con el mensaje y el perfil del usuario
    resultado = chat_sasbot(
        mensaje=datos.mensaje,
        cargo=cargo,
        area=area
    )

    # Guardar en el historial de la BD
    historial_entrada = ChatHistorial(
        mensaje=datos.mensaje,
        respuesta=resultado["respuesta"],
        user_id=current_user.id
    )
    db.add(historial_entrada)
    db.commit()

    return {
        "respuesta": resultado["respuesta"],
        "modo_emergencia": resultado["modo_emergencia"]
    }


@router.get("/historial")
def obtener_historial(
    pagina: int = 1,
    limite: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna el historial de conversaciones del usuario autenticado.
    Paginado: página 1 trae los primeros 20 mensajes, página 2 los siguientes, etc.
    Cada usuario solo puede ver SU propio historial.
    """
    offset = (pagina - 1) * limite

    historial = db.query(ChatHistorial)\
        .filter(ChatHistorial.user_id == current_user.id)\
        .order_by(ChatHistorial.timestamp.desc())\
        .offset(offset)\
        .limit(limite)\
        .all()

    return [
        {
            "mensaje": h.mensaje,
            "respuesta": h.respuesta,
            "timestamp": h.timestamp
        }
        for h in historial
    ]


@router.post("/reporte-rapido", status_code=201)
def reporte_rapido(
    datos: ReporteRapidoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Permite al empleado reportar un incidente directamente desde el chat.
    Los datos del empleado se autocompletan desde su perfil autenticado.
    El reporte queda guardado para que el Encargado SST lo vea en su panel.
    """
    # Validar tipo de reporte
    tipos_validos = ["accidente", "condicion_insegura", "casi_accidente"]
    if datos.tipo not in tipos_validos:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Debe ser uno de: {tipos_validos}"
        )

    # Por ahora guardamos el reporte como mensaje en el historial
    # En el Sprint 2 se conectará con el modelo Incidente
    mensaje_reporte = f"[REPORTE {datos.tipo.upper()}]: {datos.descripcion}"
    respuesta_automatica = (
        f"Tu reporte de {datos.tipo.replace('_', ' ')} ha sido registrado exitosamente. "
        f"El Encargado SST ha sido notificado y se comunicará contigo pronto. "
        f"Recuerda: si es una emergencia llama al 123."
    )

    historial_entrada = ChatHistorial(
        mensaje=mensaje_reporte,
        respuesta=respuesta_automatica,
        user_id=current_user.id
    )
    db.add(historial_entrada)
    db.commit()

    return {
        "mensaje": "Reporte registrado exitosamente",
        "tipo": datos.tipo,
        "notificado_sst": True
    }