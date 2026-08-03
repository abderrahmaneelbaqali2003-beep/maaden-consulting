"""Utilitaires de nettoyage de valeurs issues de pandas, partages par les importeurs.

Regle essentielle (section 9 du cahier des charges) : une valeur manquante ne doit
jamais etre convertie en zero ou en chaine vide. Elle doit rester None.
"""

import math

import pandas as pd


def clean_value(value):
    """Convertit une cellule pandas en valeur Python native, en preservant None pour les manquants."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def clean_bool(value) -> bool | None:
    """Normalise une valeur booleenne issue d'Excel (True/False Python, 'Oui'/'Non', 1/0)."""
    value = clean_value(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"oui", "true", "1", "yes"}:
        return True
    if text in {"non", "false", "0", "no"}:
        return False
    return None


def clean_str(value) -> str | None:
    value = clean_value(value)
    return str(value) if value is not None else None


def clean_int(value) -> int | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def clean_float(value) -> float | None:
    value = clean_value(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
