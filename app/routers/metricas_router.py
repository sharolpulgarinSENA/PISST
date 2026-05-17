# app/routers/metricas_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.services import metricas_service

router = APIRouter(prefix="/metricas", tags=["Dashboard y Métricas"])

PERIODOS_VALIDOS = ["mensual", "trimestral", "anual"]


@router.get("/kpis")
def obtener_kpis(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia"))
):
    return metricas_service.get_kpis(db, current_user.empresa_id)


@router.get("/dashboard-gerencia")
def dashboard_gerencia(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia"))
):
    return metricas_service.get_dashboard_gerencia(db, current_user.empresa_id)


@router.get("/alertas")
def obtener_alertas(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst"))
):
    return metricas_service.get_alertas(db, current_user.empresa_id)


@router.get("/reporte-pdf")
def descargar_reporte_pdf(
    periodo: str = "mensual",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia"))
):
    if periodo not in PERIODOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Período inválido. Use: mensual, trimestral, anual")

    from fastapi.responses import StreamingResponse
    buffer = metricas_service.generar_reporte_pdf(db, current_user.empresa_id, periodo)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=reporte_pisst_{periodo}.pdf"}
    )


@router.get("/reporte-excel")
def descargar_reporte_excel(
    periodo: str = "mensual",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst", "gerencia"))
):
    if periodo not in PERIODOS_VALIDOS:
        raise HTTPException(status_code=400, detail="Período inválido. Use: mensual, trimestral, anual")

    from fastapi.responses import StreamingResponse
    buffer = metricas_service.generar_reporte_excel(db, current_user.empresa_id, periodo)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reporte_pisst_{periodo}.xlsx"}
    )