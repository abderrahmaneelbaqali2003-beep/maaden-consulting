"""Mise en page du rapport PDF (ReportLab, 100% local/offline). Ce module assemble les
sections (`sections/*.py`) en document final et gere l'habillage commun (page de garde,
pied de page avec pagination). Aucun calcul, aucune decision technique ici : toute
donnee affichee provient de `ReportData`, deja assemblee en lecture seule par
`ReportService`.
"""

from __future__ import annotations

import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from app.reports import formatting as fmt
from app.reports.layout import build_styles
from app.reports.models import ReportData
from app.reports.sections import (
    calculations_section,
    compatibility_section,
    configuration_section,
    documentary_section,
    project_section,
    validation_section,
)

LOGO_PATH = Path(__file__).resolve().parent.parent / "static" / "branding" / "maaden-consulting-logo.png"

PAGE_SIZE = A4
MARGIN = 2 * cm


class _NumberedCanvas(pdf_canvas.Canvas):
    """Canvas differant le dessin du pied de page ("Page X / Y") a `save()`, seul moment
    ou le nombre total de pages est connu (necessite un rendu en 2 passes)."""

    def __init__(self, *args, report_reference: str = "", **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: list[dict] = []
        self.report_reference = report_reference

    def showPage(self):
        """Accumule l'etat de la page courante sans encore la valider dans le document
        (`self._startPage()`, pas `super().showPage()`) : `super().showPage()` appellerait
        `self._doc.addPage(...)` immediatement, et la page serait ajoutee une seconde fois
        lors de la boucle de `save()` -> PDF avec chaque page dupliquee. La validation
        reelle de chaque page n'a lieu qu'une seule fois, dans `save()`, une fois le pied
        de page dessine."""
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total_pages = len(self._saved_states)
        for index in range(total_pages):
            self.__dict__.update(self._saved_states[index])
            self._draw_footer(index + 1, total_pages)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def _draw_footer(self, page_number: int, total_pages: int):
        self.saveState()
        self.setStrokeColor(colors.HexColor(fmt.GRAY_BORDER))
        self.setLineWidth(0.5)
        self.line(MARGIN, 1.3 * cm, PAGE_SIZE[0] - MARGIN, 1.3 * cm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(colors.HexColor(fmt.GRAY_MUTED))
        self.drawString(MARGIN, 1.0 * cm, f"MAADEN Consulting / Rapport {self.report_reference}")
        self.drawRightString(PAGE_SIZE[0] - MARGIN, 1.0 * cm, f"Page {page_number} / {total_pages}")
        self.restoreState()


class PdfGenerator:
    def generate(self, data: ReportData) -> bytes:
        styles = build_styles()
        buffer = io.BytesIO()

        def _make_canvas(*args, **kwargs):
            return _NumberedCanvas(*args, report_reference=data.reference, **kwargs)

        doc = BaseDocTemplate(
            buffer,
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=1.8 * cm,
            title=f"Rapport MAADEN Consulting {data.reference}",
        )
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

        story: list = []
        story.extend(self._cover(data, styles))
        story.append(NextPageTemplate("main"))
        story.append(PageBreak())
        story.extend(project_section.build(data, styles))
        story.append(PageBreak())
        story.extend(configuration_section.build(data, styles))
        story.append(PageBreak())
        story.extend(calculations_section.build(data, styles))
        story.append(PageBreak())
        story.extend(compatibility_section.build(data, styles))
        story.append(PageBreak())
        story.extend(documentary_section.build(data, styles))
        story.append(PageBreak())
        story.extend(validation_section.build(data, styles))

        doc.build(story, canvasmaker=_make_canvas)
        return buffer.getvalue()

    def _cover(self, data: ReportData, styles: dict) -> list:
        elements: list = [Spacer(1, 2.5 * cm)]
        if LOGO_PATH.exists():
            img = Image(str(LOGO_PATH), width=5 * cm, height=5 * cm * 0.45)
            img.hAlign = "CENTER"
            elements.append(img)
        elements.append(Spacer(1, 1.2 * cm))
        elements.append(Paragraph("MAADEN CONSULTING", styles["cover_kicker"]))
        elements.append(Paragraph("RAPPORT DE RECOMMANDATION TECHNIQUE", styles["cover_title"]))
        elements.append(Paragraph("ECLAIRAGE PUBLIC", styles["cover_subtitle"]))
        elements.append(Spacer(1, 1.8 * cm))

        meta_rows = [
            ("REFERENCE", data.reference),
            ("DATE", fmt.fmt_date(data.generated_at)),
            ("PROJET", data.project_name or fmt.NOT_PROVIDED),
        ]
        for label, value in meta_rows:
            elements.append(Paragraph(label, styles["cover_meta_label"]))
            elements.append(Paragraph(value, styles["cover_meta_value"]))

        elements.append(Spacer(1, 0.6 * cm))
        status_table = Table(
            [
                [
                    Paragraph(
                        "STATUT : CONFIGURATION VALIDEE",
                        ParagraphStyle(
                            "cover_status", parent=styles["cover_meta_value"], textColor=colors.white, alignment=TA_CENTER
                        ),
                    )
                ]
            ],
            colWidths=[10 * cm],
        )
        status_table.hAlign = "CENTER"
        status_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fmt.SUCCESS)),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(status_table)
        elements.append(Spacer(1, 0.4 * cm))
        elements.append(Paragraph(f"Valide par : {data.validation.validator_name}", styles["cover_meta_value"]))

        elements.append(Spacer(1, 2 * cm))
        elements.append(
            Paragraph(
                "Ce rapport constitue une aide a la decision technique fondee sur les donnees disponibles dans "
                "MAADEN Consulting. Il ne remplace pas les essais fabricant, certificats, etudes photometriques "
                "reglementaires, simulations DIALux ni la validation finale d'un ingenieur ou consultant qualifie.",
                styles["disclaimer"],
            )
        )
        return elements
