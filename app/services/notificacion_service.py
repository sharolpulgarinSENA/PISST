# app/services/notificacion_service.py
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notificacion import Notificacion


def crear_notificacion(
    db: Session,
    empresa_id: UUID,
    tipo: str,
    titulo: str,
    descripcion: str,
    modulo: str,
    url_destino: str,
) -> None:
    _purgar_antiguos(db, empresa_id)
    notif = Notificacion(
        empresa_id=empresa_id,
        tipo=tipo,
        titulo=titulo,
        descripcion=descripcion,
        modulo=modulo,
        url_destino=url_destino,
    )
    db.add(notif)


def get_feed(db: Session, empresa_id: UUID, limit: int, offset: int) -> dict:
    _purgar_antiguos(db, empresa_id)
    total = db.query(Notificacion).filter(Notificacion.empresa_id == empresa_id).count()
    eventos = (
        db.query(Notificacion)
        .filter(Notificacion.empresa_id == empresa_id)
        .order_by(Notificacion.fecha.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "eventos": [
            {
                "id": str(e.id),
                "tipo": e.tipo,
                "titulo": e.titulo,
                "descripcion": e.descripcion,
                "modulo": e.modulo,
                "url_destino": e.url_destino,
                "fecha": e.fecha,
                "leido": e.leido,
            }
            for e in eventos
        ],
    }


def marcar_leido(db: Session, notificacion_id: UUID, empresa_id: UUID) -> dict:
    notif = (
        db.query(Notificacion)
        .filter(
            Notificacion.id == notificacion_id,
            Notificacion.empresa_id == empresa_id,
        )
        .first()
    )
    if not notif:
        return None
    notif.leido = True
    db.commit()
    db.refresh(notif)
    return {"id": str(notif.id), "leido": notif.leido}


def marcar_todas_leidas(db: Session, empresa_id: UUID) -> dict:
    actualizadas = (
        db.query(Notificacion)
        .filter(
            Notificacion.empresa_id == empresa_id,
            Notificacion.leido == False,
        )
        .update({"leido": True})
    )
    db.commit()
    return {"actualizadas": actualizadas}


def _purgar_antiguos(db: Session, empresa_id: UUID) -> None:
    limite = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    db.query(Notificacion).filter(
        Notificacion.empresa_id == empresa_id,
        Notificacion.fecha < limite,
    ).delete()
