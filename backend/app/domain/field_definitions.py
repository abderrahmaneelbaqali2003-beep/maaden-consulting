"""Source de verite UNIQUE pour les champs d'exigence consommes par l'etude MAADEN.

Vit dans `app/domain/` (et non `app/cps/` ni `app/ai/`) precisement pour que le CPS et
l'assistant IA la partagent sans que l'un depende du code de l'autre. Reutilisee
(jamais dupliquee) pour :
- verifier si une etude (preliminaire ou finale) est lancable ;
- afficher au consultant les champs obligatoires manquants ;
- construire le `RecommendationRequest` transmis au moteur deterministe existant ;
- construire la liste blanche des champs que l'assistant IA (Groq) est autorise a
  extraire d'une description en langage naturel (`app/ai/`) -- le LLM ne peut jamais
  inventer un champ absent de cette liste (voir `app/ai/prompts.py`).

Ajouter un champ ici sans mise a jour du moteur/du calculateur ne changerait rien a la
compatibilite calculee : cette liste ne fait que decrire les champs que le moteur sait
deja consommer (`RecommendationRequest`), pas une liste arbitraire de metadonnees.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequirementFieldDefinition:
    field_name: str  # cle telle qu'utilisee par ExtractedRequirement (cote CPS/IA)
    scope: str
    category: str  # lighting / electrical / geometry
    label: str
    unit: str | None
    required: bool
    numeric: bool
    request_attr: str  # attribut correspondant sur RecommendationRequest


REQUIREMENT_FIELD_DEFINITIONS: tuple[RequirementFieldDefinition, ...] = (
    RequirementFieldDefinition("required_flux_lm", "luminaire", "lighting", "Flux lumineux requis", "lm", True, True, "required_flux_lm"),
    RequirementFieldDefinition("max_power_w", "luminaire", "lighting", "Puissance maximale", "W", True, True, "max_power_w"),
    RequirementFieldDefinition("cct_k", "luminaire", "lighting", "Temperature de couleur (CCT)", "K", True, True, "required_cct_k"),
    RequirementFieldDefinition("voltage_nominal_v", "module", "electrical", "Tension nominale du module", "V", True, True, "voltage_nominal_v"),
    RequirementFieldDefinition("current_nominal_ma", "module", "electrical", "Courant nominal du module", "mA", True, True, "current_nominal_ma"),
    RequirementFieldDefinition("protocol", "driver", "electrical", "Protocole de commande", None, False, False, "protocol"),
    RequirementFieldDefinition("pole_height_m", "road", "geometry", "Hauteur du mat", "m", False, True, "pole_height_m"),
    RequirementFieldDefinition("pole_spacing_m", "road", "geometry", "Espacement des mats", "m", False, True, "pole_spacing_m"),
    RequirementFieldDefinition("road_width_m", "road", "geometry", "Largeur de chaussee", "m", False, True, "road_width_m"),
    RequirementFieldDefinition("road_length_m", "road", "geometry", "Longueur du troncon", "m", False, True, "road_length_m"),
    RequirementFieldDefinition("layout_type", "system", "geometry", "Type d'implantation", None, False, False, "layout_type"),
)

# (scope, field_name) -> definition, pour un lookup direct depuis une ExtractedRequirement
# ou depuis une exigence brute renvoyee par l'assistant IA.
FIELD_DEFINITIONS_BY_KEY: dict[tuple[str, str], RequirementFieldDefinition] = {
    (d.scope, d.field_name): d for d in REQUIREMENT_FIELD_DEFINITIONS
}

MANDATORY_DEFINITIONS: tuple[RequirementFieldDefinition, ...] = tuple(
    d for d in REQUIREMENT_FIELD_DEFINITIONS if d.required
)

# (scope, field_name) -> attribut RecommendationRequest (remplace l'ancien REQUEST_FIELD_MAP local).
REQUEST_FIELD_MAP: dict[tuple[str, str], str] = {k: d.request_attr for k, d in FIELD_DEFINITIONS_BY_KEY.items()}

NUMERIC_REQUEST_ATTRS: set[str] = {d.request_attr for d in REQUIREMENT_FIELD_DEFINITIONS if d.numeric}
MANDATORY_REQUEST_ATTRS: list[str] = [d.request_attr for d in MANDATORY_DEFINITIONS]
MANDATORY_ATTR_LABELS: dict[str, str] = {d.request_attr: d.label for d in MANDATORY_DEFINITIONS}
