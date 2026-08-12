"""Normalisation des nombres extraits d'un CPS francophone.

Un CPS marocain/francais melange les conventions : "19.500 lumens" (point = separateur
de milliers), "0.6 x 0.6" (point = decimale), "3,5 %" (virgule = decimale). Aucune
convention n'est fiable a 100% : cette heuristique reste volontairement simple et
TOUJOURS accompagnee de `raw_value` (jamais remplace silencieusement) pour que le
consultant puisse corriger une valeur mal interpretee lors de la validation humaine.
"""

from __future__ import annotations

import re


def parse_french_number(raw: str) -> float | None:
    text = raw.strip().replace(" ", "").replace(" ", "")
    if not text:
        return None

    if "," in text and "." in text:
        # Les deux separateurs presents : le dernier rencontre est la decimale.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif "." in text:
        integer_part, _, decimal_part = text.rpartition(".")
        if len(decimal_part) == 3 and integer_part:
            # Ex: "19.500" -> separateur de milliers -> 19500
            text = integer_part + decimal_part
        # sinon (ex: "0.6", "8.5") : point decimal standard, on ne touche pas.

    try:
        return float(text)
    except ValueError:
        return None


_NUMBER_RE = re.compile(r"\d[\d\s.,]*\d|\d")


def first_number(text: str) -> tuple[str, float | None] | None:
    """Renvoie (texte_brut, valeur) du premier nombre trouve dans `text`, ou None."""
    match = _NUMBER_RE.search(text)
    if not match:
        return None
    raw = match.group(0)
    return raw, parse_french_number(raw)
