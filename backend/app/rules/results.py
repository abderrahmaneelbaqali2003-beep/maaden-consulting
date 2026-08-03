"""Structures de resultat partagees par les matchers de compatibilite."""

from dataclasses import dataclass, field


@dataclass
class RuleOutcome:
    rule_name: str
    passed: bool
    severity: str  # blocking / warning
    message: str


@dataclass
class CriterionResult:
    """Une ligne de la matrice de validation affichee au consultant (ex: 'Tension')."""

    criterion: str  # cle stable : tension / courant / puissance / protocole / thermique_driver /
    #                 package_led / disposition_led / photometrie / distribution / thermique_lentille
    label: str  # libelle FR affiche ("Tension", "Courant", ...)
    status: str  # valid / warning / blocking / not_verifiable
    detail: str


@dataclass
class MatchEvaluation:
    is_compatible: bool
    validated_rules: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    criteria: list[CriterionResult] = field(default_factory=list)
