# app/services/metricas_service.py
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.accion_correctiva import AccionCorrectiva, EstadoAccionEnum
from app.models.capacitacion import Capacitacion
from app.models.incidente import EstadoIncidenteEnum, Incidente, TipoIncidenteEnum
from app.models.user import RoleEnum, User


def get_kpis(db: Session, empresa_id: UUID):
    total_trabajadores = (
        db.query(User)
        .filter(
            User.empresa_id == empresa_id,
            User.activo == True,
            User.role == RoleEnum.empleado,
        )
        .count()
    )

    inicio_anio = datetime(datetime.now(timezone.utc).replace(tzinfo=None).year, 1, 1)
    total_accidentes = (
        db.query(Incidente)
        .filter(
            Incidente.empresa_id == empresa_id,
            Incidente.tipo == TipoIncidenteEnum.accidente,
            Incidente.fecha >= inicio_anio,
        )
        .count()
    )

    from app.models.lesion import Lesion

    dias_perdidos_result = (
        db.query(func.sum(Lesion.incapacidad_dias))
        .join(Incidente, Lesion.incidente_id == Incidente.id)
        .filter(Incidente.empresa_id == empresa_id, Incidente.fecha >= inicio_anio)
        .scalar()
    )
    dias_perdidos = dias_perdidos_result or 0

    dias_transcurridos = (
        datetime.now(timezone.utc).replace(tzinfo=None) - inicio_anio
    ).days

    # ✅ Fix Bug #5 — División por cero el 1 de enero
    horas_trabajadas = total_trabajadores * 8 * dias_transcurridos
    horas_trabajadas = horas_trabajadas if horas_trabajadas > 0 else 1

    tasa_accidentalidad = (
        round((total_accidentes / total_trabajadores) * 100, 2)
        if total_trabajadores > 0
        else 0
    )
    indice_frecuencia = (
        round((total_accidentes / horas_trabajadas) * 1000000, 2)
        if horas_trabajadas > 0
        else 0
    )
    indice_severidad = (
        round((dias_perdidos / horas_trabajadas) * 1000000, 2)
        if horas_trabajadas > 0
        else 0
    )

    return {
        "total_trabajadores": total_trabajadores,
        "total_accidentes": total_accidentes,
        "dias_perdidos": dias_perdidos,
        "tasa_accidentalidad": tasa_accidentalidad,
        "indice_frecuencia": indice_frecuencia,
        "indice_severidad": indice_severidad,
    }


def get_dashboard_gerencia(db: Session, empresa_id: UUID):
    kpis = get_kpis(db, empresa_id)

    incidentes_activos = (
        db.query(Incidente)
        .filter(
            Incidente.empresa_id == empresa_id,
            Incidente.estado != EstadoIncidenteEnum.cerrado,
        )
        .count()
    )

    hace_un_mes = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    incidentes_ultimo_mes = (
        db.query(Incidente)
        .filter(
            Incidente.empresa_id == empresa_id, Incidente.fecha_creacion >= hace_un_mes
        )
        .count()
    )

    total_capacitaciones = (
        db.query(Capacitacion)
        .filter(Capacitacion.empresa_id == empresa_id, Capacitacion.activo == True)
        .count()
    )

    acciones_vencidas = (
        db.query(AccionCorrectiva)
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != EstadoAccionEnum.completada,
            AccionCorrectiva.fecha_limite
            < datetime.now(timezone.utc).replace(tzinfo=None),
        )
        .count()
    )

    total_acciones = (
        db.query(AccionCorrectiva)
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)
        .filter(Incidente.empresa_id == empresa_id)
        .count()
    )

    acciones_completadas = (
        db.query(AccionCorrectiva)
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado == EstadoAccionEnum.completada,
        )
        .count()
    )

    cumplimiento = (
        round((acciones_completadas / total_acciones) * 100)
        if total_acciones > 0
        else 100
    )

    return {
        "cumplimiento_sgsst": cumplimiento,
        "incidentes_activos": incidentes_activos,
        "incidentes_ultimo_mes": incidentes_ultimo_mes,
        "total_capacitaciones": total_capacitaciones,
        "acciones_vencidas": acciones_vencidas,
        "kpis": kpis,
    }


def get_alertas(db: Session, empresa_id: UUID):
    alertas = []

    sin_investigacion = (
        db.query(Incidente)
        .filter(
            Incidente.empresa_id == empresa_id,
            Incidente.estado == EstadoIncidenteEnum.abierto,
            ~Incidente.investigacion.has(),
        )
        .count()
    )

    if sin_investigacion > 0:
        alertas.append(
            {
                "tipo": "incidente_sin_investigacion",
                "nivel": "critico",
                "mensaje": f"{sin_investigacion} incidente(s) abiertos sin investigación documentada",
                "url_destino": "/incidentes?estado=abierto",
            }
        )

    acciones_vencidas = (
        db.query(AccionCorrectiva)
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != EstadoAccionEnum.completada,
            AccionCorrectiva.fecha_limite
            < datetime.now(timezone.utc).replace(tzinfo=None),
        )
        .count()
    )

    if acciones_vencidas > 0:
        alertas.append(
            {
                "tipo": "accion_correctiva_vencida",
                "nivel": "critico",
                "mensaje": f"{acciones_vencidas} acción(es) correctiva(s) vencida(s)",
                "url_destino": "/acciones-correctivas",
            }
        )

    proxima_semana = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    acciones_proximas = (
        db.query(AccionCorrectiva)
        .join(Incidente, AccionCorrectiva.incidente_id == Incidente.id)
        .filter(
            Incidente.empresa_id == empresa_id,
            AccionCorrectiva.estado != EstadoAccionEnum.completada,
            AccionCorrectiva.fecha_limite
            >= datetime.now(timezone.utc).replace(tzinfo=None),
            AccionCorrectiva.fecha_limite <= proxima_semana,
        )
        .count()
    )

    if acciones_proximas > 0:
        alertas.append(
            {
                "tipo": "accion_correctiva_proxima",
                "nivel": "medio",
                "mensaje": f"{acciones_proximas} acción(es) correctiva(s) vence(n) en los próximos 7 días",
                "url_destino": "/acciones-correctivas",
            }
        )

    return {"total_alertas": len(alertas), "alertas": alertas}


# ── Reportes ejecutivos ───────────────────────────────────────────


def generar_reporte_pdf(db: Session, empresa_id: UUID, periodo: str):
    from io import BytesIO

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    dashboard = get_dashboard_gerencia(db, empresa_id)
    kpis = dashboard["kpis"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()

    def est(nombre, size, color, bold=False, align=TA_CENTER, after=10):
        return ParagraphStyle(
            nombre,
            parent=styles["Normal"],
            fontSize=size,
            textColor=colors.HexColor(color),
            alignment=align,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            spaceAfter=after,
        )

    fecha_actual = datetime.now(timezone.utc).replace(tzinfo=None).strftime("%d/%m/%Y")

    contenido = [
        Spacer(1, 0.2 * inch),
        Paragraph("PISST", est("t1", 28, "#1E3A5F", bold=True, after=4)),
        Paragraph(
            "Plataforma Integral de Seguridad y Salud en el Trabajo",
            est("t2", 11, "#666666", after=4),
        ),
        Paragraph(
            f"Reporte Ejecutivo — Período: {periodo.capitalize()}",
            est("t3", 13, "#1d4ed8", bold=True, after=4),
        ),
        Paragraph(f"Generado el: {fecha_actual}", est("t4", 10, "#999999", after=16)),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee")),
        Spacer(1, 0.3 * inch),
        Paragraph("KPIs de Seguridad", est("t5", 14, "#1E3A5F", bold=True, after=12)),
    ]

    data_kpis = [
        ["Indicador", "Valor"],
        ["Total Trabajadores", str(kpis["total_trabajadores"])],
        ["Total Accidentes", str(kpis["total_accidentes"])],
        ["Días Perdidos", str(kpis["dias_perdidos"])],
        ["Tasa de Accidentalidad", f"{kpis['tasa_accidentalidad']}%"],
        ["Índice de Frecuencia", str(kpis["indice_frecuencia"])],
        ["Índice de Severidad", str(kpis["indice_severidad"])],
    ]

    tabla_kpis = Table(data_kpis, colWidths=[3.5 * inch, 2.5 * inch])
    tabla_kpis.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#F1EFE8"), colors.white],
                ),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    contenido.append(tabla_kpis)
    contenido.append(Spacer(1, 0.3 * inch))
    contenido.append(
        Paragraph("Resumen Ejecutivo", est("t6", 14, "#1E3A5F", bold=True, after=12))
    )

    data_resumen = [
        ["Métrica", "Valor"],
        ["Cumplimiento SG-SST", f"{dashboard['cumplimiento_sgsst']}%"],
        ["Incidentes Activos", str(dashboard["incidentes_activos"])],
        ["Incidentes Último Mes", str(dashboard["incidentes_ultimo_mes"])],
        ["Capacitaciones Activas", str(dashboard["total_capacitaciones"])],
        ["Acciones Correctivas Vencidas", str(dashboard["acciones_vencidas"])],
    ]

    tabla_resumen = Table(data_resumen, colWidths=[3.5 * inch, 2.5 * inch])
    tabla_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#F1EFE8"), colors.white],
                ),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    contenido.append(tabla_resumen)
    contenido.append(Spacer(1, 0.4 * inch))
    contenido.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#eeeeee"))
    )
    contenido.append(Spacer(1, 0.2 * inch))
    contenido.append(
        Paragraph(
            "PISST — Reporte generado automáticamente por el sistema.",
            est("t7", 9, "#999999", after=0),
        )
    )

    doc.build(contenido)
    buffer.seek(0)
    return buffer


def generar_reporte_excel(db: Session, empresa_id: UUID, periodo: str):
    from io import BytesIO

    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    dashboard = get_dashboard_gerencia(db, empresa_id)
    kpis = dashboard["kpis"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Reporte PISST"

    azul_navy = "1E3A5F"
    azul_btn = "1d4ed8"

    header_font = Font(name="Calibri", bold=True, color="FFFFFF", size=12)
    title_font = Font(name="Calibri", bold=True, color=azul_navy, size=16)
    sub_font = Font(name="Calibri", bold=True, color=azul_btn, size=11)
    normal_font = Font(name="Calibri", size=10)

    fill_navy = PatternFill("solid", fgColor=azul_navy)
    fill_azul = PatternFill("solid", fgColor=azul_btn)
    fill_gris = PatternFill("solid", fgColor="F1EFE8")
    fill_blanco = PatternFill("solid", fgColor="FFFFFF")

    center = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws.merge_cells("A1:C1")
    ws["A1"] = "PISST — Reporte Ejecutivo"
    ws["A1"].font = title_font
    ws["A1"].alignment = center

    ws.merge_cells("A2:C2")
    ws["A2"] = (
        f"Período: {periodo.capitalize()} | Generado: {datetime.now(timezone.utc).replace(tzinfo=None).strftime('%d/%m/%Y')}"
    )
    ws["A2"].font = Font(name="Calibri", color="666666", size=10)
    ws["A2"].alignment = center

    ws.append([])

    ws.append(["KPIs de Seguridad", "", ""])
    ws[f"A{ws.max_row}"].font = sub_font

    ws.append(["Indicador", "Valor", ""])
    for col in range(1, 3):
        cell = ws.cell(row=ws.max_row, column=col)
        cell.fill = fill_navy
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    kpi_rows = [
        ("Total Trabajadores", kpis["total_trabajadores"]),
        ("Total Accidentes", kpis["total_accidentes"]),
        ("Días Perdidos", kpis["dias_perdidos"]),
        ("Tasa de Accidentalidad", f"{kpis['tasa_accidentalidad']}%"),
        ("Índice de Frecuencia", kpis["indice_frecuencia"]),
        ("Índice de Severidad", kpis["indice_severidad"]),
    ]

    for i, (indicador, valor) in enumerate(kpi_rows):
        ws.append([indicador, valor, ""])
        fill = fill_gris if i % 2 == 0 else fill_blanco
        for col in range(1, 3):
            cell = ws.cell(row=ws.max_row, column=col)
            cell.fill = fill
            cell.font = normal_font
            cell.alignment = center
            cell.border = border

    ws.append([])

    ws.append(["Resumen Ejecutivo", "", ""])
    ws[f"A{ws.max_row}"].font = sub_font

    ws.append(["Métrica", "Valor", ""])
    for col in range(1, 3):
        cell = ws.cell(row=ws.max_row, column=col)
        cell.fill = fill_azul
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    resumen_rows = [
        ("Cumplimiento SG-SST", f"{dashboard['cumplimiento_sgsst']}%"),
        ("Incidentes Activos", dashboard["incidentes_activos"]),
        ("Incidentes Último Mes", dashboard["incidentes_ultimo_mes"]),
        ("Capacitaciones Activas", dashboard["total_capacitaciones"]),
        ("Acciones Vencidas", dashboard["acciones_vencidas"]),
    ]

    for i, (metrica, valor) in enumerate(resumen_rows):
        ws.append([metrica, valor, ""])
        fill = fill_gris if i % 2 == 0 else fill_blanco
        for col in range(1, 3):
            cell = ws.cell(row=ws.max_row, column=col)
            cell.fill = fill
            cell.font = normal_font
            cell.alignment = center
            cell.border = border

    ws.column_dimensions["A"].width = 35
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 5
    ws.row_dimensions[1].height = 30

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
