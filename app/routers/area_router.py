from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.area import Area
from app.models.user import User
from app.schemas.area_schema import AreaCreate, AreaResponse

router = APIRouter(prefix="/areas", tags=["Áreas"])


@router.get("/", response_model=List[AreaResponse])
def listar_areas(
    db: Session = Depends(get_db), current_user: User = Depends(require_role("sst"))
):
    return (
        db.query(Area)
        .filter(Area.empresa_id == current_user.empresa_id, Area.activo == True)
        .all()
    )


@router.post("/", response_model=AreaResponse, status_code=201)
def crear_area(
    datos: AreaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    if (
        db.query(Area)
        .filter(
            Area.empresa_id == current_user.empresa_id,
            Area.nombre == datos.nombre,
            Area.activo == True,
        )
        .first()
    ):
        raise HTTPException(status_code=400, detail="Ya existe un área con ese nombre")

    area = Area(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        empresa_id=current_user.empresa_id,
    )
    db.add(area)
    db.commit()
    db.refresh(area)
    return area
