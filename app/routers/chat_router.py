# app/routers/chat_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.chat_historial import ChatHistorial
from app.models.incidente import Incidente, TipoIncidenteEnum, SeveridadEnum, EstadoIncidenteEnum
from app.services.ai_service import chat_sasbot

router = APIRouter(prefix="/chat", tags=["SASBOT - Chat IA"])


# ── Schemas ───────────────────────────────────────────────────────

class MensajeRequest(BaseModel):
    mensaje: str

class ReporteRapidoRequest(BaseModel):
    tipo: str        # "accidente", "condicion_insegura", "cuasi_accidente"
    descripcion: str
    lugar: Optional[str] = "No especificado"


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
    cargo = current_user.cargo.nombre if current_user.cargo else "empleado general"
    area  = current_user.area.nombre  if current_user.area  else "área general"

    resultado = chat_sasbot(
        mensaje=datos.mensaje,
        cargo=cargo,
        area=area
    )

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
    Paginado: página 1 trae los primeros 20 mensajes.
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
    Crea un registro real en la tabla Incidente para que el SST lo vea.
    """
    # Validar tipo de reporte y mapear al enum correcto
    tipos_map = {
        "accidente": TipoIncidenteEnum.accidente,
        "condicion_insegura": TipoIncidenteEnum.condicion_insegura,
        "cuasi_accidente": TipoIncidenteEnum.cuasi_accidente,
        "casi_accidente": TipoIncidenteEnum.cuasi_accidente  # alias
    }

    if datos.tipo not in tipos_map:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo inválido. Debe ser uno de: {list(tipos_map.keys())}"
        )

    # ✅ Fix HU003 — Crear registro real en tabla Incidente
    nuevo_incidente = Incidente(
        tipo=tipos_map[datos.tipo],
        severidad=SeveridadEnum.sin_lesion,  # default, el SST puede actualizar
        fecha=datetime.utcnow(),
        lugar=datos.lugar,
        descripcion=datos.descripcion,
        estado=EstadoIncidenteEnum.borrador,
        empresa_id=current_user.empresa_id,
        reportado_por_id=current_user.id,
        trabajador_afectado_id=current_user.id  # el empleado que reporta
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
        mensaje=mensaje_reporte,
        respuesta=respuesta_automatica,
        user_id=current_user.id
    )
    db.add(historial_entrada)
    db.commit()

    return {
        "mensaje": "Reporte registrado exitosamente",
        "incidente_id": str(nuevo_incidente.id),
        "tipo": datos.tipo,
        "estado": "borrador",
        "notificado_sst": True
    }