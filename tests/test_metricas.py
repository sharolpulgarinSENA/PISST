# tests/test_metricas.py
from app.services.metricas_service import get_kpis


def test_kpis_empresa_sin_datos(db, empresa):
    resultado = get_kpis(db, empresa.id)
    assert resultado["total_trabajadores"] == 0
    assert resultado["total_accidentes"] == 0
    assert resultado["tasa_accidentalidad"] == 0
    assert resultado["indice_frecuencia"] == 0
    assert resultado["indice_severidad"] == 0


def test_kpis_no_divide_por_cero(db, empresa):
    resultado = get_kpis(db, empresa.id)
    assert isinstance(resultado["tasa_accidentalidad"], (int, float))
    assert isinstance(resultado["indice_frecuencia"], (int, float))
    assert isinstance(resultado["indice_severidad"], (int, float))
