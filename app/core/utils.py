# app/core/utils.py
from datetime import date, timedelta
from typing import Literal, Optional, Tuple

PeriodoType = Literal["mes", "trimestre", "anio"]

_DIAS_POR_PERIODO = {"mes": 30, "trimestre": 90, "anio": 365}


def periodo_a_rango(periodo: Optional[str]) -> Tuple[Optional[date], Optional[date]]:
    """
    Convierte un periodo ("mes" | "trimestre" | "anio") en un rango
    (fecha_desde, fecha_hasta) terminando hoy. Si periodo es None o no
    es reconocido, retorna (None, None) — sin filtro de fecha.
    """
    dias = _DIAS_POR_PERIODO.get(periodo) if periodo else None
    if dias is None:
        return None, None

    hoy = date.today()
    return hoy - timedelta(days=dias), hoy
