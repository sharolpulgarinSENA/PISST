# tests/test_schemas.py
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.capacitacion import AsistenciaCreate
from app.schemas.incidente import (
    AccionCorrectivaCreate,
    AccionCorrectivaUpdate,
    IncidenteCreate,
    IncidenteEstadoUpdate,
    IncidenteUpdate,
)
from app.schemas.riesgo import MedidaControlCreate, MedidaControlUpdate, PeligroCreate

# ── IncidenteCreate ───────────────────────────────────────────────


def test_incidente_enum_valido():
    datos = IncidenteCreate(
        tipo="accidente",
        severidad="leve",
        fecha=datetime.now(timezone.utc),
        lugar="Bodega",
        descripcion="Caída",
    )
    assert datos.tipo.value == "accidente"
    assert datos.severidad.value == "leve"


def test_incidente_tipo_invalido_422():
    with pytest.raises(ValidationError):
        IncidenteCreate(
            tipo="invalido_xyz",
            severidad="leve",
            fecha=datetime.now(timezone.utc),
            lugar="Bodega",
            descripcion="Caída",
        )


def test_incidente_severidad_invalida_422():
    with pytest.raises(ValidationError):
        IncidenteCreate(
            tipo="accidente",
            severidad="catastrofico",
            fecha=datetime.now(timezone.utc),
            lugar="Bodega",
            descripcion="Caída",
        )


def test_incidente_todos_los_tipos_validos():
    for tipo in ("accidente", "incidente", "cuasi_accidente", "condicion_insegura"):
        datos = IncidenteCreate(
            tipo=tipo,
            severidad="leve",
            fecha=datetime.now(timezone.utc),
            lugar="X",
            descripcion="X",
        )
        assert datos.tipo.value == tipo


def test_incidente_todas_las_severidades_validas():
    for sev in ("sin_lesion", "leve", "moderada", "grave", "mortal"):
        datos = IncidenteCreate(
            tipo="incidente",
            severidad=sev,
            fecha=datetime.now(timezone.utc),
            lugar="X",
            descripcion="X",
        )
        assert datos.severidad.value == sev


# ── IncidenteEstadoUpdate ─────────────────────────────────────────


def test_incidente_estado_valido():
    for estado in ("borrador", "en_revision", "abierto", "en_investigacion", "cerrado"):
        datos = IncidenteEstadoUpdate(estado=estado)
        assert datos.estado.value == estado


def test_incidente_estado_invalido_422():
    with pytest.raises(ValidationError):
        IncidenteEstadoUpdate(estado="estado_inventado")


# ── IncidenteUpdate ───────────────────────────────────────────────


def test_incidente_update_severidad_invalida_422():
    with pytest.raises(ValidationError):
        IncidenteUpdate(severidad="muy_grave")


def test_incidente_update_severidad_none_valido():
    datos = IncidenteUpdate(severidad=None)
    assert datos.severidad is None


# ── AccionCorrectivaCreate / Update ───────────────────────────────


def test_accion_prioridad_valida():
    import uuid
    from datetime import timedelta

    datos = AccionCorrectivaCreate(
        descripcion="Corregir piso",
        prioridad="alta",
        fecha_limite=datetime.now(timezone.utc) + timedelta(days=7),
        responsable_id=uuid.uuid4(),
    )
    assert datos.prioridad.value == "alta"


def test_accion_prioridad_invalida_422():
    import uuid
    from datetime import timedelta

    with pytest.raises(ValidationError):
        AccionCorrectivaCreate(
            descripcion="X",
            prioridad="urgente",
            fecha_limite=datetime.now(timezone.utc) + timedelta(days=1),
            responsable_id=uuid.uuid4(),
        )


def test_accion_estado_invalido_422():
    with pytest.raises(ValidationError):
        AccionCorrectivaUpdate(estado="terminada")


def test_accion_estado_valido():
    for estado in ("planificada", "en_ejecucion", "completada", "vencida"):
        datos = AccionCorrectivaUpdate(estado=estado)
        assert datos.estado.value == estado


# ── PeligroCreate ─────────────────────────────────────────────────


def test_riesgo_enum_valido():
    datos = PeligroCreate(descripcion="Ruido excesivo", tipo="fisico")
    assert datos.tipo.value == "fisico"


def test_riesgo_tipo_invalido_422():
    with pytest.raises(ValidationError):
        PeligroCreate(descripcion="Algo", tipo="desconocido")


def test_riesgo_todos_los_tipos_validos():
    tipos = (
        "fisico",
        "quimico",
        "biologico",
        "ergonomico",
        "psicosocial",
        "mecanico",
        "electrico",
        "locativo",
        "fenomeno_natural",
    )
    for tipo in tipos:
        datos = PeligroCreate(descripcion="X", tipo=tipo)
        assert datos.tipo.value == tipo


# ── MedidaControlCreate / Update ─────────────────────────────────


def test_medida_tipo_valido():
    datos = MedidaControlCreate(descripcion="Usar EPP", tipo="epp")
    assert datos.tipo.value == "epp"


def test_medida_tipo_invalido_422():
    with pytest.raises(ValidationError):
        MedidaControlCreate(descripcion="X", tipo="ninguno")


def test_medida_estado_invalido_422():
    with pytest.raises(ValidationError):
        MedidaControlUpdate(estado="cerrada")


def test_medida_estado_valido():
    for estado in ("planificada", "en_ejecucion", "completada"):
        datos = MedidaControlUpdate(estado=estado)
        assert datos.estado.value == estado


# ── AsistenciaCreate ──────────────────────────────────────────────


def test_capacitacion_enum_valido():
    import uuid

    datos = AsistenciaCreate(
        sesion_id=uuid.uuid4(), empleado_id=uuid.uuid4(), estado="presente"
    )
    assert datos.estado.value == "presente"


def test_asistencia_estado_invalido_422():
    import uuid

    with pytest.raises(ValidationError):
        AsistenciaCreate(
            sesion_id=uuid.uuid4(), empleado_id=uuid.uuid4(), estado="tardanza"
        )


def test_asistencia_todos_los_estados_validos():
    import uuid

    for estado in ("presente", "ausente", "justificado"):
        datos = AsistenciaCreate(
            sesion_id=uuid.uuid4(), empleado_id=uuid.uuid4(), estado=estado
        )
        assert datos.estado.value == estado


def test_asistencia_estado_requerido():
    import uuid

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        AsistenciaCreate(sesion_id=uuid.uuid4(), empleado_id=uuid.uuid4())
