"""Tests de l'extraction deterministe CPS/CCTP (regex, aucun LLM)."""

from app.cps.extractor import CpsExtractor
from app.cps.normalizer import parse_french_number
from app.rag.parsing import ParsedPage

REAL_CCTP_EXCERPT_P41 = """
Le luminaire d'eclairage public a LED ayant les caracteristiques techniques suivantes :
Hauteur d'installation : 8 m ; 10m
Etancheite : IP 66
Resistance aux chocs : IK 10
Moyenne taille : jusqu'a 140W pour un flux allant jusqu'a 19.500 lumens
Temperature de couleur : 3000K
"""

REAL_CCTP_EXCERPT_P42 = """
CRI> 70
Courant Fonctionnant inferieur a 750 mA
Voltage 220-240 VAC 50-60 Hz.
Tension nominale : 48 V.
Driver disponible avec sortie 1-10V, DALI, PLC
Implantation unilaterale, espacement de 30 m.
Longueur du troncon : 300 m.
"""


def test_parse_french_number_thousands_separator():
    assert parse_french_number("19.500") == 19500.0
    assert parse_french_number("100.000") == 100000.0


def test_parse_french_number_decimal_point():
    assert parse_french_number("0.6") == 0.6
    assert parse_french_number("8.5") == 8.5


def test_parse_french_number_decimal_comma():
    assert parse_french_number("3,5") == 3.5


def test_extract_flux_and_power_from_real_cctp_text():
    pages = [ParsedPage(page_number=41, text=REAL_CCTP_EXCERPT_P41)]
    drafts = CpsExtractor().extract(pages)

    flux = next(d for d in drafts if d.field_name == "required_flux_lm")
    assert flux.numeric_value == 19500.0
    assert flux.unit == "lm"
    assert flux.source_page == 41
    assert flux.operator == ">="

    power = next(d for d in drafts if d.field_name == "max_power_w")
    assert power.numeric_value == 140.0
    assert power.operator == "<="


def test_extract_cct_and_pole_height():
    """L'extraction est volontairement restreinte aux 7 grandeurs utiles a l'etude
    (flux, CCT, puissance, tension nominale, courant, protocole, geometrie routiere) :
    IP/IK ne sont plus extraits (bruit non exploitable par le moteur, retire a la
    demande du consultant)."""
    pages = [ParsedPage(page_number=41, text=REAL_CCTP_EXCERPT_P41)]
    drafts = CpsExtractor().extract(pages)

    cct = next(d for d in drafts if d.field_name == "cct_k")
    assert cct.numeric_value == 3000.0

    assert not any(d.field_name in ("ip_required", "ik_required") for d in drafts)

    height = next(d for d in drafts if d.field_name == "pole_height_m")
    assert height.numeric_value == 8.0


def test_extract_current_voltage_geometry_and_protocols():
    pages = [ParsedPage(page_number=42, text=REAL_CCTP_EXCERPT_P42)]
    drafts = CpsExtractor().extract(pages)

    current = next(d for d in drafts if d.field_name == "current_nominal_ma")
    assert current.numeric_value == 750.0
    assert current.scope == "module"

    # La tension secteur (220-240 VAC) ne doit jamais etre confondue avec la tension
    # nominale du module : seule la phrase explicite "tension nominale" doit matcher.
    voltage = next(d for d in drafts if d.field_name == "voltage_nominal_v")
    assert voltage.numeric_value == 48.0
    assert voltage.scope == "module"
    assert not any(d.raw_value == "220" or d.raw_value == "240" for d in drafts if d.field_name == "voltage_nominal_v")

    layout = next(d for d in drafts if d.field_name == "layout_type")
    assert layout.raw_value == "unilateral"

    spacing = next(d for d in drafts if d.field_name == "pole_spacing_m")
    assert spacing.numeric_value == 30.0

    length = next(d for d in drafts if d.field_name == "road_length_m")
    assert length.numeric_value == 300.0

    protocols = {d.raw_value for d in drafts if d.field_name == "protocol"}
    assert protocols == {"DALI", "1-10V", "PLC"}


def test_extraction_every_draft_is_traceable():
    pages = [ParsedPage(page_number=41, text=REAL_CCTP_EXCERPT_P41), ParsedPage(page_number=42, text=REAL_CCTP_EXCERPT_P42)]
    drafts = CpsExtractor().extract(pages)

    assert len(drafts) > 0
    for draft in drafts:
        assert draft.source_page in (41, 42)
        assert draft.source_excerpt  # jamais vide : toute exigence pointe vers son texte source


def test_has_sufficient_text_detects_scanned_document():
    scanned_pages = [ParsedPage(page_number=i, text="") for i in range(1, 6)]
    assert CpsExtractor().has_sufficient_text(scanned_pages) is False

    real_pages = [ParsedPage(page_number=1, text=REAL_CCTP_EXCERPT_P41)]
    assert CpsExtractor().has_sufficient_text(real_pages) is True


def test_no_extraction_on_empty_document():
    assert CpsExtractor().extract([]) == []
