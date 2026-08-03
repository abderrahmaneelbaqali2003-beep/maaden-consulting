from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import Settings, get_settings
from app.database.models import Driver, LedModule, Lens, Manufacturer, ProjectRequirement, SavedConfiguration
from app.repositories.driver_repository import list_drivers
from app.repositories.lens_repository import list_lenses
from app.repositories.module_repository import list_modules
from app.rules.results import CriterionResult
from app.schemas.common import PaginatedResponse
from app.schemas.configurator import (
    AlternativeConfigurationOut,
    ConfiguratorOptionItem,
    ConfiguratorOptionsResponse,
    ConfiguratorResultResponse,
    CriterionOut,
    PartialRequirements,
    RecommendMissingRequest,
    SaveConfigurationRequest,
    SavedConfigurationRead,
    ValidateConfigurationRequest,
)
from app.schemas.recommendation import ComponentRef, ScoresOut
from app.services.configuration_validation_service import ConfigurationEvaluation, ConfigurationValidationService
from app.services.hybrid_configuration_service import HybridConfigurationService, MissingRequirementFieldsError
from app.services.manual_configuration_service import AlternativeConfiguration, ManualConfigurationService

router = APIRouter(prefix="/api/configurator", tags=["configurator"])

SELECTION_MODES = [
    {"value": "automatic", "label": "Recommandation automatique"},
    {"value": "manual", "label": "Selection manuelle assistee"},
    {"value": "hybrid", "label": "Selection semi-automatique"},
]

PROTOCOLS = ["DALI", "DALI-2", "D4i", "0-10V", "1-10V"]


# --- Helpers ---------------------------------------------------------------


def _component_ref(entity) -> ComponentRef | None:
    if entity is None:
        return None
    return ComponentRef(id=entity.id, manufacturer=entity.manufacturer.name, reference=entity.reference)


def _requirement_from_partial(payload: PartialRequirements) -> ProjectRequirement:
    """Construit un ProjectRequirement TRANSITOIRE (jamais flush/commit) pour l'evaluation.
    Les contraintes NOT NULL du modele ne s'appliquent qu'a la persistance : un objet
    transitoire avec des champs None est parfaitement utilisable par le moteur de regles."""
    return ProjectRequirement(**payload.model_dump())


def _criteria_out(criteria: list[CriterionResult]) -> list[CriterionOut]:
    return [CriterionOut(criterion=c.criterion, label=c.label, status=c.status, detail=c.detail) for c in criteria]


def _scores_out(evaluation: ConfigurationEvaluation) -> ScoresOut:
    s = evaluation.scores
    return ScoresOut(
        electrical=s.electrical, photometric=s.photometric, mechanical=s.mechanical,
        thermal=s.thermal, data_quality=s.data_quality,
    )


def _alternatives_out(alternatives: list[AlternativeConfiguration]) -> list[AlternativeConfigurationOut]:
    out = []
    for alt in alternatives:
        out.append(
            AlternativeConfigurationOut(
                driver=_component_ref(alt.driver),
                module=_component_ref(alt.module),
                lens=_component_ref(alt.lens),
                status=alt.evaluation.status,
                overall_score=alt.evaluation.scores.overall,
                scores=_scores_out(alt.evaluation),
                warnings=alt.evaluation.warnings,
            )
        )
    return out


def _build_suggestions(evaluation: ConfigurationEvaluation) -> list[str]:
    if evaluation.is_compatible:
        return []
    suggestions = ["Choisir une autre reference pour le(s) composant(s) en cause (voir les alternatives)."]
    if any("Tension" in r for r in evaluation.blocking_reasons):
        suggestions.append("Choisir un driver dont la plage de tension couvre celle du module.")
    if any("Courant" in r for r in evaluation.blocking_reasons):
        suggestions.append("Choisir un driver dont la plage de courant couvre celle du module.")
    if any("Puissance" in r for r in evaluation.blocking_reasons):
        suggestions.append("Choisir un driver de puissance maximale superieure, ou reduire la marge de securite.")
    if any("protocole" in r.lower() for r in evaluation.blocking_reasons):
        suggestions.append("Choisir un driver supportant le protocole demande.")
    if any("Package LED" in r for r in evaluation.blocking_reasons):
        suggestions.append("Choisir une lentille compatible avec le package LED du module.")
    if any("cellules" in r.lower() for r in evaluation.blocking_reasons):
        suggestions.append("Choisir une lentille dont le nombre de cellules optiques correspond au nombre de LED du module.")
    return suggestions


def _driver_key_specs(driver: Driver) -> dict:
    return {
        "voltage_range_v": f"{driver.output_voltage_min_v}-{driver.output_voltage_max_v}",
        "current_range_ma": (
            f"{driver.output_current_min_ma}-{driver.output_current_max_ma}"
            if driver.output_current_min_ma is not None and driver.output_current_max_ma is not None
            else None
        ),
        "power_max_w": driver.output_power_max_w,
        "protocols": [
            p
            for p, flag in [("DALI-2", driver.dali_2), ("D4i", driver.d4i), ("0-10V", driver.dimming_0_10v), ("1-10V", driver.dimming_1_10v)]
            if flag
        ],
    }


def _module_key_specs(module: LedModule) -> dict:
    return {
        "flux_lm": module.luminous_flux_nominal_lm,
        "cct_k": module.cct_nominal_k,
        "power_w": module.power_nominal_w,
        "led_package": module.led_package,
        "voltage_v": module.input_voltage_nominal_v,
        "current_ma": module.current_nominal_ma,
    }


def _lens_key_specs(lens: Lens) -> dict:
    return {
        "compatible_led_package": lens.compatible_led_package,
        "distribution": lens.iesna_distribution_type,
        "ies_or_ldt_available": lens.ies_file_available or lens.ldt_file_available,
        "optical_cells_quantity": lens.optical_cells_quantity,
    }


def _module_matches_requirement(module: LedModule, requirement: PartialRequirements, settings: Settings) -> str | None:
    """Statut intrinseque d'un module (sans driver/lentille) par rapport au flux/CCT/puissance
    demandes. Retourne None si le contexte est insuffisant pour se prononcer."""
    if requirement.required_flux_lm is None or requirement.required_cct_k is None:
        return None

    flux_min = requirement.required_flux_lm * settings.flux_tolerance_min
    flux_max = requirement.required_flux_lm * settings.flux_tolerance_max
    flux_ok = flux_min <= module.luminous_flux_nominal_lm <= flux_max

    cct_ok = module.cct_nominal_k == requirement.required_cct_k
    if not cct_ok and module.cct_options:
        options = {opt.strip() for opt in str(module.cct_options).split(",") if opt.strip()}
        cct_ok = str(requirement.required_cct_k) in options

    power_ok = (
        requirement.max_power_w is None or module.power_nominal_w is None or module.power_nominal_w <= requirement.max_power_w
    )

    if flux_ok and cct_ok and power_ok:
        return "compatible"
    return "not_compatible"


def _fetch_entity_or_404(db: Session, model, entity_id: int | None, label: str):
    if entity_id is None:
        return None
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail=f"{label} introuvable (id={entity_id}).")
    return entity


# --- Endpoints ---------------------------------------------------------------


@router.get("/options", response_model=ConfiguratorOptionsResponse)
def get_configurator_options(db: Session = Depends(get_db)):
    def _manufacturer_names(model) -> list[str]:
        rows = (
            db.query(Manufacturer.name)
            .join(model, model.manufacturer_id == Manufacturer.id)
            .filter(model.is_active.is_(True))
            .distinct()
            .order_by(Manufacturer.name)
            .all()
        )
        return [r[0] for r in rows]

    return ConfiguratorOptionsResponse(
        selection_modes=SELECTION_MODES,
        protocols=PROTOCOLS,
        manufacturers={
            "drivers": _manufacturer_names(Driver),
            "modules": _manufacturer_names(LedModule),
            "lenses": _manufacturer_names(Lens),
        },
        counts={
            "drivers": db.query(Driver).filter(Driver.is_active.is_(True)).count(),
            "modules": db.query(LedModule).filter(LedModule.is_active.is_(True)).count(),
            "lenses": db.query(Lens).filter(Lens.is_active.is_(True)).count(),
        },
    )


@router.get("/modules", response_model=PaginatedResponse[ConfiguratorOptionItem])
def list_configurator_modules(
    db: Session = Depends(get_db),
    search: str | None = Query(None),
    manufacturer: str | None = Query(None),
    led_package: str | None = Query(None),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    required_flux_lm: float | None = Query(None, gt=0),
    max_power_w: float | None = Query(None, gt=0),
    required_cct_k: int | None = Query(None, gt=0),
):
    items, total, total_pages = list_modules(
        db, search=search, manufacturer=manufacturer, led_package=led_package,
        include_inactive=include_inactive, page=page, page_size=page_size,
    )
    settings = get_settings()
    requirement = PartialRequirements(required_flux_lm=required_flux_lm, max_power_w=max_power_w, required_cct_k=required_cct_k)

    out = [
        ConfiguratorOptionItem(
            id=m.id, external_ref=m.external_ref, manufacturer=m.manufacturer.name, reference=m.reference,
            product_family=m.product_family, key_specs=_module_key_specs(m),
            status=_module_matches_requirement(m, requirement, settings), is_active=m.is_active,
        )
        for m in items
    ]
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/drivers", response_model=PaginatedResponse[ConfiguratorOptionItem])
def list_configurator_drivers(
    module_id: int = Query(...),
    db: Session = Depends(get_db),
    search: str | None = Query(None),
    manufacturer: str | None = Query(None),
    protocol: str | None = Query(None),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    ambient_temperature_c: float | None = Query(None),
):
    module = _fetch_entity_or_404(db, LedModule, module_id, "Module")
    items, total, total_pages = list_drivers(
        db, search=search, manufacturer=manufacturer, protocol=protocol,
        include_inactive=include_inactive, page=page, page_size=page_size,
    )
    settings = get_settings()
    requirement = _requirement_from_partial(PartialRequirements(ambient_temperature_c=ambient_temperature_c))
    service = ConfigurationValidationService()

    out = []
    for d in items:
        evaluation = service.evaluate(d, module, None, requirement, settings, skip_explanation=True)
        out.append(
            ConfiguratorOptionItem(
                id=d.id, external_ref=d.external_ref, manufacturer=d.manufacturer.name, reference=d.reference,
                product_family=d.product_family, key_specs=_driver_key_specs(d),
                status=evaluation.status, is_active=d.is_active,
            )
        )
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/lenses", response_model=PaginatedResponse[ConfiguratorOptionItem])
def list_configurator_lenses(
    module_id: int = Query(...),
    db: Session = Depends(get_db),
    search: str | None = Query(None),
    manufacturer: str | None = Query(None),
    led_package: str | None = Query(None),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    module = _fetch_entity_or_404(db, LedModule, module_id, "Module")
    items, total, total_pages = list_lenses(
        db, search=search, manufacturer=manufacturer, led_package=led_package,
        include_inactive=include_inactive, page=page, page_size=page_size,
    )
    settings = get_settings()
    requirement = _requirement_from_partial(PartialRequirements())
    service = ConfigurationValidationService()

    out = []
    for lens in items:
        evaluation = service.evaluate(None, module, lens, requirement, settings, skip_explanation=True)
        out.append(
            ConfiguratorOptionItem(
                id=lens.id, external_ref=lens.external_ref, manufacturer=lens.manufacturer.name, reference=lens.reference,
                product_family=lens.product_family, key_specs=_lens_key_specs(lens),
                status=evaluation.status, is_active=lens.is_active,
            )
        )
    return PaginatedResponse(items=out, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.post("/validate", response_model=ConfiguratorResultResponse)
def validate_configuration(payload: ValidateConfigurationRequest, db: Session = Depends(get_db)):
    module = _fetch_entity_or_404(db, LedModule, payload.module_id, "Module")
    driver = _fetch_entity_or_404(db, Driver, payload.driver_id, "Driver")
    lens = _fetch_entity_or_404(db, Lens, payload.lens_id, "Lentille")

    settings = get_settings()
    requirement = _requirement_from_partial(payload.project_requirements)

    manual_service = ManualConfigurationService()
    evaluation = manual_service.validate(driver, module, lens, requirement, settings)
    alternatives = manual_service.find_alternatives(
        db, module, requirement, settings,
        exclude_driver_id=driver.id if driver else None, exclude_lens_id=lens.id if lens else None,
    )

    return ConfiguratorResultResponse(
        selection_mode=payload.selection_mode,
        status=evaluation.status,
        is_compatible=evaluation.is_compatible,
        needs_manual_validation=evaluation.needs_manual_validation,
        driver=_component_ref(driver),
        module=_component_ref(module),
        lens=_component_ref(lens),
        scores=_scores_out(evaluation),
        validated_rules=evaluation.validated_rules,
        warnings=evaluation.warnings,
        blocking_reasons=evaluation.blocking_reasons,
        criteria=_criteria_out(evaluation.criteria),
        explanation=evaluation.explanation,
        suggestions=_build_suggestions(evaluation),
        alternatives=_alternatives_out(alternatives),
    )


@router.post("/recommend-missing", response_model=ConfiguratorResultResponse)
def recommend_missing(payload: RecommendMissingRequest, db: Session = Depends(get_db)):
    if payload.driver_id is None and payload.module_id is None and payload.lens_id is None:
        raise HTTPException(
            status_code=422, detail="Le mode semi-automatique necessite au moins un composant impose (driver, module ou lentille)."
        )

    fixed_driver = _fetch_entity_or_404(db, Driver, payload.driver_id, "Driver")
    fixed_module = _fetch_entity_or_404(db, LedModule, payload.module_id, "Module")
    fixed_lens = _fetch_entity_or_404(db, Lens, payload.lens_id, "Lentille")

    settings = get_settings()
    requirement = _requirement_from_partial(payload.project_requirements)

    try:
        result = HybridConfigurationService().recommend_missing(
            db, requirement, settings, fixed_driver=fixed_driver, fixed_module=fixed_module, fixed_lens=fixed_lens
        )
    except MissingRequirementFieldsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result.best is None:
        return ConfiguratorResultResponse(
            selection_mode="hybrid",
            status="impossible",
            is_compatible=False,
            needs_manual_validation=False,
            driver=_component_ref(fixed_driver),
            module=_component_ref(fixed_module),
            lens=_component_ref(fixed_lens),
            scores=None,
            validated_rules=[],
            warnings=[],
            blocking_reasons=["Aucune combinaison n'a pu etre trouvee pour completer les composants imposes."],
            criteria=[],
            explanation="",
            suggestions=["Assouplir les besoins projet ou choisir un autre composant impose."],
            alternatives=[],
        )

    best = result.best
    return ConfiguratorResultResponse(
        selection_mode="hybrid",
        status=best.evaluation.status,
        is_compatible=best.evaluation.is_compatible,
        needs_manual_validation=best.evaluation.needs_manual_validation,
        driver=_component_ref(best.driver),
        module=_component_ref(best.module),
        lens=_component_ref(best.lens),
        scores=_scores_out(best.evaluation),
        validated_rules=best.evaluation.validated_rules,
        warnings=best.evaluation.warnings,
        blocking_reasons=best.evaluation.blocking_reasons,
        criteria=_criteria_out(best.evaluation.criteria),
        explanation=best.evaluation.explanation,
        suggestions=_build_suggestions(best.evaluation),
        alternatives=_alternatives_out(
            [AlternativeConfiguration(a.driver, a.module, a.lens, a.evaluation) for a in result.alternatives]
        ),
    )


@router.post("/save", response_model=SavedConfigurationRead, status_code=201)
def save_configuration(payload: SaveConfigurationRequest, db: Session = Depends(get_db)):
    module = _fetch_entity_or_404(db, LedModule, payload.module_id, "Module")
    driver = _fetch_entity_or_404(db, Driver, payload.driver_id, "Driver")
    lens = _fetch_entity_or_404(db, Lens, payload.lens_id, "Lentille")

    saved = SavedConfiguration(
        project_id=payload.project_id,
        selection_mode=payload.selection_mode,
        driver_id=driver.id if driver else None,
        module_id=module.id,
        lens_id=lens.id if lens else None,
        status=payload.status,
        overall_score=payload.overall_score,
        validated_rules=payload.validated_rules,
        blocking_reasons=payload.blocking_reasons,
        warnings=payload.warnings,
        user_comment=payload.user_comment,
        is_favorite=payload.is_favorite,
        validated_at=datetime.now(timezone.utc) if payload.status in ("compatible", "compatible_with_warning") else None,
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)

    return SavedConfigurationRead(
        id=saved.id, project_id=saved.project_id, selection_mode=saved.selection_mode,
        driver=_component_ref(driver), module=_component_ref(module), lens=_component_ref(lens),
        status=saved.status, overall_score=saved.overall_score, validated_rules=saved.validated_rules,
        blocking_reasons=saved.blocking_reasons, warnings=saved.warnings, user_comment=saved.user_comment,
        is_favorite=saved.is_favorite, created_at=saved.created_at, updated_at=saved.updated_at,
        validated_at=saved.validated_at,
    )
