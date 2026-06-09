# app/routers/notificacion_router.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services import notificacion_service

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("/feed")
def feed_notificaciones(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Feed de eventos de la empresa, del más reciente al más antiguo."""
    return notificacion_service.get_feed(db, current_user.empresa_id, limit, offset)


@router.patch("/{notificacion_id}/leido")
def marcar_leido(
    notificacion_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca una notificación como leída."""
    resultado = notificacion_service.marcar_leido(
        db, notificacion_id, current_user.empresa_id
    )
    if not resultado:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return resultado


@router.patch("/leer-todas")
def leer_todas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca todas las notificaciones no leídas como leídas."""
    return notificacion_service.marcar_todas_leidas(db, current_user.empresa_id)
