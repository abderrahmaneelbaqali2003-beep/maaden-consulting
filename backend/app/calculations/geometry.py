"""Grandeurs geometriques (section 3.F, 3.G, 3.I).

Indicateurs de pre-dimensionnement uniquement : aucun ne constitue une preuve
de conformite normative (EN/NM 13201). L'estimation du nombre de luminaires
n'est jamais un dimensionnement final — la geometrie reelle du projet peut
le modifier.
"""

import math

Layout = str  # "unilateral" | "opposite" | "staggered" | "central"


def calculate_spacing_height_ratio(spacing_m: float | None, height_m: float | None) -> float | None:
    """S/H = pole_spacing_m / pole_height_m. Ex: 30 / 10 = 3.0."""
    if spacing_m is None or height_m is None or height_m == 0:
        return None
    return spacing_m / height_m


def calculate_road_segment_area_m2(width_m: float | None, spacing_m: float | None) -> float | None:
    """A = road_width_m x pole_spacing_m. Ex: 7 x 30 = 210 m2."""
    if width_m is None or spacing_m is None:
        return None
    return width_m * spacing_m


def estimate_luminaire_count(
    road_length_m: float | None, pole_spacing_m: float | None, layout_type: Layout | None
) -> int | None:
    """Estimation V1 du nombre de points lumineux (jamais un dimensionnement final).

    base_positions ~= ceil(road_length_m / pole_spacing_m) + 1

    - unilateral : base_positions (un seul cote).
    - opposite   : 2 x base_positions (vis-a-vis, deux cotes alignes).
    - staggered  : base_positions (quinconce : memes points lumineux totaux que
      l'unilaterale, repartis en alternance sur les deux cotes).
    - central    : base_positions (mat central ; approximation V1, a affiner
      selon l'architecture reelle du luminaire bi-directionnel).
    """
    if road_length_m is None or pole_spacing_m is None or pole_spacing_m <= 0:
        return None
    base_positions = math.ceil(road_length_m / pole_spacing_m) + 1
    if layout_type == "opposite":
        return 2 * base_positions
    return base_positions
