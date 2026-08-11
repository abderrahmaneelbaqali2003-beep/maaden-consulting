"""Section 10 - Validation du consultant. Aucune signature manuscrite generee
automatiquement : uniquement le nom, la date et le commentaire saisis par le
consultant au moment de la validation."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from app.reports import formatting as fmt
from app.reports.layout import kv_table, section_title
from app.reports.models import ReportData

DISCLAIMER = (
    "Ce rapport constitue une aide a la decision technique fondee sur les donnees disponibles "
    "dans MAADEN Consulting. Il ne remplace pas les essais fabricant, certificats, etudes "
    "photometriques reglementaires, simulations DIALux ni la validation finale d'un ingenieur "
    "ou consultant qualifie."
)


def build(data: ReportData, styles: dict) -> list:
    elements: list = [section_title("10. Validation du consultant", styles)]
    elements.append(Spacer(1, 0.4 * cm))

    status_style = ParagraphStyle("status_success", parent=styles["badge_success"], alignment=TA_CENTER)
    status_table = Table(
        [[Paragraph("STATUT : VALIDEE", status_style)]],
        colWidths=[6 * cm],
    )
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fmt.SUCCESS_BG)),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    elements.append(status_table)
    elements.append(Spacer(1, 0.4 * cm))

    rows = [
        ("Configuration validee", "Oui"),
        ("Validee par", fmt.fmt_text(data.validation.validator_name)),
        ("Date de validation", fmt.fmt_datetime(data.validation.validated_at)),
        ("Commentaire", fmt.sanitize_pdf_text(data.validation.comment) or fmt.NOT_PROVIDED),
    ]
    elements.append(kv_table(rows, styles))

    elements.append(Spacer(1, 1.5 * cm))
    elements.append(Paragraph("Avertissement", styles["h2"]))
    elements.append(Paragraph(DISCLAIMER, styles["disclaimer"]))

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(
            f"Rapport genere le {fmt.fmt_datetime(data.generated_at)} - Reference {data.reference} - "
            f"Gabarit v{data.template_version}",
            styles["small"],
        )
    )
    return elements
