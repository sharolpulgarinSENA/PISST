# tests/test_analytics_service.py
import uuid
from datetime import datetime, timezone

from app.models.capacitacion import Asistencia, Capacitacion, SesionCapacitacion
from app.models.incidente import Incidente, SeveridadEnum, TipoIncidenteEnum
from app.models.riesgo import (
    EstadoControlEnum,
    EvaluacionRiesgo,
    MedidaControl,
    NivelRiesgoEnum,
    Peligro,
    TipoControlEnum,
    TipoPeligroEnum,
)
from app.services import analytics_service

# ── helpers ──────────────────────────────────────────────────────────


def make_incidente(
    db, empresa, usuario, tipo=TipoIncidenteEnum.incidente, severidad=SeveridadEnum.leve
):
    inc = Incidente(
        tipo=tipo,
        severidad=severidad,
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
        lugar="Bodega",
        descripcion="Descripción test",
        empresa_id=empresa.id,
        reportado_por_id=usuario.id,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)
    return inc


def make_peligro(db, empresa):
    p = Peligro(
        descripcion="Peligro test",
        tipo=TipoPeligroEnum.fisico,
        empresa_id=empresa.id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_evaluacion_riesgo(db, peligro, nivel=NivelRiesgoEnum.alto, residual=False):
    ev = EvaluacionRiesgo(
        probabilidad=3,
        severidad=3,
        nivel_riesgo=nivel,
        es_residual=residual,
        fecha_evaluacion=datetime.now(timezone.utc).replace(tzinfo=None),
        peligro_id=peligro.id,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def make_medida_control(db, peligro, estado=EstadoControlEnum.completada):
    mc = MedidaControl(
        descripcion="Medida test",
        tipo=TipoControlEnum.administrativo,
        estado=estado,
        peligro_id=peligro.id,
    )
    db.add(mc)
    db.commit()
    db.refresh(mc)
    return mc


def make_capacitacion_con_sesion(db, empresa, estado_sesion="realizada"):
    cap = Capacitacion(
        titulo="Cap test",
        duracion_horas=2,
        empresa_id=empresa.id,
    )
    db.add(cap)
    db.commit()
    db.refresh(cap)

    ses = SesionCapacitacion(
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
        estado=estado_sesion,
        capacitacion_id=cap.id,
    )
    db.add(ses)
    db.commit()
    db.refresh(ses)
    return cap, ses


def make_asistencia(db, sesion, empleado, estado="presente"):
    a = Asistencia(
        sesion_id=sesion.id,
        empleado_id=empleado.id,
        estado=estado,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def make_respuesta_empleado(db, evaluacion, empleado, aprobado=True):
    from app.schemas.capacitacion import ResponderEvaluacionRequest, RespuestaCreate
    from app.services import capacitacion_service

    pregunta = evaluacion.preguntas[0]
    respuesta_correcta = pregunta.respuesta_correcta if aprobado else "z"
    request = ResponderEvaluacionRequest(
        evaluacion_id=evaluacion.id,
        respuestas=[
            RespuestaCreate(pregunta_id=pregunta.id, respuesta_dada=respuesta_correcta)
        ],
    )
    return capacitacion_service.responder_evaluacion(db, request, empleado.id)


# ── analizar_incidentes ──────────────────────────────────────────────


def test_analytics_incidentes_sin_datos(db, empresa, usuario_sst):
    resultado = analytics_service.analizar_incidentes(db, empresa.id)
    assert resultado["total_incidentes"] == 0
    assert resultado["por_tipo"] == {}
    assert resultado["por_severidad"] == {}
    assert resultado["tasa_mensual_promedio"] == 0.0
    assert resultado["tendencia"] == "sin_datos"


def test_analytics_incidentes_con_datos(db, empresa, usuario_sst):
    make_incidente(
        db, empresa, usuario_sst, TipoIncidenteEnum.accidente, SeveridadEnum.grave
    )
    make_incidente(
        db, empresa, usuario_sst, TipoIncidenteEnum.incidente, SeveridadEnum.leve
    )

    resultado = analytics_service.analizar_incidentes(db, empresa.id)

    assert resultado["total_incidentes"] >= 2
    assert "accidente" in resultado["por_tipo"]
    assert "incidente" in resultado["por_tipo"]
    assert resultado["tasa_mensual_promedio"] > 0


def test_analytics_multitenant_incidentes(db, empresa, usuario_sst):
    from app.core.security import get_password_hash
    from app.models.empresa import Empresa
    from app.models.user import RoleEnum, User

    emp2 = Empresa(nombre="Otra empresa", nit=uuid.uuid4().hex[:12], sector="X")
    db.add(emp2)
    db.commit()
    db.refresh(emp2)

    user2 = User(
        nombre="User2",
        email=f"u2_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=get_password_hash("pw"),
        role=RoleEnum.sst,
        empresa_id=emp2.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user2)
    db.commit()
    db.refresh(user2)

    make_incidente(db, emp2, user2)
    conteo_antes = analytics_service.analizar_incidentes(db, empresa.id)[
        "total_incidentes"
    ]
    make_incidente(db, emp2, user2)
    conteo_despues = analytics_service.analizar_incidentes(db, empresa.id)[
        "total_incidentes"
    ]
    # La empresa original no ve incidentes de emp2
    assert conteo_antes == conteo_despues


# ── analizar_riesgos ─────────────────────────────────────────────────


def test_analytics_riesgos_sin_datos(db, empresa):
    resultado = analytics_service.analizar_riesgos(db, empresa.id)
    assert resultado["total_peligros"] == 0
    assert resultado["pct_con_control_implementado"] == 0.0


def test_analytics_riesgos_distribucion(db, empresa):
    p1 = make_peligro(db, empresa)
    p2 = make_peligro(db, empresa)
    make_evaluacion_riesgo(db, p1, NivelRiesgoEnum.alto)
    make_evaluacion_riesgo(db, p2, NivelRiesgoEnum.critico)

    resultado = analytics_service.analizar_riesgos(db, empresa.id)

    assert resultado["total_peligros"] >= 2
    total_por_nivel = sum(resultado["por_nivel"].values())
    assert total_por_nivel == resultado["total_peligros"]


def test_analytics_riesgos_pct_control(db, empresa):
    p1 = make_peligro(db, empresa)
    make_peligro(db, empresa)  # segundo peligro sin medida — reduce el %
    make_medida_control(db, p1, EstadoControlEnum.completada)

    resultado = analytics_service.analizar_riesgos(db, empresa.id)

    assert resultado["pct_con_control_implementado"] > 0
    assert resultado["pct_con_control_implementado"] <= 100


# ── analizar_capacitaciones ──────────────────────────────────────────


def test_analytics_capacitaciones_sin_datos(db, empresa):
    resultado = analytics_service.analizar_capacitaciones(db, empresa.id)
    assert resultado["total_evaluaciones"] == 0
    assert resultado["tasa_aprobacion_pct"] == 0.0
    assert resultado["asistencia_promedio_pct"] == 0.0
    assert resultado["alertas_asistencia"] == []


def test_analytics_capacitaciones_aprobacion(db, empresa, usuario_sst):
    from app.schemas.capacitacion import EvaluacionCreate, PreguntaCreate
    from app.services import capacitacion_service

    cap, ses = make_capacitacion_con_sesion(db, empresa, "realizada")

    ev = capacitacion_service.create_evaluacion(
        db,
        EvaluacionCreate(
            titulo="Eval test",
            puntaje_minimo=60,
            sesion_id=ses.id,
            preguntas=[
                PreguntaCreate(
                    texto="¿Test?",
                    opcion_a="A",
                    opcion_b="B",
                    opcion_c="C",
                    opcion_d="D",
                    respuesta_correcta="a",
                )
            ],
        ),
    )

    make_respuesta_empleado(db, ev, usuario_sst, aprobado=True)

    resultado = analytics_service.analizar_capacitaciones(db, empresa.id)
    assert resultado["total_evaluaciones"] >= 1
    assert resultado["tasa_aprobacion_pct"] > 0


def test_analytics_alerta_asistencia(db, empresa, usuario_sst):
    cap, ses = make_capacitacion_con_sesion(db, empresa, "realizada")
    make_asistencia(db, ses, usuario_sst, "ausente")

    resultado = analytics_service.analizar_capacitaciones(db, empresa.id)

    # Un empleado con 0% asistencia debe generar alerta
    assert resultado["asistencia_promedio_pct"] < 100
    assert len(resultado["alertas_asistencia"]) >= 1


def test_analytics_capacitaciones_sin_sesion_realizada(db, empresa):
    cap = Capacitacion(titulo="Cap programada", duracion_horas=1, empresa_id=empresa.id)
    db.add(cap)
    db.commit()

    ses = SesionCapacitacion(
        fecha=datetime.now(timezone.utc).replace(tzinfo=None),
        estado="programada",
        capacitacion_id=cap.id,
    )
    db.add(ses)
    db.commit()

    resultado = analytics_service.analizar_capacitaciones(db, empresa.id)
    assert resultado["capacitaciones_sin_sesion_realizada"] >= 1


# ── calcular_cumplimiento ────────────────────────────────────────────


def test_analytics_cumplimiento_vacio(db, empresa):
    resultado = analytics_service.calcular_cumplimiento(db, empresa.id)
    assert resultado["score_total"] == 0.0
    assert "incidentes_investigados" in resultado["desglose"]
    assert "peligros_con_control" in resultado["desglose"]
    assert "capacitaciones_realizadas" in resultado["desglose"]
    assert "no_conformidades_cerradas" in resultado["desglose"]


def test_analytics_cumplimiento_con_datos_parciales(db, empresa):
    # Agregar una capacitación con sesión realizada para subir el score
    make_capacitacion_con_sesion(db, empresa, "realizada")

    resultado = analytics_service.calcular_cumplimiento(db, empresa.id)
    assert 0 <= resultado["score_total"] <= 100
    assert resultado["desglose"]["capacitaciones_realizadas"] > 0
