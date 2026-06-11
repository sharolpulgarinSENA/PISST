# app/services/furat_service.py
import io
from datetime import datetime, timezone
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.services.incidente_service import get_incidente_by_id


def _nr(value) -> str:
    """Retorna el valor como string, o 'No registrado' si es None/vacío."""
    if value is None or str(value).strip() == "":
        return "No registrado"
    return str(value).strip()


def _obtener_datos_furat(db: Session, incidente_id: UUID, empresa_id: UUID) -> dict:
    """
    Extrae y normaliza todos los datos necesarios para generar el FURAT.
    Retorna un dict con claves tipadas — útil para tests sin parsear el PDF.
    """
    incidente = get_incidente_by_id(db, incidente_id, empresa_id)
    empresa = db.query(Empresa).filter(Empresa.id == incidente.empresa_id).first()
    trabajador = incidente.trabajador_afectado
    lesion = incidente.lesion
    investigacion = incidente.investigacion

    # ── Empresa ──────────────────────────────────────────────────────
    datos = {
        "razon_social": _nr(empresa.nombre if empresa else None),
        "nit": _nr(empresa.nit if empresa else None),
        "ciudad": _nr(empresa.ciudad if empresa else None),
        "direccion": _nr(empresa.direccion if empresa else None),
        "telefono_empresa": _nr(empresa.telefono if empresa else None),
        "sector": _nr(empresa.sector if empresa else None),
        # ── Trabajador ────────────────────────────────────────────────
        "nombre_trabajador": _nr(trabajador.nombre if trabajador else None),
        "cargo_trabajador": _nr(
            trabajador.cargo.nombre if trabajador and trabajador.cargo else None
        ),
        "area_trabajador": _nr(
            trabajador.area.nombre if trabajador and trabajador.area else None
        ),
        "tipo_vinculacion": _nr(trabajador.tipo_vinculacion if trabajador else None),
        "telefono_trabajador": _nr(trabajador.telefono if trabajador else None),
        # ── Accidente ─────────────────────────────────────────────────
        "fecha_accidente": (
            incidente.fecha.strftime("%d/%m/%Y %H:%M")
            if incidente.fecha
            else "No registrado"
        ),
        "lugar": _nr(incidente.lugar),
        "tipo": incidente.tipo.value,
        "severidad": incidente.severidad.value,
        "descripcion": _nr(incidente.descripcion),
        "testigos": (
            ", ".join(t.nombre for t in incidente.testigos)
            if incidente.testigos
            else "Sin testigos registrados"
        ),
        # ── Lesión ────────────────────────────────────────────────────
        "tipo_lesion": _nr(lesion.tipo_lesion if lesion else None),
        "parte_afectada": _nr(lesion.parte_afectada if lesion else None),
        "incapacidad_dias": str(lesion.incapacidad_dias) if lesion else "0",
        # ── Investigación ─────────────────────────────────────────────
        "causas_inmediatas": (
            _nr(investigacion.causas_inmediatas)
            if investigacion
            else "Pendiente de investigación"
        ),
        "causas_basicas": (
            _nr(investigacion.causas_basicas)
            if investigacion
            else "Pendiente de investigación"
        ),
        "factores_contribuyentes": (
            _nr(investigacion.factores_contribuyentes)
            if investigacion
            else "Pendiente de investigación"
        ),
        "lecciones_aprendidas": (
            _nr(investigacion.lecciones_aprendidas)
            if investigacion
            else "Pendiente de investigación"
        ),
        # ── Metadatos ─────────────────────────────────────────────────
        "fecha_reporte": datetime.now(timezone.utc)
        .replace(tzinfo=None)
        .strftime("%d/%m/%Y"),
        "incidente_id": str(incidente_id),
    }
    return datos


def generar_furat(db: Session, incidente_id: UUID, empresa_id: UUID) -> bytes:
    """
    Genera el formulario FURAT en PDF.
    Retorna los bytes del PDF para ser descargado.
    """
    d = _obtener_datos_furat(db, incidente_id, empresa_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=12,
        alignment=1,
        spaceAfter=6,
    )
    style_subtitle = ParagraphStyle(
        "subtitle", parent=styles["Normal"], fontSize=9, alignment=1, spaceAfter=4
    )
    style_normal = ParagraphStyle(
        "normal", parent=styles["Normal"], fontSize=8, spaceAfter=2
    )

    elementos = []

    # ── Encabezado ────────────────────────────────────────────────
    elementos.append(
        Paragraph("FORMULARIO ÚNICO DE REPORTE DE ACCIDENTE DE TRABAJO", style_title)
    )
    elementos.append(
        Paragraph(
            "FURAT — Resolución 0156 de 2005 — República de Colombia", style_subtitle
        )
    )
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 1: Datos de la empresa ────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 1 — DATOS DE LA EMPRESA</b>", style_normal))

    datos_empresa = [
        [
            "Razón Social",
            d["razon_social"],
            "Fecha del reporte",
            d["fecha_reporte"],
        ],
        ["NIT", d["nit"], "Ciudad", d["ciudad"]],
        ["Dirección", d["direccion"], "Teléfono", d["telefono_empresa"]],
        ["Sector / Actividad", d["sector"], "", ""],
    ]

    tabla_empresa = Table(datos_empresa, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm])
    tabla_empresa.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("BACKGROUND", (2, 0), (2, -2), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_empresa)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 2: Datos del trabajador ──────────────────────────
    elementos.append(
        Paragraph("<b>SECCIÓN 2 — DATOS DEL TRABAJADOR ACCIDENTADO</b>", style_normal)
    )

    datos_trabajador = [
        ["Nombre completo", d["nombre_trabajador"], "Cargo", d["cargo_trabajador"]],
        ["Área", d["area_trabajador"], "Tipo vinculación", d["tipo_vinculacion"]],
        ["Teléfono", d["telefono_trabajador"], "", ""],
    ]

    tabla_trabajador = Table(
        datos_trabajador, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm]
    )
    tabla_trabajador.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("BACKGROUND", (2, 0), (2, -2), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_trabajador)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 3: Datos del accidente ────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 3 — DATOS DEL ACCIDENTE</b>", style_normal))

    datos_accidente = [
        [
            "Fecha del accidente",
            d["fecha_accidente"],
            "Lugar",
            d["lugar"],
        ],
        ["Tipo de evento", d["tipo"], "Severidad", d["severidad"]],
        ["Testigos", d["testigos"], "", ""],
        ["Descripción", d["descripcion"], "", ""],
    ]

    tabla_accidente = Table(
        datos_accidente, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm]
    )
    tabla_accidente.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("BACKGROUND", (2, 0), (2, 1), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
                ("SPAN", (1, 2), (3, 2)),
                ("SPAN", (1, 3), (3, 3)),
            ]
        )
    )
    elementos.append(tabla_accidente)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 4: Lesión ─────────────────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 4 — DATOS DE LA LESIÓN</b>", style_normal))

    datos_lesion = [
        [
            "Tipo de lesión",
            d["tipo_lesion"],
            "Parte afectada",
            d["parte_afectada"],
        ],
        ["Días de incapacidad", d["incapacidad_dias"], "", ""],
    ]

    tabla_lesion = Table(datos_lesion, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm])
    tabla_lesion.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("BACKGROUND", (2, 0), (2, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_lesion)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 5: Investigación ──────────────────────────────────
    elementos.append(
        Paragraph("<b>SECCIÓN 5 — INVESTIGACIÓN DE CAUSAS</b>", style_normal)
    )

    datos_inv = [
        ["Causas inmediatas", d["causas_inmediatas"]],
        ["Causas básicas", d["causas_basicas"]],
        ["Factores contribuyentes", d["factores_contribuyentes"]],
        ["Lecciones aprendidas", d["lecciones_aprendidas"]],
    ]

    tabla_inv = Table(datos_inv, colWidths=[4 * cm, 15 * cm])
    tabla_inv.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_inv)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 6: Firmas ─────────────────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 6 — FIRMAS</b>", style_normal))

    datos_firmas = [
        ["Firma Trabajador", "", "Firma Encargado SST", ""],
        ["Nombre:", "___________________", "Nombre:", "___________________"],
        ["Fecha:", "___________________", "Fecha:", "___________________"],
    ]

    tabla_firmas = Table(datos_firmas, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm])
    tabla_firmas.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
                ("BACKGROUND", (2, 0), (2, -1), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elementos.append(tabla_firmas)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Pie de página ─────────────────────────────────────────────
    elementos.append(
        Paragraph(
            f"Documento generado por PISST — {d['fecha_reporte']} — ID: {d['incidente_id']}",
            style_subtitle,
        )
    )

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
