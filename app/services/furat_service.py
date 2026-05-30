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


def generar_furat(db: Session, incidente_id: UUID, empresa_id: UUID) -> bytes:
    """
    Genera el formulario FURAT en PDF.
    Retorna los bytes del PDF para ser descargado.
    """
    # Obtener el incidente con toda su información
    incidente = get_incidente_by_id(db, incidente_id, empresa_id)

    # Crear el buffer en memoria
    buffer = io.BytesIO()

    # Crear el documento PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    # Estilos
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontSize=12,
        alignment=1,  # centrado
        spaceAfter=6,
    )
    style_subtitle = ParagraphStyle(
        "subtitle", parent=styles["Normal"], fontSize=9, alignment=1, spaceAfter=4
    )
    style_normal = ParagraphStyle(
        "normal", parent=styles["Normal"], fontSize=8, spaceAfter=2
    )

    # Contenido del PDF
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

    # Después
    empresa = db.query(Empresa).filter(Empresa.id == incidente.empresa_id).first()
    razon_social = empresa.nombre if empresa else "N/A"
    nit = empresa.nit if empresa else "N/A"

    datos_empresa = [
        [
            "Razón Social",
            razon_social,
            "Fecha del reporte",
            datetime.now(timezone.utc).replace(tzinfo=None).strftime("%d/%m/%Y"),
        ],
        ["NIT", nit, "Ciudad", "N/A"],
    ]

    tabla_empresa = Table(datos_empresa, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm])
    tabla_empresa.setStyle(
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
    elementos.append(tabla_empresa)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 2: Datos del trabajador ──────────────────────────
    elementos.append(
        Paragraph("<b>SECCIÓN 2 — DATOS DEL TRABAJADOR ACCIDENTADO</b>", style_normal)
    )

    trabajador = incidente.trabajador_afectado
    nombre_trabajador = trabajador.nombre if trabajador else "No especificado"
    cargo_trabajador = (
        trabajador.cargo.nombre
        if trabajador and trabajador.cargo
        else "No especificado"
    )
    area_trabajador = (
        trabajador.area.nombre if trabajador and trabajador.area else "No especificado"
    )

    datos_trabajador = [
        ["Nombre completo", nombre_trabajador, "Cargo", cargo_trabajador],
        ["Área", area_trabajador, "Tipo vinculación", "Empleado"],
    ]

    tabla_trabajador = Table(
        datos_trabajador, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm]
    )
    tabla_trabajador.setStyle(
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
    elementos.append(tabla_trabajador)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 3: Datos del accidente ────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 3 — DATOS DEL ACCIDENTE</b>", style_normal))

    datos_accidente = [
        [
            "Fecha del accidente",
            incidente.fecha.strftime("%d/%m/%Y %H:%M") if incidente.fecha else "N/A",
            "Lugar",
            incidente.lugar,
        ],
        [
            "Tipo de evento",
            incidente.tipo.value,
            "Severidad",
            incidente.severidad.value,
        ],
        ["Descripción", incidente.descripcion, "", ""],
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
                ("SPAN", (1, 2), (3, 2)),  # descripción ocupa todo el ancho
            ]
        )
    )
    elementos.append(tabla_accidente)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 4: Lesión ─────────────────────────────────────────
    elementos.append(Paragraph("<b>SECCIÓN 4 — DATOS DE LA LESIÓN</b>", style_normal))

    lesion = incidente.lesion
    datos_lesion = [
        [
            "Tipo de lesión",
            lesion.tipo_lesion if lesion else "Sin lesión",
            "Parte afectada",
            lesion.parte_afectada if lesion else "N/A",
        ],
        [
            "Días de incapacidad",
            str(lesion.incapacidad_dias) if lesion else "0",
            "",
            "",
        ],
    ]

    tabla_lesion = Table(datos_lesion, colWidths=[3.5 * cm, 6 * cm, 3.5 * cm, 6 * cm])
    tabla_lesion.setStyle(
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
    elementos.append(tabla_lesion)
    elementos.append(Spacer(1, 0.3 * cm))

    # ── Sección 5: Investigación ──────────────────────────────────
    elementos.append(
        Paragraph("<b>SECCIÓN 5 — INVESTIGACIÓN DE CAUSAS</b>", style_normal)
    )

    investigacion = incidente.investigacion
    datos_inv = [
        [
            "Causas inmediatas",
            (
                investigacion.causas_inmediatas
                if investigacion
                else "Pendiente de investigación"
            ),
        ],
        [
            "Causas básicas",
            (
                investigacion.causas_basicas
                if investigacion
                else "Pendiente de investigación"
            ),
        ],
        [
            "Factores contribuyentes",
            investigacion.factores_contribuyentes if investigacion else "N/A",
        ],
        [
            "Lecciones aprendidas",
            investigacion.lecciones_aprendidas if investigacion else "N/A",
        ],
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
            f"Documento generado por PISST — {datetime.now(timezone.utc).replace(tzinfo=None).strftime('%d/%m/%Y %H:%M')} — ID: {incidente_id}",
            style_subtitle,
        )
    )

    # Construir el PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
