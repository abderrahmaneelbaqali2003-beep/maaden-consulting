"""Section 5 - Matrice de compatibilite. Reutilise integralement `validated_rules`,
`warnings` et `blocking_reasons` du moteur deterministe : jamais de reconstruction
manuelle des regles ici."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from app.reports import formatting as fmt
from app.reports.layout import data_table, section_title
from app.reports.models import ReportData


def build(data: ReportData, styles: dict) -> list:
    elements: list = [section_title("5. Matrice de compatibilite", styles)]
    elements.append(Spacer(1, 0.4 * cm))

    rows: list[list[str]] = []
    for rule in data.validated_rules:
        rows.append(["Critere technique valide", fmt.sanitize_pdf_text(rule)])
    for warning in data.warnings:
        rows.append(["Avertissement", fmt.sanitize_pdf_text(warning)])
    for reason in data.blocking_reasons:
        rows.append(["Raison de refus", fmt.sanitize_pdf_text(reason)])

    if not rows:
        elements.append(Paragraph("Aucune regle de compatibilite disponible pour cette configuration.", styles["body_muted"]))
        return elements

    elements.append(
        data_table(["Statut", "Regle / observation"], rows, styles, col_widths=[4 * cm, 13 * cm])
    )
    return elements
