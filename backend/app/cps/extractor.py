"""Extraction deterministe d'exigences techniques depuis le texte d'un CPS/CCTP.

Chaque champ detecte reste tracable (page + extrait) et n'est jamais applique
automatiquement : `ExtractedRequirementDraft` alimente uniquement l'ecran de
validation humaine (`ExtractedRequirement.validation_status="detected"`).
"""

from __future__ import annotations

import re

from app.cps import patterns as p
from app.cps.models import ExtractedRequirementDraft
from app.cps.normalizer import parse_french_number
from app.rag.parsing import ParsedPage

MAX_EXCERPT_LENGTH = 220


def _excerpt(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    excerpt = text[line_start:line_end].strip()
    if len(excerpt) > MAX_EXCERPT_LENGTH:
        excerpt = excerpt[:MAX_EXCERPT_LENGTH].rstrip() + "..."
    return excerpt


def _numeric_draft(
    match: re.Match,
    text: str,
    page_number: int,
    category: str,
    scope: str,
    field_name: str,
    operator: str,
    unit: str | None,
    group: int = 1,
) -> ExtractedRequirementDraft | None:
    raw = match.group(group)
    value = parse_french_number(raw)
    if value is None:
        return None
    return ExtractedRequirementDraft(
        category=category,
        scope=scope,
        field_name=field_name,
        operator=operator,
        raw_value=raw.strip(),
        numeric_value=value,
        unit=unit,
        source_page=page_number,
        source_excerpt=_excerpt(text, match.start(), match.end()),
        extraction_confidence="medium",
    )


def _extract_regex_field(
    text: str,
    page_number: int,
    pattern: re.Pattern,
    category: str,
    scope: str,
    field_name: str,
    operator: str,
    unit: str | None,
    group: int = 1,
) -> list[ExtractedRequirementDraft]:
    drafts = []
    for match in pattern.finditer(text):
        draft = _numeric_draft(match, text, page_number, category, scope, field_name, operator, unit, group)
        if draft is not None:
            drafts.append(draft)
    return drafts


def _extract_layout_type(text: str, page_number: int) -> list[ExtractedRequirementDraft]:
    drafts = []
    lowered = text.lower()
    for layout_value, keywords in p.LAYOUT_KEYWORDS.items():
        for keyword in keywords:
            index = lowered.find(keyword)
            if index == -1:
                continue
            drafts.append(
                ExtractedRequirementDraft(
                    category="geometry", scope="system", field_name="layout_type", operator="==",
                    raw_value=layout_value, numeric_value=None, unit=None,
                    source_page=page_number, source_excerpt=_excerpt(text, index, index + len(keyword)),
                    extraction_confidence="medium",
                )
            )
            break  # un seul candidat par type d'implantation et par page
    return drafts


def _extract_protocols(text: str, page_number: int) -> list[ExtractedRequirementDraft]:
    drafts = []
    seen_spans: set[tuple[int, int]] = set()
    for keyword in p.PROTOCOL_KEYWORDS:
        for match in re.finditer(re.escape(keyword), text, re.IGNORECASE):
            # Evite de compter "DALI" en double a l'interieur d'un "DALI-2" deja trouve.
            if any(s <= match.start() and match.end() <= e for s, e in seen_spans):
                continue
            seen_spans.add((match.start(), match.end()))
            drafts.append(
                ExtractedRequirementDraft(
                    category="electrical", scope="driver", field_name="protocol", operator="==",
                    raw_value=keyword, numeric_value=None, unit=None,
                    source_page=page_number, source_excerpt=_excerpt(text, match.start(), match.end()),
                    extraction_confidence="high",
                )
            )
    return drafts


FIELD_EXTRACTORS = [
    lambda text, pg: _extract_regex_field(text, pg, p.FLUX_LM, "lighting", "luminaire", "required_flux_lm", ">=", "lm"),
    lambda text, pg: _extract_regex_field(text, pg, p.POWER_W, "lighting", "luminaire", "max_power_w", "<=", "W"),
    lambda text, pg: _extract_regex_field(text, pg, p.CCT_K, "lighting", "luminaire", "cct_k", "==", "K"),
    lambda text, pg: _extract_regex_field(text, pg, p.CURRENT_MA, "electrical", "module", "current_nominal_ma", "==", "mA"),
    lambda text, pg: _extract_regex_field(text, pg, p.VOLTAGE_NOMINAL_V, "electrical", "module", "voltage_nominal_v", "==", "V"),
    lambda text, pg: _extract_regex_field(text, pg, p.POLE_HEIGHT_M, "geometry", "road", "pole_height_m", "==", "m"),
    lambda text, pg: _extract_regex_field(text, pg, p.POLE_SPACING_M, "geometry", "road", "pole_spacing_m", "==", "m"),
    lambda text, pg: _extract_regex_field(text, pg, p.ROAD_WIDTH_M, "geometry", "road", "road_width_m", "==", "m"),
    lambda text, pg: _extract_regex_field(text, pg, p.ROAD_LENGTH_M, "geometry", "road", "road_length_m", "==", "m"),
    _extract_layout_type,
    _extract_protocols,
]


class CpsExtractor:
    """Point d'entree unique de l'extraction. Fonctionne page par page pour conserver
    la tracabilite (`source_page`)."""

    def extract(self, pages: list[ParsedPage]) -> list[ExtractedRequirementDraft]:
        drafts: list[ExtractedRequirementDraft] = []
        for page in pages:
            if not page.text.strip():
                continue
            for extractor in FIELD_EXTRACTORS:
                drafts.extend(extractor(page.text, page.page_number))
        return drafts

    def has_sufficient_text(self, pages: list[ParsedPage]) -> bool:
        """Heuristique simple : un CPS scanne (image sans OCR) produit tres peu de texte
        extractible par page en moyenne. Seuil bas et volontairement prudent (jamais
        d'invention de contenu en dessous)."""
        if not pages:
            return False
        total_chars = sum(len(page.text.strip()) for page in pages)
        return (total_chars / len(pages)) >= 30
