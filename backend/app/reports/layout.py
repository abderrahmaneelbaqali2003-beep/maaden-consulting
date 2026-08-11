"""Styles et primitives de mise en page partagees entre `pdf_generator.py` et les
sections (`sections/*.py`). Isole dans un module a part pour eviter tout import
circulaire (les sections ne dependent jamais de `pdf_generator.py`)."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Table, TableStyle

from app.reports import formatting as fmt


def build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_kicker": ParagraphStyle(
            "cover_kicker", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=11,
            textColor=colors.HexColor(fmt.GOLD), alignment=TA_CENTER, spaceAfter=6,
        ),
        "cover_title": ParagraphStyle(
            "cover_title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=26,
            textColor=colors.HexColor(fmt.ANTHRACITE), alignment=TA_CENTER, spaceAfter=4,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle", parent=base["Normal"], fontName="Helvetica", fontSize=14,
            textColor=colors.HexColor(fmt.GRAY_MUTED), alignment=TA_CENTER, spaceAfter=2,
        ),
        "cover_meta_label": ParagraphStyle(
            "cover_meta_label", parent=base["Normal"], fontName="Helvetica", fontSize=9,
            textColor=colors.HexColor(fmt.GRAY_MUTED), alignment=TA_CENTER,
        ),
        "cover_meta_value": ParagraphStyle(
            "cover_meta_value", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=12,
            textColor=colors.HexColor(fmt.ANTHRACITE), alignment=TA_CENTER, spaceAfter=10,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=15,
            textColor=colors.HexColor(fmt.ANTHRACITE), spaceBefore=4, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5,
            textColor=colors.HexColor(fmt.ANTHRACITE), spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName="Helvetica", fontSize=9.5,
            textColor=colors.HexColor(fmt.ANTHRACITE), leading=13, alignment=TA_LEFT,
        ),
        "body_muted": ParagraphStyle(
            "body_muted", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            textColor=colors.HexColor(fmt.GRAY_MUTED), leading=12,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"], fontName="Helvetica", fontSize=7.5,
            textColor=colors.HexColor(fmt.GRAY_MUTED), leading=10,
        ),
        "table_cell": ParagraphStyle(
            "table_cell", parent=base["Normal"], fontName="Helvetica", fontSize=8.5,
            textColor=colors.HexColor(fmt.ANTHRACITE), leading=11,
        ),
        "table_cell_label": ParagraphStyle(
            "table_cell_label", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
            textColor=colors.HexColor(fmt.GRAY_MUTED), leading=11,
        ),
        "table_header": ParagraphStyle(
            "table_header", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8.5,
            textColor=colors.HexColor(fmt.WHITE), leading=11,
        ),
        "badge_success": ParagraphStyle(
            "badge_success", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.HexColor(fmt.SUCCESS),
        ),
        "badge_warning": ParagraphStyle(
            "badge_warning", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.HexColor(fmt.WARNING),
        ),
        "badge_destructive": ParagraphStyle(
            "badge_destructive", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=9,
            textColor=colors.HexColor(fmt.DESTRUCTIVE),
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer", parent=base["Normal"], fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=colors.HexColor(fmt.GRAY_MUTED), leading=10, alignment=TA_LEFT,
        ),
    }


def section_title(text: str, styles: dict) -> Table:
    """Titre de section : bandeau anthracite pleine largeur avec un liseret gold."""
    t = Table(
        [[Paragraph(text, ParagraphStyle("st", parent=styles["h1"], textColor=colors.white))]],
        colWidths=[17 * cm],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fmt.ANTHRACITE)),
                ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor(fmt.GOLD)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def kv_table(rows: list[tuple[str, str]], styles: dict, col_widths=(6.5 * cm, 10.5 * cm)) -> Table:
    """Table label/valeur a deux colonnes (fiches Projet, Driver, Module, Lentille)."""
    data = [
        [Paragraph(label, styles["table_cell_label"]), Paragraph(value, styles["table_cell"])]
        for label, value in rows
    ]
    t = Table(data, colWidths=list(col_widths))
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(fmt.GRAY_BORDER)),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAF8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def data_table(header: list[str], rows: list[list[str]], styles: dict, col_widths: list[float]) -> Table:
    """Table a en-tete repete sur la page suivante (`repeatRows=1`) si elle est coupee."""
    header_row = [Paragraph(h, styles["table_header"]) for h in header]
    body_rows = [[Paragraph(cell, styles["table_cell"]) for cell in row] for row in rows]
    t = Table([header_row] + body_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(fmt.ANTHRACITE)),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(fmt.GRAY_BORDER)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAF8")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def status_badge_style(status: str, styles: dict) -> ParagraphStyle:
    return {
        "success": styles["badge_success"],
        "warning": styles["badge_warning"],
        "destructive": styles["badge_destructive"],
    }.get(status, styles["badge_warning"])
