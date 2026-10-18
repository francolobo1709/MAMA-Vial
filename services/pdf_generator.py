"""Servicio de generación de reportes y certificados de ensayo de laboratorio vial en PDF.

Utiliza ReportLab para emitir certificados oficiales con formato DNV/IRAM listos para firma.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class LabPdfReportService:
    """Genera certificados técnicos en PDF para ensayos Marshall y volumetría asfáltica."""

    @classmethod
    def generate_marshall_certificate(
        cls,
        summary_data: Dict[str, Any],
        output_path: str = "Certificado_Marshall_Franco.pdf",
        operator_name: str = "Franco",
        operator_title: str = "Analista de Estructuras Viales y de Transporte MP: 2205",
    ) -> str:
        """Crea un documento PDF formateado con encabezados técnicos y tablas de resultados."""
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,  # Centrado
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=10,
            spaceAfter=6,
        )
        normal_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748"),
        )
        bold_style = ParagraphStyle(
            "BodyBold",
            parent=normal_style,
            fontName="Helvetica-Bold",
        )

        story = []

        # Encabezado
        story.append(Paragraph("CONTROL DE CALIDAD VIAL - LABORATORIO DE ASFALTOS", title_style))
        story.append(Paragraph("Certificado de Ensayo Volumétrico Marshall (Normas DNV VN-E5-93 / IRAM 1534)", subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3182CE"), spaceAfter=10))

        # Metadatos del ensayo
        fecha_str = datetime.now().strftime("%d/%m/%Y - %H:%M")
        meta_table_data = [
            [
                Paragraph("<b>Operador / Resp. Técnico:</b>", normal_style),
                Paragraph(operator_name, bold_style),
                Paragraph("<b>Fecha de Registro:</b>", normal_style),
                Paragraph(fecha_str, normal_style),
            ],
            [
                Paragraph("<b>Sistema Asistente:</b>", normal_style),
                Paragraph("Mari (Visión Computacional)", normal_style),
                Paragraph("<b>Método de Ensayo:</b>", normal_style),
                Paragraph("Marshall / Densidad In-Situ", normal_style),
            ],
        ]
        t_meta = Table(meta_table_data, colWidths=[130, 140, 130, 140])
        t_meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t_meta)
        story.append(Spacer(1, 12))

        # Tabla de Datos de Probetas y Mediciones
        story.append(Paragraph("Valores Registrados de Campo e Inyección", section_style))

        series = summary_data.get("series", [])
        if not series:
            # Caso de probeta individual
            series = [
                {
                    "probeta": 1,
                    "peso_seco": summary_data.get("peso_seco", 0.0),
                    "peso_sumergido": summary_data.get("peso_sumergido", 0.0),
                    "peso_sss": summary_data.get("peso_sss", 0.0),
                    "temperatura": summary_data.get("temperatura", 0.0),
                    "Gmm": summary_data.get("Gmm", 0.0),
                    "Gmb": summary_data.get("Gmb", 0.0),
                    "Va": summary_data.get("Va_porcentaje", 0.0),
                }
            ]

        # Construir filas de la tabla
        table_headers = [
            Paragraph("<b>Muestra</b>", bold_style),
            Paragraph("<b>P. Seco (g)</b>", bold_style),
            Paragraph("<b>P. Sumerg. (g)</b>", bold_style),
            Paragraph("<b>P. SSS (g)</b>", bold_style),
            Paragraph("<b>Temp (°C)</b>", bold_style),
            Paragraph("<b>Gmm Rice</b>", bold_style),
            Paragraph("<b>Gmb (g/cm³)</b>", bold_style),
            Paragraph("<b>% Vacíos</b>", bold_style),
        ]
        results_rows = [table_headers]

        for s in series:
            p_seco = f"{float(s.get('peso_seco', 0)):.1f}" if s.get('peso_seco') is not None else "-"
            p_sum = f"{float(s.get('peso_sumergido', 0)):.1f}" if s.get('peso_sumergido') is not None else "-"
            p_sss = f"{float(s.get('peso_sss', 0)):.1f}" if s.get('peso_sss') is not None else "-"
            temp = f"{float(s.get('temperatura', 0)):.1f}" if s.get('temperatura') is not None else "-"
            gmm = f"{float(s.get('Gmm', 0)):.3f}" if s.get('Gmm') is not None else "-"
            gmb = f"{float(s.get('Gmb', 0)):.3f}" if s.get('Gmb') is not None else "-"
            va = f"{float(s.get('Va', 0)):.2f}%" if s.get('Va') is not None else "-"

            results_rows.append(
                [
                    Paragraph(f"Probeta {s.get('probeta', 1)}", normal_style),
                    Paragraph(p_seco, normal_style),
                    Paragraph(p_sum, normal_style),
                    Paragraph(p_sss, normal_style),
                    Paragraph(temp, normal_style),
                    Paragraph(gmm, normal_style),
                    Paragraph(gmb, bold_style),
                    Paragraph(va, bold_style),
                ]
            )

        t_results = Table(results_rows, colWidths=[65, 65, 65, 65, 60, 65, 75, 70])
        t_results.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_results)
        story.append(Spacer(1, 14))

        # Evaluación Normativa
        story.append(Paragraph("Diagnóstico de Cumplimiento Normativo (DNV)", section_style))
        avg_va = summary_data.get("promedio_va") or summary_data.get("Va_porcentaje")
        if avg_va is not None:
            va_num = float(avg_va)
            if 3.0 <= va_num <= 5.0:
                eval_text = (
                    f"✅ <b>CONFORME:</b> El porcentaje de vacíos de aire ({va_num:.2f}%) se encuentra dentro del "
                    "rango óptimo establecido por el Pliego de Especificaciones Técnicas Generales de la DNV (3.0% - 5.0%) "
                    "para carpetas de rodamiento convencionales."
                )
                box_bg = colors.HexColor("#F0FFF4")
                box_border = colors.HexColor("#68D391")
            elif va_num < 3.0:
                eval_text = (
                    f"⚠️ <b>ALERTA DE FLUJO PLÁSTICO:</b> Vacíos de aire ({va_num:.2f}%) por debajo del mínimo especificado (&lt; 3.0%). "
                    "Riesgo de exudación de ligante y ahuellamiento prematuro bajo tránsito pesado."
                )
                box_bg = colors.HexColor("#FFFAF0")
                box_border = colors.HexColor("#F6AD55")
            else:
                eval_text = (
                    f"⚠️ <b>ALERTA DE PERMEABILIDAD:</b> Vacíos de aire ({va_num:.2f}%) por encima del límite máximo (&gt; 5.0%). "
                    "Posible susceptibilidad al daño por humedad (stripping) y oxidación acelerada del betún."
                )
                box_bg = colors.HexColor("#FFF5F5")
                box_border = colors.HexColor("#FC8181")
        else:
            eval_text = "Se requiere determinación de Rice (Gmm) para contrastar los vacíos normativos."
            box_bg = colors.HexColor("#F7FAFC")
            box_border = colors.HexColor("#CBD5E0")

        t_eval = Table([[Paragraph(eval_text, normal_style)]], colWidths=[540])
        t_eval.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), box_bg),
                    ("BOX", (0, 0), (-1, -1), 1, box_border),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(t_eval)
        story.append(Spacer(1, 35))

        # Bloque de Firma
        sig_name = operator_name if operator_name else "Franco"
        signature_data = [
            [
                "",
                Paragraph(
                    f"________________________________________<br/>"
                    f"<b>{sig_name}</b><br/>"
                    f"{operator_title}",
                    subtitle_style,
                ),
                "",
            ]
        ]
        t_sig = Table(signature_data, colWidths=[80, 380, 80])
        story.append(t_sig)

        doc.build(story)
        return output_path

    @classmethod
    def generate_technical_report(
        cls,
        title: str,
        subtitle: str,
        summary_text: str,
        output_path: str = "Informe_Tecnico_Laboratorio.pdf",
        operator_name: str = "Franco",
        operator_title: str = "Analista de Estructuras Viales y de Transporte MP: 2205",
    ) -> str:
        """Genera un informe técnico general en PDF a partir del análisis y diagnóstico de planillas."""
        import re

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#1A365D"),
            alignment=1,
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4A5568"),
            alignment=1,
            spaceAfter=10,
        )
        section_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=8,
            spaceAfter=4,
        )
        normal_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=4,
        )
        bold_style = ParagraphStyle(
            "BodyBold",
            parent=normal_style,
            fontName="Helvetica-Bold",
        )

        story = []

        # Encabezado
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(subtitle, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3182CE"), spaceAfter=10))

        # Metadatos del informe
        fecha_str = datetime.now().strftime("%d/%m/%Y - %H:%M")
        meta_table_data = [
            [
                Paragraph("<b>Operador / Resp. Técnico:</b>", normal_style),
                Paragraph(operator_name, bold_style),
                Paragraph("<b>Fecha de Emisión:</b>", normal_style),
                Paragraph(fecha_str, normal_style),
            ],
            [
                Paragraph("<b>Sistema Asistente:</b>", normal_style),
                Paragraph("Mari (Asistente de Laboratorio Vial)", normal_style),
                Paragraph("<b>Normativa de Control:</b>", normal_style),
                Paragraph("Pliegos DNV / Normas IRAM", normal_style),
            ],
        ]
        t_meta = Table(meta_table_data, colWidths=[140, 140, 130, 130])
        t_meta.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_meta)
        story.append(Spacer(1, 12))

        # Sección de Diagnóstico
        story.append(Paragraph("Resumen Ejecutivo y Diagnóstico Técnico", section_style))

        # Limpiar texto e interpretar estilos básicos
        clean_text = summary_text.replace("&", "&amp;")
        clean_text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", clean_text)

        for line in clean_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("### "):
                story.append(Paragraph(line.replace("### ", ""), section_style))
            elif line.startswith("## "):
                story.append(Paragraph(line.replace("## ", ""), section_style))
            elif line.startswith("# "):
                story.append(Paragraph(line.replace("# ", ""), section_style))
            elif line.startswith(("- ", "* ", "• ")):
                bullet = line.lstrip("-*• ")
                story.append(Paragraph(f"• {bullet}", normal_style))
            elif line.startswith("|"):
                # Si es una fila de tabla en markdown, omitir caracteres pipes crudos
                continue
            else:
                try:
                    story.append(Paragraph(line, normal_style))
                except Exception:
                    # En caso de caracteres especiales que fallen en Platypus
                    story.append(Paragraph(re.sub(r"<[^>]*>", "", line), normal_style))

        story.append(Spacer(1, 25))

        # Bloque de Firma
        sig_name = operator_name if operator_name else "Franco"
        signature_data = [
            [
                "",
                Paragraph(
                    f"________________________________________<br/>"
                    f"<b>{sig_name}</b><br/>"
                    f"{operator_title}",
                    subtitle_style,
                ),
                "",
            ]
        ]
        t_sig = Table(signature_data, colWidths=[80, 380, 80])
        story.append(t_sig)

        doc.build(story)
        return output_path


# ---------------------------------------------------------------------------
# Motor de Impresión FPDF: Reportes Técnicos de Alta Jerarquía y Tablas Monospace
# ---------------------------------------------------------------------------
from fpdf import FPDF
import datetime


class PDFReporte(FPDF):
    """Generador corporativo de informes en PDF con FPDF2."""

    def header(self) -> None:
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(0, 51, 102)  # Azul oscuro corporativo
        self.cell(
            self.epw,
            10,
            "INFORME TÉCNICO CONSOLIDADO DE LABORATORIO VIAL",
            border=False,
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        fecha_actual = datetime.datetime.now().strftime("%d/%m/%Y - %H:%M")
        self.cell(
            self.epw,
            6,
            f"Operador: Franco Lobo | Analista: Jarvis QA | Fecha: {fecha_actual}",
            border="B",
            align="C",
            new_x="LMARGIN",
            new_y="NEXT",
        )
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-25)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(0, 0, 0)
        self.cell(self.epw, 4, "___________________________________", align="R", new_x="LMARGIN", new_y="NEXT")
        self.cell(self.epw, 4, "Franco Lobo", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 8)
        self.cell(
            self.epw,
            4,
            "Analista de Estructuras Viales y Transporte | MP: 2205",
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

        # Numeración de página
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(128, 128, 128)
        self.cell(self.epw, 8, f"Página {self.page_no()}", align="C")


def generar_informe_pdf(texto_reporte: str, nombre_archivo: str = "Reporte_Consolidado_Asfalto.pdf") -> str:
    """Convierte el diagnóstico de laboratorio en un PDF técnico estructurado con FPDF."""
    pdf = PDFReporte()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=30)

    lineas = texto_reporte.split("\n")

    for linea in lineas:
        linea_str = linea.strip()
        if not linea_str:
            pdf.ln(2)
            continue

        if linea_str.startswith(("###", "##")):
            pdf.ln(3)
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.set_text_color(0, 51, 102)
            texto_limpio = linea_str.replace("#", "").strip()
            pdf.multi_cell(pdf.epw, 7, text=texto_limpio, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
        elif linea_str.startswith("|"):
            pdf.set_font("Courier", size=7.5)  # Tipografía monoespaciada para tablas
            texto_limpio = linea.replace("**", "")
            pdf.multi_cell(pdf.epw, 4.5, text=texto_limpio, new_x="LMARGIN", new_y="NEXT")
        else:
            pdf.set_font("Helvetica", size=9.5)
            texto_limpio = linea.replace("**", "")
            pdf.multi_cell(pdf.epw, 5.5, text=texto_limpio, new_x="LMARGIN", new_y="NEXT")

    pdf.output(nombre_archivo)
    return nombre_archivo
