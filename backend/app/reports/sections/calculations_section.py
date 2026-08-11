"""Section 4 - Calculs techniques. Reutilise `CalculationResult` produit par
`CalculationService` (jamais reimplemente ici). Une grandeur `not_calculable`
n'est jamais affichee (aucune formule dont les entrees sont indisponibles).
Les estimations de pre-dimensionnement (`is_estimate=True`) sont clairement
etiquetees et accompagnees d'une note DIALux/IES."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer

from app.calculations.models import CalculationValue
from app.reports import formatting as fmt
from app.reports.layout import data_table, section_title
from app.reports.models import ReportData

ESTIMATE_NOTE = (
    "Cette valeur constitue une estimation de pre-dimensionnement et ne remplace pas une "
    "simulation photometrique DIALux basee sur un fichier IES/LDT."
)


def _format_inputs(item: CalculationValue) -> str:
    parts = [f"{k} = {v}" for k, v in item.inputs.items() if v is not None]
    return ", ".join(parts) if parts else fmt.NOT_PROVIDED


def _rows(values: list[CalculationValue]) -> list[list[str]]:
    rows = []
    for item in values:
        if item.status == "not_calculable":
            continue
        label = item.label + (" (ESTIMATION)" if item.is_estimate else "")
        result = fmt.fmt_number(item.value, item.unit)
        formula = item.formula or fmt.NOT_PROVIDED
        rows.append([label, formula, _format_inputs(item), result])
    return rows


def build(data: ReportData, styles: dict) -> list:
    calc = data.calculations
    ordered_values = [
        calc.electrical.module_power_w,
        calc.electrical.module_power_consistency_percent,
        calc.electrical.driver_required_power_w,
        calc.electrical.driver_loading_percent,
        calc.electrical.driver_power_margin_percent,
        calc.electrical.luminous_efficacy_lm_w,
        calc.geometry.spacing_height_ratio,
        calc.geometry.road_segment_area_m2,
        calc.geometry.estimated_luminaire_count,
        calc.energy.total_installed_power_kw,
        calc.energy.annual_energy_kwh,
        calc.energy.annual_energy_with_dimming_kwh,
        calc.energy.energy_saving_percent,
        calc.energy.energy_saved_kwh_year,
        calc.energy.annual_energy_cost,
        calc.thermal.driver_thermal_margin_c,
        calc.thermal.lens_thermal_margin_c,
        calc.thermal.tightest_thermal_margin_c,
        calc.photometric.estimated_average_illuminance_lux,
        calc.photometric.uniformity_u0,
    ]

    elements: list = [section_title("4. Calculs techniques", styles)]
    elements.append(Spacer(1, 0.4 * cm))

    rows = _rows(ordered_values)
    has_estimates = any(v.is_estimate and v.status != "not_calculable" for v in ordered_values)

    if not rows:
        elements.append(
            Paragraph(
                "Aucune grandeur technique calculable pour cette configuration (donnees projet/produit "
                "insuffisantes).",
                styles["body_muted"],
            )
        )
        return elements

    elements.append(
        data_table(
            ["Grandeur", "Formule", "Valeurs utilisees", "Resultat"],
            rows,
            styles,
            col_widths=[4.2 * cm, 4.5 * cm, 5.3 * cm, 3 * cm],
        )
    )

    if has_estimates:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(ESTIMATE_NOTE, styles["small"]))

    if calc.warnings:
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph("Avertissements de calcul", styles["h2"]))
        for warning in calc.warnings:
            elements.append(Paragraph(f"- {fmt.sanitize_pdf_text(warning)}", styles["body_muted"]))

    return elements
