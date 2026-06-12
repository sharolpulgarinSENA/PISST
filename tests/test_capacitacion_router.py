# tests/test_capacitacion_router.py
"""Tests de integración para el router de capacitaciones (endpoints HTTP)."""
import uuid
from datetime import datetime, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.user import RoleEnum, User

# ── Helpers ────────────────────────────────────────────────────────


def crear_usuario(db, empresa, role=RoleEnum.sst):
    email = f"{role.value}_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        nombre="Test User",
        email=email,
        password_hash=get_password_hash("password123"),
        role=role,
        empresa_id=empresa.id,
        activo=True,
        debe_cambiar_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth(user):
    import os

    os.environ.setdefault("SECRET_KEY", "test-secret-key-para-tests-unitarios")
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def crear_capacitacion_via_api(client, headers, titulo="Cap test"):
    resp = client.post(
        "/capacitaciones/",
        json={"titulo": titulo, "duracion_horas": 4},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


def crear_sesion_via_api(client, headers, capacitacion_id):
    resp = client.post(
        "/capacitaciones/sesiones",
        json={
            "fecha": datetime.now(timezone.utc).isoformat(),
            "lugar": "Sala A",
            "capacitacion_id": str(capacitacion_id),
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ── GET /capacitaciones/ ───────────────────────────────────────────


def test_listar_capacitaciones_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get("/capacitaciones/", headers=auth(sst))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── POST /capacitaciones/ ──────────────────────────────────────────


def test_crear_capacitacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/capacitaciones/",
        json={"titulo": "Seguridad básica", "duracion_horas": 2},
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["titulo"] == "Seguridad básica"


def test_crear_capacitacion_con_areas(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.post(
        "/capacitaciones/",
        json={"titulo": "Cap con áreas", "area_ids": []},
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert "areas" in resp.json()


def test_crear_capacitacion_sin_auth(client):
    resp = client.post("/capacitaciones/", json={"titulo": "X"})
    assert resp.status_code == 401


# ── PATCH /capacitaciones/{id} ────────────────────────────────────


def test_actualizar_capacitacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    resp = client.patch(
        f"/capacitaciones/{cap['id']}",
        json={"titulo": "Título actualizado"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["titulo"] == "Título actualizado"


def test_actualizar_capacitacion_con_areas(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    resp = client.patch(
        f"/capacitaciones/{cap['id']}",
        json={"area_ids": []},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["areas"] == []


# ── GET /capacitaciones/cobertura ─────────────────────────────────


def test_cobertura_capacitaciones(client, db, empresa):
    sst = crear_usuario(db, empresa)
    resp = client.get("/capacitaciones/cobertura", headers=auth(sst))
    assert resp.status_code == 200
    assert "porcentaje" in resp.json()


# ── POST /capacitaciones/sesiones ─────────────────────────────────


def test_crear_sesion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    resp = client.post(
        "/capacitaciones/sesiones",
        json={
            "fecha": datetime.now(timezone.utc).isoformat(),
            "lugar": "Sala B",
            "capacitacion_id": cap["id"],
        },
        headers=auth(sst),
    )
    assert resp.status_code == 201


# ── PATCH /capacitaciones/sesiones/{id}/estado ────────────────────


def test_cambiar_estado_sesion_realizada(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.patch(
        f"/capacitaciones/sesiones/{sesion['id']}/estado",
        params={"estado": "realizada"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "realizada"


def test_cambiar_estado_sesion_cancelada(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.patch(
        f"/capacitaciones/sesiones/{sesion['id']}/estado",
        params={"estado": "cancelada"},
        headers=auth(sst),
    )
    assert resp.status_code == 200


# ── PATCH /capacitaciones/sesiones/{id} ───────────────────────────


def test_reprogramar_sesion(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    nueva_fecha = "2027-01-15T09:00:00"
    resp = client.patch(
        f"/capacitaciones/sesiones/{sesion['id']}",
        json={"fecha": nueva_fecha, "lugar": "Sala C"},
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert resp.json()["lugar"] == "Sala C"


# ── GET /capacitaciones/{id}/sesiones ─────────────────────────────


def test_listar_sesiones(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.get(f"/capacitaciones/{cap['id']}/sesiones", headers=auth(sst))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── POST /capacitaciones/asistencia ───────────────────────────────


def test_registrar_asistencia(client, db, empresa):
    sst = crear_usuario(db, empresa)
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.post(
        "/capacitaciones/asistencia",
        json={
            "sesion_id": sesion["id"],
            "empleado_id": str(empleado.id),
            "estado": "presente",
        },
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["estado"] == "presente"


# ── GET /capacitaciones/sesiones/{id}/asistencia ──────────────────


def test_asistencia_por_sesion(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.get(
        f"/capacitaciones/sesiones/{sesion['id']}/asistencia",
        headers=auth(sst),
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── GET /capacitaciones/empleados/{id}/historial ──────────────────


def test_historial_empleado_sst(client, db, empresa):
    sst = crear_usuario(db, empresa)
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.get(
        f"/capacitaciones/empleados/{empleado.id}/historial",
        headers=auth(sst),
    )
    assert resp.status_code == 200


def test_historial_empleado_propio(client, db, empresa):
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.get(
        f"/capacitaciones/empleados/{empleado.id}/historial",
        headers=auth(empleado),
    )
    assert resp.status_code == 200


def test_historial_empleado_otro_denegado(client, db, empresa):
    emp1 = crear_usuario(db, empresa, RoleEnum.empleado)
    emp2 = crear_usuario(db, empresa, RoleEnum.empleado)
    resp = client.get(
        f"/capacitaciones/empleados/{emp2.id}/historial",
        headers=auth(emp1),
    )
    assert resp.status_code == 403


# ── POST /capacitaciones/evaluaciones ────────────────────────────


def test_crear_evaluacion_ok(client, db, empresa):
    sst = crear_usuario(db, empresa)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])
    resp = client.post(
        "/capacitaciones/evaluaciones",
        json={
            "titulo": "Evaluación SST",
            "puntaje_minimo": 70,
            "sesion_id": sesion["id"],
            "preguntas": [
                {
                    "texto": "¿Color del casco?",
                    "opcion_a": "Rojo",
                    "opcion_b": "Azul",
                    "opcion_c": "Amarillo",
                    "opcion_d": "Verde",
                    "respuesta_correcta": "c",
                }
            ],
        },
        headers=auth(sst),
    )
    assert resp.status_code == 201
    assert resp.json()["titulo"] == "Evaluación SST"


# ── POST /capacitaciones/evaluaciones/responder ───────────────────


def test_responder_evaluacion_aprueba(client, db, empresa):
    sst = crear_usuario(db, empresa)
    empleado = crear_usuario(db, empresa, RoleEnum.empleado)
    cap = crear_capacitacion_via_api(client, auth(sst))
    sesion = crear_sesion_via_api(client, auth(sst), cap["id"])

    # Registrar asistencia del empleado
    client.post(
        "/capacitaciones/asistencia",
        json={
            "sesion_id": sesion["id"],
            "empleado_id": str(empleado.id),
            "estado": "presente",
        },
        headers=auth(sst),
    )

    # Crear evaluación
    ev_resp = client.post(
        "/capacitaciones/evaluaciones",
        json={
            "titulo": "Eval aprobación",
            "puntaje_minimo": 60,
            "sesion_id": sesion["id"],
            "preguntas": [
                {
                    "texto": "¿Qué es EPP?",
                    "opcion_a": "Equipo de Protección Personal",
                    "opcion_b": "Equipo de Primeros Pasos",
                    "opcion_c": "Error",
                    "opcion_d": "Nada",
                    "respuesta_correcta": "a",
                }
            ],
        },
        headers=auth(sst),
    )
    evaluacion_id = ev_resp.json()["id"]
    pregunta_id = ev_resp.json()["preguntas"][0]["id"]

    resp = client.post(
        "/capacitaciones/evaluaciones/responder",
        json={
            "evaluacion_id": evaluacion_id,
            "respuestas": [{"pregunta_id": pregunta_id, "respuesta_dada": "a"}],
        },
        headers=auth(empleado),
    )
    assert resp.status_code == 200
    assert resp.json()["aprobado"] is True
