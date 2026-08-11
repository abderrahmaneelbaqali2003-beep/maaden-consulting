"""Section 1 - Informations du projet."""

from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Spacer

from app.reports import formatting as fmt
from app.reports.layout import kv_table, section_title
from app.reports.models import ReportData

LAYOUT_LABELS = {
    "unilateral": "Unilaterale",
    "opposite": "Vis-a-vis (opposee)",
    "staggered": "Quinconce",
    "central": "Centrale (bi-face)",
}


def build(data: ReportData, styles: dict) -> list:
    project = data.project
    rows = [
        ("Type de voie", fmt.fmt_text(project.road_type)),
        ("Largeur de chaussee", fmt.fmt_number(project.road_width_m, "m")),
        ("Longueur du troncon", fmt.fmt_number(project.road_length_m, "m")),
        ("Hauteur du mat", fmt.fmt_number(project.pole_height_m, "m")),
        ("Espacement des mats", fmt.fmt_number(project.pole_spacing_m, "m")),
        ("Type d'implantation", LAYOUT_LABELS.get(project.layout_type or "", fmt.fmt_text(project.layout_type))),
        ("Flux lumineux requis", fmt.fmt_number(project.required_flux_lm, "lm", 0)),
        ("Temperature de couleur (CCT)", fmt.fmt_number(project.required_cct_k, "K", 0)),
        ("Puissance maximale autorisee", fmt.fmt_number(project.max_power_w, "W")),
        ("Tension nominale", fmt.fmt_number(project.voltage_nominal_v, "V")),
        ("Courant nominal", fmt.fmt_number(project.current_nominal_ma, "mA")),
        ("Protocole", fmt.fmt_text(project.protocol)),
        ("Package LED", fmt.fmt_text(project.led_package)),
        ("Temperature ambiante", fmt.fmt_number(project.ambient_temperature_c, "C")),
    ]
    return [
        section_title("1. Informations du projet", styles),
        Spacer(1, 0.4 * cm),
        kv_table(rows, styles),
    ]
