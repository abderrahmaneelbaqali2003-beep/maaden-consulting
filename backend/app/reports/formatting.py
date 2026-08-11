"""Helpers de formatage partages par toutes les sections du rapport PDF.

Regle d'or : une donnee absente s'affiche toujours "Non renseigne", jamais
None/null/undefined ni une valeur inventee (0, "-", etc.).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from xml.sax.saxutils import escape

NOT_PROVIDED = "Non renseigne"

# Colors MAADEN (identite visuelle reprise de frontend/src/index.css) --------------------
ANTHRACITE = "#25292B"
GRAY_MUTED = "#707779"
GRAY_BORDER = "#DADBD7"
GOLD = "#C99A32"
GOLD_LIGHT = "#F4EAD3"
WHITE = "#FFFFFF"
BACKGROUND = "#F5F5F2"
SUCCESS = "#2F7D4A"
SUCCESS_BG = "#E7F3EB"
WARNING = "#B56E16"
WARNING_BG = "#FBF0DD"
DESTRUCTIVE = "#B33A3A"
DESTRUCTIVE_BG = "#F8E7E7"


def fmt_text(value: str | None) -> str:
    if value is None:
        return NOT_PROVIDED
    text = value.strip()
    return text if text else NOT_PROVIDED


def fmt_number(value: float | int | None, unit: str | None = None, decimals: int = 1) -> str:
    if value is None:
        return NOT_PROVIDED
    if isinstance(value, int) and not isinstance(value, bool):
        formatted = f"{value:,}".replace(",", " ")
    else:
        formatted = f"{value:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{formatted} {unit}" if unit else formatted


def fmt_bool(value: bool | None, true_label: str = "Oui", false_label: str = "Non") -> str:
    if value is None:
        return NOT_PROVIDED
    return true_label if value else false_label


def fmt_datetime(value: datetime | None) -> str:
    if value is None:
        return NOT_PROVIDED
    return value.strftime("%d/%m/%Y %H:%M")


def fmt_date(value: datetime | None) -> str:
    if value is None:
        return NOT_PROVIDED
    return value.strftime("%d/%m/%Y")


def sanitize_pdf_text(value: str | None) -> str:
    """Echappe tout texte externe (commentaire consultant, resume documentaire...) avant
    de l'inserer dans un `reportlab.platypus.Paragraph` : le moteur Paragraph interprete un
    sous-ensemble de balises pseudo-HTML, donc un texte utilisateur non echappe pourrait
    casser la mise en page ou injecter une balise. `xml.sax.saxutils.escape` neutralise
    <, > et & ; les retours a la ligne sont convertis en <br/> explicite APRES echappement.
    """
    if not value:
        return ""
    cleaned = "".join(ch for ch in value if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    escaped = escape(cleaned.strip())
    return escaped.replace("\n", "<br/>")


def sanitize_filename(value: str) -> str:
    """Reduit une chaine a un nom de fichier sur : ascii, alphanum + `-`/`_`, longueur bornee.
    N'utilise jamais un texte utilisateur brut/non filtre dans un nom de fichier."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized).strip("_")
    return safe[:120] or "rapport"


def build_report_reference(result_id: int, year: int) -> str:
    """Identifiant stable et reproductible : MC-{annee}-{result_id sur 6 chiffres}."""
    return f"MC-{year}-{result_id:06d}"


def relevance_label_by_rank(index: int) -> str:
    """`relevance_score` (fusion RRF hybride) n'est pas une probabilite normalisee : jamais
    affiche en %. On derive un niveau qualitatif a partir du rang relatif au sein des
    preuves d'une meme configuration (deja triees par pertinence decroissante)."""
    if index == 0:
        return "Elevee"
    if index <= 2:
        return "Moyenne"
    return "Faible"


def confidence_label(confidence: str) -> str:
    return {
        "high": "ELEVEE",
        "medium": "MOYENNE",
        "low": "FAIBLE",
        "insufficient_evidence": "PREUVES INSUFFISANTES",
    }.get(confidence, "PREUVES INSUFFISANTES")
