"""Tests de la selection manuelle assistee et semi-automatique (configurateur)."""

from app.core.config import get_settings
from app.database.models import SavedConfiguration
from app.services.configuration_validation_service import ConfigurationValidationService
from tests.factories import make_driver, make_lens, make_module, make_requirement

settings = get_settings()


def _requirements_payload(**overrides):
    payload = {
        "required_flux_lm": 6000,
        "max_power_w": 80,
        "required_cct_k": 4000,
        "voltage_nominal_v": 48,
        "current_nominal_ma": 1050,
    }
    payload.update(overrides)
    return payload


# --- Mode manuel : configuration compatible ---

def test_manual_validate_compatible_configuration(client, db_session):
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54, output_power_max_w=150)
    module = make_module(db_session, input_voltage_nominal_v=48, current_nominal_ma=1050, power_nominal_w=50, led_package="3535", led_quantity=32)
    lens = make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={
            "selection_mode": "manual",
            "driver_id": driver.id,
            "module_id": module.id,
            "lens_id": lens.id,
            "project_requirements": _requirements_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_compatible"] is True
    assert body["status"] in {"compatible", "compatible_with_warning", "manual_validation_required"}
    assert body["driver"]["id"] == driver.id
    assert body["module"]["id"] == module.id
    assert body["lens"]["id"] == lens.id
    assert body["scores"]["electrical"] > 0
    criteria_names = {c["criterion"] for c in body["criteria"]}
    assert {"tension", "courant", "puissance", "package_led"}.issubset(criteria_names)


# --- Driver incompatible ---

def test_manual_validate_driver_incompatible(client, db_session):
    driver = make_driver(db_session, output_voltage_min_v=100, output_voltage_max_v=200)
    module = make_module(db_session, input_voltage_nominal_v=48)
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={
            "selection_mode": "manual",
            "driver_id": driver.id,
            "module_id": module.id,
            "project_requirements": _requirements_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_compatible"
    assert body["is_compatible"] is False
    assert any("Tension" in r for r in body["blocking_reasons"])
    tension_criterion = next(c for c in body["criteria"] if c["criterion"] == "tension")
    assert tension_criterion["status"] == "blocking"
    assert len(body["suggestions"]) > 0


# --- Lentille incompatible ---

def test_manual_validate_lens_incompatible(client, db_session):
    module = make_module(db_session, led_package="3535", led_quantity=32)
    lens = make_lens(db_session, compatible_led_package="5050", optical_cells_quantity=32)
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={"selection_mode": "manual", "module_id": module.id, "lens_id": lens.id, "project_requirements": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_compatible"
    assert any("Package LED" in r for r in body["blocking_reasons"])


# --- Donnees manquantes ---

def test_manual_validate_missing_data(client, db_session):
    driver = make_driver(db_session)
    module = make_module(
        db_session,
        luminous_flux_nominal_lm=999999,
        cct_nominal_k=4321,
        input_voltage_nominal_v=None,
        current_nominal_ma=None,
        power_nominal_w=None,
    )
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={"selection_mode": "manual", "driver_id": driver.id, "module_id": module.id, "project_requirements": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "data_incomplete"
    assert body["validated_rules"] == []
    assert len(body["warnings"]) > 0


# --- Selection partielle (module seul) ---

def test_manual_validate_partial_selection_module_only(client, db_session):
    module = make_module(db_session)
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={"selection_mode": "manual", "module_id": module.id, "project_requirements": {}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["driver"] is None
    assert body["lens"] is None
    assert body["module"]["id"] == module.id
    driver_criterion = next(c for c in body["criteria"] if c["criterion"] == "driver")
    assert driver_criterion["status"] == "not_verifiable"


def test_manual_validate_unknown_module_returns_404(client):
    response = client.post(
        "/api/configurator/validate", json={"selection_mode": "manual", "module_id": 999999, "project_requirements": {}}
    )
    assert response.status_code == 404


# --- Mode semi-automatique ---

def test_hybrid_module_fixed_recommends_driver_and_lens(client, db_session):
    module = make_module(db_session, input_voltage_nominal_v=48, current_nominal_ma=1050, power_nominal_w=50, led_package="3535", led_quantity=32)
    make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54, output_power_max_w=150)
    make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    db_session.flush()

    response = client.post(
        "/api/configurator/recommend-missing",
        json={"module_id": module.id, "project_requirements": _requirements_payload(max_power_w=150)},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["module"]["id"] == module.id
    assert body["driver"] is not None
    assert body["lens"] is not None
    assert body["status"] in {"compatible", "compatible_with_warning", "manual_validation_required"}


def test_hybrid_driver_fixed_requires_flux_and_cct(client, db_session):
    driver = make_driver(db_session)
    db_session.flush()

    response = client.post(
        "/api/configurator/recommend-missing",
        json={"driver_id": driver.id, "project_requirements": {}},
    )

    assert response.status_code == 422


def test_hybrid_no_component_fixed_returns_422(client):
    response = client.post("/api/configurator/recommend-missing", json={"project_requirements": {}})
    assert response.status_code == 422


# --- Enregistrement d'une configuration ---

def test_save_configuration(client, db_session):
    driver = make_driver(db_session)
    module = make_module(db_session)
    db_session.flush()

    response = client.post(
        "/api/configurator/save",
        json={
            "selection_mode": "manual",
            "driver_id": driver.id,
            "module_id": module.id,
            "status": "compatible",
            "overall_score": 82.5,
            "validated_rules": ["Tension OK"],
            "warnings": [],
            "blocking_reasons": [],
            "user_comment": "Validee pour le projet X",
            "is_favorite": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["module"]["id"] == module.id
    assert body["driver"]["id"] == driver.id
    assert body["is_favorite"] is True
    assert body["validated_at"] is not None

    saved = db_session.query(SavedConfiguration).filter_by(id=body["id"]).one()
    assert saved.status == "compatible"
    assert saved.user_comment == "Validee pour le projet X"


def test_save_configuration_unknown_module_returns_404(client):
    response = client.post(
        "/api/configurator/save", json={"selection_mode": "manual", "module_id": 999999, "status": "compatible"}
    )
    assert response.status_code == 404


# --- Alternatives ---

def test_manual_validate_returns_alternatives(client, db_session):
    # Tension hors de toute plage reelle (max reel ~342 V) pour isoler le test des 108 drivers deja importes.
    module = make_module(db_session, input_voltage_nominal_v=999, current_nominal_ma=1050, power_nominal_w=50)
    chosen_driver = make_driver(db_session, output_voltage_min_v=900, output_voltage_max_v=1000, output_power_max_w=100)
    alternative_driver = make_driver(db_session, output_voltage_min_v=500, output_voltage_max_v=1500, output_power_max_w=150)
    db_session.flush()

    response = client.post(
        "/api/configurator/validate",
        json={
            "selection_mode": "manual",
            "driver_id": chosen_driver.id,
            "module_id": module.id,
            "project_requirements": _requirements_payload(max_power_w=150),
        },
    )

    assert response.status_code == 200
    body = response.json()
    alternative_ids = {a["driver"]["id"] for a in body["alternatives"] if a["driver"]}
    assert alternative_driver.id in alternative_ids
    assert chosen_driver.id not in alternative_ids


# --- Composants incompatibles identifies dans les listes (desactivation cote frontend) ---

def test_list_configurator_drivers_flags_incompatible_status(client, db_session):
    module = make_module(db_session, input_voltage_nominal_v=48)
    compatible_driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54)
    incompatible_driver = make_driver(db_session, output_voltage_min_v=100, output_voltage_max_v=200)
    db_session.flush()

    response = client.get("/api/configurator/drivers", params={"module_id": module.id, "page_size": 200})

    assert response.status_code == 200
    items = {item["id"]: item["status"] for item in response.json()["items"]}
    assert items[compatible_driver.id] in {"compatible", "compatible_with_warning", "manual_validation_required"}
    assert items[incompatible_driver.id] == "not_compatible"


def test_list_configurator_modules_status_requires_flux_and_cct(client, db_session):
    # flux/CCT hors de toute plage reelle pour isoler le test des 209 modules deja importes.
    module = make_module(db_session, luminous_flux_nominal_lm=999999, cct_nominal_k=4321)
    db_session.flush()

    without_context = client.get(
        "/api/configurator/modules", params={"search": module.reference, "page_size": 5}
    )
    assert without_context.status_code == 200
    items = without_context.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] is None

    with_context = client.get(
        "/api/configurator/modules",
        params={"search": module.reference, "page_size": 5, "required_flux_lm": 999999, "required_cct_k": 4321},
    )
    assert with_context.status_code == 200
    items = with_context.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "compatible"


def test_configurator_options_endpoint(client, db_session):
    make_driver(db_session)
    db_session.flush()

    response = client.get("/api/configurator/options")

    assert response.status_code == 200
    body = response.json()
    assert {m["value"] for m in body["selection_modes"]} == {"automatic", "manual", "hybrid"}
    assert body["counts"]["drivers"] >= 1


# --- Reutilisation du meme moteur de regles ---

def test_configurator_reuses_same_validation_service_as_direct_call(db_session):
    """Verifie que le service partage donne EXACTEMENT le meme resultat qu'un appel direct :
    prouve qu'aucune logique de compatibilite n'est dupliquee entre les modes."""
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54)
    module = make_module(db_session, input_voltage_nominal_v=48)
    requirement = make_requirement(required_flux_lm=6000, required_cct_k=4000)

    service = ConfigurationValidationService()
    direct_result = service.evaluate(driver, module, None, requirement, settings, skip_explanation=True)

    from app.services.manual_configuration_service import ManualConfigurationService

    manual_result = ManualConfigurationService().validate(driver, module, None, requirement, settings)

    assert direct_result.status in {"compatible", "compatible_with_warning", "manual_validation_required"}
    assert direct_result.status == manual_result.status
    assert direct_result.validated_rules == manual_result.validated_rules
    assert direct_result.scores.overall == manual_result.scores.overall
