"""Lecture de fichiers Excel/CSV pour l'import (section 9 du cahier des charges).

Detecte automatiquement :
- la feuille Excel principale a utiliser (par nom, ex: contient 'cleaned')
- le separateur CSV (virgule, point-virgule, tabulation)
"""

import csv
from pathlib import Path

import pandas as pd

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}


def is_allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def list_excel_sheets(file_path: str) -> list[str]:
    return pd.ExcelFile(file_path).sheet_names


def detect_main_sheet(file_path: str, name_hint: str) -> str:
    """Trouve la feuille dont le nom contient `name_hint` (ex: 'cleaned'), sinon la premiere feuille."""
    sheets = list_excel_sheets(file_path)
    for sheet in sheets:
        if name_hint.lower() in sheet.lower():
            return sheet
    return sheets[0]


def detect_csv_delimiter(file_path: str) -> str:
    with open(file_path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        return dialect.delimiter
    except csv.Error:
        return ","


def read_dataframe(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Lit un fichier Excel ou CSV en DataFrame pandas.

    Pour Excel : utilise `sheet_name` si fourni, sinon detecte une feuille 'cleaned'.
    Pour CSV : detecte automatiquement le separateur et gere les nombres a virgule decimale.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        target_sheet = sheet_name or detect_main_sheet(file_path, "cleaned")
        return pd.read_excel(file_path, sheet_name=target_sheet, engine="openpyxl")
    if suffix == ".csv":
        delimiter = detect_csv_delimiter(file_path)
        df = pd.read_csv(file_path, sep=delimiter, encoding="utf-8-sig")
        # Gere les nombres avec virgule decimale (format français) sur les colonnes non numeriques detectees comme texte
        for col in df.columns:
            if df[col].dtype == object:
                converted = pd.to_numeric(
                    df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce"
                )
                # N'applique la conversion que si la quasi-totalite des valeurs non vides sont numeriques
                non_null = df[col].notna().sum()
                if non_null > 0 and converted.notna().sum() >= non_null * 0.9:
                    df[col] = converted
        return df
    raise ValueError(f"Extension de fichier non supportee : {suffix}")
