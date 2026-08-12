"""Structures internes du pipeline d'extraction CPS (pas d'ORM ici)."""

from __future__ import annotations

from dataclasses import dataclass

CATEGORIES = {"lighting", "electrical", "luminaire", "geometry", "environment", "energy", "documentary"}
SCOPES = {"driver", "module", "lens", "luminaire", "road", "photometric", "system", "documentary"}


@dataclass
class ExtractedRequirementDraft:
    category: str
    scope: str
    field_name: str
    operator: str  # <=, >=, ==
    raw_value: str
    numeric_value: float | None
    unit: str | None
    source_page: int
    source_excerpt: str
    extraction_confidence: str  # high / medium / low
