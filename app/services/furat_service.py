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


def _safe(value, max_len: int = 500) -> str:
    """Elimina caracteres de control y trunca cadenas largas para evitar problemas en el PDF."""
    s = str(value) if value is not None else ""
    s = "".join(c for c in s if c >= " " or c in "\n\r\t")
    return s[:max_len]


def _nr(value, max_len: int = 500) -> str:
    """Retorna el valor como string sanitizado, o 'No registrado' si es None/vacío."""
    s = _safe(value, max_len).strip()
    return s if s else "No registrado"


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
    Genera el formulario FURAT en PDF con diseño profesional.
    Retorna los bytes del PDF para ser descargado.
    """
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.lib.units import inch

    d = _obtener_datos_furat(db, incidente_id, empresa_id)

    # ── Paleta ────────────────────────────────────────────────────
    NAVY = colors.HexColor("#1B3A5C")
    ACCENT = colors.HexColor("#0EA5E9")
    WHITE = colors.white
    LABEL_BG = colors.HexColor("#EEF2FF")
    ROW_ALT = colors.HexColor("#F8FAFC")
    BORDER = colors.HexColor("#CBD5E1")
    MUTED = colors.HexColor("#64748B")
    SEC_BG = colors.HexColor("#1E3A5C")
    W, H = letter

    fecha_reporte = d["fecha_reporte"]
    inc_id_short = d["incidente_id"][:16]

    # ── Callbacks header/footer ───────────────────────────────────
    def header_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()

        # Banda superior
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, H - 68, W, 68, fill=True, stroke=False)
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(0, H - 72, W, 4, fill=True, stroke=False)

        # Franja roja decorativa (bandera Colombia)
        canvas_obj.setFillColor(colors.HexColor("#C0392B"))
        canvas_obj.rect(0, H - 68, 6, 68, fill=True, stroke=False)
        canvas_obj.setFillColor(colors.HexColor("#F1C40F"))
        canvas_obj.rect(6, H - 68, 6, 68, fill=True, stroke=False)

        # Texto principal en banda
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawString(
            22, H - 26, "FORMULARIO ÚNICO DE REPORTE DE ACCIDENTE DE TRABAJO"
        )
        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(colors.HexColor("#A0C4E8"))
        canvas_obj.drawString(
            22, H - 42, "FURAT  —  Resolución 0156 de 2005  —  República de Colombia"
        )
        canvas_obj.setFillColor(colors.HexColor("#CBD5E1"))
        canvas_obj.drawString(
            22, H - 57, "Sistema de Gestión de Seguridad y Salud en el Trabajo — SG-SST"
        )

        # Fecha arriba derecha
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(colors.HexColor("#CBD5E1"))
        canvas_obj.drawRightString(W - 14, H - 26, f"Fecha: {fecha_reporte}")
        canvas_obj.drawRightString(W - 14, H - 40, f"ID: {inc_id_short}...")

        # Footer
        canvas_obj.setFillColor(ROW_ALT)
        canvas_obj.rect(0, 0, W, 28, fill=True, stroke=False)
        canvas_obj.setFillColor(BORDER)
        canvas_obj.rect(0, 28, W, 0.5, fill=True, stroke=False)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.setFillColor(MUTED)
        canvas_obj.drawString(
            14,
            10,
            "Documento generado por PISST — Plataforma Integral de Seguridad y Salud en el Trabajo",
        )
        canvas_obj.drawRightString(W - 14, 10, f"Página {doc_obj.page}")

        canvas_obj.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=1.05 * inch,
        bottomMargin=0.55 * inch,
    )

    styles = getSampleStyleSheet()

    def p(texto, size=8, bold=False, color=None, align=TA_LEFT, after=0):
        return Paragraph(
            texto,
            ParagraphStyle(
                "px",
                parent=styles["Normal"],
                fontSize=size,
                textColor=color or colors.HexColor("#1E293B"),
                fontName="Helvetica-Bold" if bold else "Helvetica",
                alignment=align,
                spaceAfter=after,
                leading=size * 1.35,
            ),
        )

    W_total = W - 1.1 * inch
    L1, L2, L3, L4 = W_total * 0.18, W_total * 0.32, W_total * 0.18, W_total * 0.32

    def lbl(txt):
        return p(txt, size=7.5, bold=True, color=colors.HexColor("#1E3A5C"))

    def val(txt):
        return p(_safe(txt, 300), size=8)

    def sec_header(num, titulo):
        """Fila de encabezado de sección que abarca todo el ancho."""
        texto = p(f"  SECCIÓN {num} — {titulo}", size=8.5, bold=True, color=WHITE)
        t = Table([[texto]], colWidths=[W_total])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SEC_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    def tabla4(filas, spans=None):
        """Tabla de 4 columnas con etiquetas y valores."""
        t = Table(filas, colWidths=[L1, L2, L3, L4])
        style_cmds = [
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, ROW_ALT]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for col in (0, 2):
            style_cmds.append(("BACKGROUND", (col, 0), (col, -1), LABEL_BG))
        if spans:
            style_cmds.extend(spans)
        t.setStyle(TableStyle(style_cmds))
        return t

    def tabla2(filas):
        """Tabla de 2 columnas para investigación."""
        L_lbl = W_total * 0.22
        L_val = W_total * 0.78
        t = Table(filas, colWidths=[L_lbl, L_val])
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, ROW_ALT]),
                    ("BACKGROUND", (0, 0), (0, -1), LABEL_BG),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return t

    def sp(n=0.2):
        return Spacer(1, n * cm)

    # ── Contenido ─────────────────────────────────────────────────
    elementos = []

    # ── S1: Empresa ───────────────────────────────────────────────
    elementos.append(sec_header(1, "DATOS DE LA EMPRESA"))
    elementos.append(
        tabla4(
            [
                [
                    lbl("Razón Social"),
                    val(d["razon_social"]),
                    lbl("Fecha del reporte"),
                    val(d["fecha_reporte"]),
                ],
                [lbl("NIT"), val(d["nit"]), lbl("Ciudad"), val(d["ciudad"])],
                [
                    lbl("Dirección"),
                    val(d["direccion"]),
                    lbl("Teléfono"),
                    val(d["telefono_empresa"]),
                ],
                [lbl("Sector / Actividad"), val(d["sector"]), p(""), p("")],
            ],
            spans=[("SPAN", (1, 3), (3, 3))],
        )
    )
    elementos.append(sp(0.35))

    # ── S2: Trabajador ────────────────────────────────────────────
    elementos.append(sec_header(2, "DATOS DEL TRABAJADOR ACCIDENTADO"))
    elementos.append(
        tabla4(
            [
                [
                    lbl("Nombre completo"),
                    val(d["nombre_trabajador"]),
                    lbl("Cargo"),
                    val(d["cargo_trabajador"]),
                ],
                [
                    lbl("Área"),
                    val(d["area_trabajador"]),
                    lbl("Tipo vinculación"),
                    val(d["tipo_vinculacion"]),
                ],
                [lbl("Teléfono"), val(d["telefono_trabajador"]), p(""), p("")],
            ],
            spans=[("SPAN", (1, 2), (3, 2))],
        )
    )
    elementos.append(sp(0.35))

    # ── S3: Accidente ─────────────────────────────────────────────
    elementos.append(sec_header(3, "DATOS DEL ACCIDENTE"))
    elementos.append(
        tabla4(
            [
                [
                    lbl("Fecha del accidente"),
                    val(d["fecha_accidente"]),
                    lbl("Lugar"),
                    val(d["lugar"]),
                ],
                [
                    lbl("Tipo de evento"),
                    val(d["tipo"]),
                    lbl("Severidad"),
                    val(d["severidad"]),
                ],
                [lbl("Testigos"), val(d["testigos"]), p(""), p("")],
                [lbl("Descripción"), val(d["descripcion"]), p(""), p("")],
            ],
            spans=[
                ("SPAN", (1, 2), (3, 2)),
                ("SPAN", (1, 3), (3, 3)),
            ],
        )
    )
    elementos.append(sp(0.35))

    # ── S4: Lesión ────────────────────────────────────────────────
    elementos.append(sec_header(4, "DATOS DE LA LESIÓN"))
    elementos.append(
        tabla4(
            [
                [
                    lbl("Tipo de lesión"),
                    val(d["tipo_lesion"]),
                    lbl("Parte afectada"),
                    val(d["parte_afectada"]),
                ],
                [lbl("Días de incapacidad"), val(d["incapacidad_dias"]), p(""), p("")],
            ],
            spans=[("SPAN", (1, 1), (3, 1))],
        )
    )
    elementos.append(sp(0.35))

    # ── S5: Investigación ─────────────────────────────────────────
    elementos.append(sec_header(5, "INVESTIGACIÓN DE CAUSAS"))
    elementos.append(
        tabla2(
            [
                [lbl("Causas inmediatas"), val(d["causas_inmediatas"])],
                [lbl("Causas básicas"), val(d["causas_basicas"])],
                [lbl("Factores contribuyentes"), val(d["factores_contribuyentes"])],
                [lbl("Lecciones aprendidas"), val(d["lecciones_aprendidas"])],
            ]
        )
    )
    elementos.append(sp(0.35))

    # ── S6: Firmas ────────────────────────────────────────────────
    elementos.append(sec_header(6, "FIRMAS Y APROBACIÓN"))
    L_half = W_total / 2
    firmas = Table(
        [
            [
                p(
                    "Firma Trabajador",
                    size=8,
                    bold=True,
                    color=colors.HexColor("#1E3A5C"),
                    align=TA_CENTER,
                ),
                p(
                    "Firma Encargado SST",
                    size=8,
                    bold=True,
                    color=colors.HexColor("#1E3A5C"),
                    align=TA_CENTER,
                ),
            ],
            [p(""), p("")],
            [p(""), p("")],
            [
                p(
                    "_______________________________",
                    size=9,
                    align=TA_CENTER,
                    color=MUTED,
                ),
                p(
                    "_______________________________",
                    size=9,
                    align=TA_CENTER,
                    color=MUTED,
                ),
            ],
            [
                p(
                    "Nombre: " + d["nombre_trabajador"],
                    size=7.5,
                    align=TA_CENTER,
                    color=MUTED,
                ),
                p(
                    "Nombre: ____________________",
                    size=7.5,
                    align=TA_CENTER,
                    color=MUTED,
                ),
            ],
            [
                p("Fecha: __________________", size=7.5, align=TA_CENTER, color=MUTED),
                p("Fecha: __________________", size=7.5, align=TA_CENTER, color=MUTED),
            ],
        ],
        colWidths=[L_half, L_half],
        rowHeights=[None, 10, 10, None, None, None],
    )
    firmas.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, BORDER),
                ("LINEAFTER", (0, 0), (0, -1), 0.4, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), LABEL_BG),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elementos.append(firmas)

    doc.build(elementos, onFirstPage=header_footer, onLaterPages=header_footer)
    buffer.seek(0)
    return buffer.getvalue()
