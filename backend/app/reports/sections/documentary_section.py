"""Section 6 - References documentaires, Section 7 - Validations restantes,
Section 8 - Confiance documentaire, Section 9 - Conclusion technique.

Regle de terminologie (critique) : un score de classement documentaire (fusion RRF
hybride) n'est jamais une probabilite/similarite normalisee -> jamais affiche en `%`.
Une preuve documentaire n'est JAMAIS presentee comme une conformite normative acquise
("Conforme IEC 62717") ; seuls des intitules prudents sont utilises : "Reference
applicable", "Preuve a verifier", "Validation documentaire requise".
"""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

from app.reports import formatting as fmt
from app.reports.layout import data_table, section_title, status_badge_style
from app.reports.models import ReportData

EVIDENCE_CATEGORY_LABELS = {
    "road_lighting": "Eclairage routier",
    "photometric": "Performance photometrique",
    "driver_standard": "Securite driver LED",
    "module_standard": "Performance / securite module LED",
    "luminaire_standard": "Securite du luminaire",
    "lens_photometry": "Photometrie de la lentille",
    "smart_lighting": "Commande numerique (DALI / D4i)",
    "safety": "Securite",
    "performance": "Performance",
    "measurement": "Mesure",
}

VERIFICATION_LABELS = {
    "retrieved": "Preuve a verifier",
    "verified": "Reference documentaire verifiee",
    "manual_validation_required": "Validation documentaire requise",
}

CONFIDENCE_STATUS_STYLE = {
    "high": "success",
    "medium": "warning",
    "low": "warning",
    "insufficient_evidence": "destructive",
}

CONFIDENCE_SENTENCE = (
    "La confiance documentaire constitue un indicateur de disponibilite et de qualite des "
    "preuves associees. Elle ne modifie pas la compatibilite technique calculee par le "
    "moteur deterministe."
)


def build(data: ReportData, styles: dict) -> list:
    elements: list = [section_title("6. References documentaires", styles)]
    elements.append(Spacer(1, 0.4 * cm))

    doc = data.documentary
    if doc.evidence:
        rows = [
            [
                EVIDENCE_CATEGORY_LABELS.get(e.category, e.category),
                fmt.sanitize_pdf_text(e.document),
                fmt.fmt_text(e.section),
                fmt.fmt_number(e.page, decimals=0),
                fmt.sanitize_pdf_text(e.summary),
                VERIFICATION_LABELS.get(e.verification_status, e.verification_status),
                f"Pertinence documentaire : {e.relevance_label}",
            ]
            for e in doc.evidence
        ]
        elements.append(
            data_table(
                ["Categorie", "Document", "Section", "Page", "Resume", "Statut", "Pertinence"],
                rows,
                styles,
                col_widths=[2.6 * cm, 2.6 * cm, 2.2 * cm, 1.1 * cm, 4.5 * cm, 2.5 * cm, 2.5 * cm],
            )
        )
    else:
        elements.append(Paragraph("Aucune preuve documentaire retrouvee pour cette configuration.", styles["body_muted"]))

    # --- Section 7 : Validations restantes ---
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(section_title("7. Validations restantes", styles))
    elements.append(Spacer(1, 0.3 * cm))
    if data.remaining_validations:
        for item in data.remaining_validations:
            elements.append(Paragraph(f"- {fmt.sanitize_pdf_text(item)}", styles["body"]))
    else:
        elements.append(Paragraph("Aucune validation complementaire identifiee.", styles["body_muted"]))

    # --- Section 8 : Confiance documentaire ---
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(section_title("8. Confiance documentaire", styles))
    elements.append(Spacer(1, 0.3 * cm))
    badge_status = CONFIDENCE_STATUS_STYLE.get(doc.confidence, "warning")
    badge = Table(
        [[Paragraph(fmt.confidence_label(doc.confidence), status_badge_style(badge_status, styles))]],
        colWidths=[6 * cm],
    )
    bg = {"success": fmt.SUCCESS_BG, "warning": fmt.WARNING_BG, "destructive": fmt.DESTRUCTIVE_BG}[badge_status]
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(badge)
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph(CONFIDENCE_SENTENCE, styles["body_muted"]))

    # --- Section 9 : Conclusion technique ---
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(section_title("9. Conclusion technique", styles))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(fmt.sanitize_pdf_text(data.conclusion), styles["body"]))

    return elements
