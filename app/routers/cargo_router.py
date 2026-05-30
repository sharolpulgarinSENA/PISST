from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.area import Area
from app.models.cargo import Cargo
from app.models.user import User
from app.schemas.cargo_schema import CargoCreate, CargoResponse

router = APIRouter(prefix="/cargos", tags=["Cargos"])


@router.get("/", response_model=List[CargoResponse])
def listar_cargos(
    db: Session = Depends(get_db), current_user: User = Depends(require_role("sst"))
):
    return (
        db.query(Cargo)
        .filter(Cargo.empresa_id == current_user.empresa_id, Cargo.activo == True)
        .all()
    )


@router.post("/", response_model=CargoResponse, status_code=201)
def crear_cargo(
    datos: CargoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("sst")),
):
    area = (
        db.query(Area)
        .filter(
            Area.id == datos.area_id,
            Area.empresa_id == current_user.empresa_id,
            Area.activo == True,
        )
        .first()
    )
    if not area:
        raise HTTPException(
            status_code=404, detail="Área no encontrada o no pertenece a tu empresa"
        )

    if (
        db.query(Cargo)
        .filter(
            Cargo.empresa_id == current_user.empresa_id,
            Cargo.nombre == datos.nombre,
            Cargo.activo == True,
        )
        .first()
    ):
        raise HTTPException(status_code=400, detail="Ya existe un cargo con ese nombre")

    cargo = Cargo(
        nombre=datos.nombre, area_id=datos.area_id, empresa_id=current_user.empresa_id
    )
    db.add(cargo)
    db.commit()
    db.refresh(cargo)
    return cargo
