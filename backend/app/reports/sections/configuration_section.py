"""Section 2 - Configuration retenue (Driver / Module / Lentille) + Section 3 - Score
technique. Le score technique affiche est celui deja calcule par le moteur
deterministe (`RecommendationResult`) : jamais recalcule ici, jamais mele a la
confiance documentaire (section distincte, voir `documentary_section.py`)."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from app.reports import formatting as fmt
from app.reports.layout import kv_table, section_title
from app.reports.models import ReportData


def _driver_rows(driver) -> list[tuple[str, str]]:
    return [
        ("Fabricant", fmt.fmt_text(driver.manufacturer)),
        ("Reference", fmt.fmt_text(driver.reference)),
        ("Famille produit", fmt.fmt_text(driver.product_family)),
        ("Puissance maximale", fmt.fmt_number(driver.output_power_max_w, "W")),
        (
            "Plage de tension de sortie",
            f"{fmt.fmt_number(driver.output_voltage_min_v, 'V')} - {fmt.fmt_number(driver.output_voltage_max_v, 'V')}",
        ),
        (
            "Plage de courant de sortie",
            f"{fmt.fmt_number(driver.output_current_min_ma, 'mA')} - {fmt.fmt_number(driver.output_current_max_ma, 'mA')}",
        ),
        ("Rendement", fmt.fmt_number(driver.efficiency_percent, "%")),
        ("Protocoles / gradation", ", ".join(driver.protocols) if driver.protocols else fmt.NOT_PROVIDED),
        ("DALI-2", fmt.fmt_bool(driver.dali_2)),
        ("D4i", fmt.fmt_bool(driver.d4i)),
        ("Indice de protection (IP)", fmt.fmt_text(driver.ip_rating)),
        (
            "Certifications",
            ", ".join(
                label
                for label, present in [
                    ("CE", driver.ce_certified),
                    ("ENEC", driver.enec_certified),
                    ("UL", driver.ul_certified),
                    ("RoHS", driver.rohs_compliant),
                ]
                if present
            )
            or fmt.fmt_text(driver.certifications),
        ),
    ]


def _module_rows(module) -> list[tuple[str, str]]:
    return [
        ("Fabricant", fmt.fmt_text(module.manufacturer)),
        ("Reference", fmt.fmt_text(module.reference)),
        ("Famille produit", fmt.fmt_text(module.product_family)),
        ("Package LED", fmt.fmt_text(module.led_package)),
        ("Nombre de LED", fmt.fmt_number(module.led_quantity, decimals=0)),
        ("Tension", fmt.fmt_number(module.input_voltage_nominal_v, "V")),
        ("Courant", fmt.fmt_number(module.current_nominal_ma, "mA")),
        ("Puissance", fmt.fmt_number(module.power_nominal_w, "W")),
        ("Flux lumineux", fmt.fmt_number(module.luminous_flux_nominal_lm, "lm", 0)),
        ("Temperature de couleur (CCT)", fmt.fmt_number(module.cct_nominal_k, "K", 0)),
        ("IRC (CRI)", fmt.fmt_number(module.cri_min, decimals=0)),
        ("Efficacite lumineuse", fmt.fmt_number(module.luminous_efficacy_nominal_lm_w, "lm/W")),
        ("Duree de vie", fmt.fmt_number(module.lifetime_hours, "h", 0)),
        (
            "Certifications",
            ", ".join(
                label
                for label, present in [
                    ("CE", module.ce_certified),
                    ("ENEC", module.enec_certified),
                    ("UL", module.ul_certified),
                    ("RoHS", module.rohs_compliant),
                ]
                if present
            )
            or fmt.fmt_text(module.certifications),
        ),
    ]


def _lens_rows(lens) -> list[tuple[str, str]]:
    return [
        ("Fabricant", fmt.fmt_text(lens.manufacturer)),
        ("Reference", fmt.fmt_text(lens.reference)),
        ("Package LED compatible", fmt.fmt_text(lens.compatible_led_package)),
        ("Nombre de cellules", fmt.fmt_number(lens.optical_cells_quantity, decimals=0)),
        ("Rangees x Colonnes", f"{fmt.fmt_number(lens.rows_count, decimals=0)} x {fmt.fmt_number(lens.columns_count, decimals=0)}"),
        ("Pas X / Y", f"{fmt.fmt_number(lens.lens_pitch_x_mm, 'mm')} / {fmt.fmt_number(lens.lens_pitch_y_mm, 'mm')}"),
        ("Type de distribution", fmt.fmt_text(lens.iesna_distribution_type)),
        ("Angle de faisceau", fmt.fmt_number(lens.beam_angle_horizontal_deg, "deg")),
        ("Fichier IES disponible", fmt.fmt_bool(lens.ies_file_available)),
        ("Fichier LDT disponible", fmt.fmt_bool(lens.ldt_file_available)),
        (
            "Dimensions (L x l x H)",
            f"{fmt.fmt_number(lens.length_mm, 'mm')} x {fmt.fmt_number(lens.width_mm, 'mm')} x {fmt.fmt_number(lens.height_mm, 'mm')}",
        ),
        ("Temperature de fonctionnement max.", fmt.fmt_number(lens.operating_temperature_max_c, "C")),
    ]


def _score_bar(label: str, value: float, max_value: float, styles: dict) -> Table:
    percent = max(0.0, min(1.0, value / max_value)) if max_value else 0.0
    bar_width = 8 * cm
    filled = bar_width * percent
    t = Table(
        [[Paragraph(f"{label}", styles["table_cell"]), Paragraph(f"{value:g}/{max_value:g}", styles["table_cell_label"])]],
        colWidths=[9 * cm, 2 * cm],
    )
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    bar = Table([[""]], colWidths=[filled if filled > 0 else 0.01], rowHeights=[0.35 * cm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fmt.GOLD))]))
    track = Table([[bar]], colWidths=[bar_width], rowHeights=[0.35 * cm])
    track.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(fmt.GRAY_BORDER)),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    wrapper = Table([[t], [track]], colWidths=[11 * cm])
    wrapper.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
    return wrapper


def build(data: ReportData, styles: dict) -> list:
    elements: list = [section_title("2. Configuration retenue", styles)]

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("Driver", styles["h2"]))
    if data.driver:
        elements.append(kv_table(_driver_rows(data.driver), styles))
    else:
        elements.append(Paragraph("Aucun driver associe a cette configuration.", styles["body_muted"]))

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Module LED", styles["h2"]))
    elements.append(kv_table(_module_rows(data.module), styles))

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Lentille", styles["h2"]))
    if data.lens:
        elements.append(kv_table(_lens_rows(data.lens), styles))
    else:
        elements.append(
            Paragraph(
                "Aucune lentille trouvee pour cette configuration - a completer manuellement.",
                styles["badge_warning"],
            )
        )

    elements.append(Spacer(1, 0.6 * cm))
    elements.append(section_title("3. Score technique", styles))
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph(f"Score global : {data.scores.overall:g}/100", styles["h2"]))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(_score_bar("Electrique", data.scores.electrical, 35, styles))
    elements.append(_score_bar("Flux / CCT", data.scores.photometric, 25, styles))
    elements.append(_score_bar("Mecanique / optique", data.scores.mechanical, 20, styles))
    elements.append(_score_bar("Thermique", data.scores.thermal, 10, styles))
    elements.append(_score_bar("Qualite des donnees", data.scores.data_quality, 10, styles))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(
        Paragraph(
            "Ce score technique reflete uniquement la compatibilite calculee par le moteur deterministe. "
            "Il ne doit jamais etre confondu avec la confiance documentaire (section 8).",
            styles["small"],
        )
    )
    return elements
