"""Tests du moteur de compatibilite / scoring / recommandation (section 17, scenarios 1-16)."""

from app.core.config import get_settings
from app.database.models import RecommendationResult
from app.services.candidate_selection import select_candidate_modules
from app.services.driver_module_matcher import evaluate_driver_for_module
from app.services.module_lens_matcher import evaluate_lens_for_module
from app.services.recommendation_engine import run_recommendation
from tests.factories import make_driver, make_lens, make_module, make_requirement

settings = get_settings()


# --- 1-3 : tension ---

def test_scenario_01_tension_compatible(db_session):
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54)
    module = make_module(db_session, input_voltage_nominal_v=48)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is True
    assert any("Tension" in r for r in result.validated_rules)


def test_scenario_02_tension_module_trop_elevee(db_session):
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54)
    module = make_module(db_session, input_voltage_nominal_v=60)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("Tension" in r for r in result.blocking_reasons)


def test_scenario_03_tension_module_trop_faible(db_session):
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54)
    module = make_module(db_session, input_voltage_nominal_v=20)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("Tension" in r for r in result.blocking_reasons)


# --- 4-5 : courant ---

def test_scenario_04_courant_compatible(db_session):
    driver = make_driver(db_session, output_current_min_ma=700, output_current_max_ma=1050)
    module = make_module(db_session, current_nominal_ma=900)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is True
    assert any("Courant" in r for r in result.validated_rules)


def test_scenario_05_courant_incompatible(db_session):
    driver = make_driver(db_session, output_current_min_ma=700, output_current_max_ma=1050)
    module = make_module(db_session, current_nominal_ma=1500)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("Courant" in r for r in result.blocking_reasons)


# --- 6 : marge de puissance insuffisante ---

def test_scenario_06_puissance_sans_marge_suffisante(db_session):
    driver = make_driver(db_session, output_power_max_w=52)
    module = make_module(db_session, power_nominal_w=50)  # 50 * 1.10 = 55 > 52
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("Puissance" in r for r in result.blocking_reasons)


# --- 7 : protocole non supporte ---

def test_scenario_07_protocole_non_supporte(db_session):
    driver = make_driver(db_session, d4i=False, dali_2=False)
    module = make_module(db_session)
    req = make_requirement(protocol="D4i")

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("protocole" in r.lower() for r in result.blocking_reasons)


# --- 8-9 : CCT ---

def test_scenario_08_module_bonne_cct(db_session):
    make_module(db_session, cct_nominal_k=4000, luminous_flux_nominal_lm=6000)
    req = make_requirement(required_cct_k=4000, required_flux_lm=6000)

    candidates = select_candidate_modules(db_session, req, settings)

    assert any(m.cct_nominal_k == 4000 for m in candidates)


def test_scenario_09_module_mauvaise_cct(db_session):
    module = make_module(db_session, cct_nominal_k=3000, luminous_flux_nominal_lm=6000, cct_options=None)
    req = make_requirement(required_cct_k=4000, required_flux_lm=6000)

    candidates = select_candidate_modules(db_session, req, settings)

    assert module.id not in [m.id for m in candidates]


# --- 10-11 : compatibilite lentille ---

def test_scenario_10_package_led_compatible_avec_lentille(db_session):
    module = make_module(db_session, led_package="3535")
    lens = make_lens(db_session, compatible_led_package="2835,3030,3535")
    req = make_requirement()

    result = evaluate_lens_for_module(lens, module, req, settings)

    assert result.is_compatible is True
    assert any("Package LED" in r for r in result.validated_rules)


def test_scenario_11_nombre_de_leds_incompatible(db_session):
    module = make_module(db_session, led_package="3535", led_quantity=32)
    lens = make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=16)
    req = make_requirement()

    result = evaluate_lens_for_module(lens, module, req, settings)

    assert result.is_compatible is False
    assert any("cellules" in r.lower() for r in result.blocking_reasons)


# --- 13 : lentille sans fichier IES ---

def test_scenario_13_lentille_sans_fichier_ies(db_session):
    module = make_module(db_session, led_package="3535")
    lens = make_lens(db_session, compatible_led_package="3535", ies_file_available=False, ldt_file_available=False)
    req = make_requirement()

    result = evaluate_lens_for_module(lens, module, req, settings)

    assert result.is_compatible is True  # non bloquant
    assert any("IES/LDT" in w for w in result.warnings)


# --- 14 : donnees incompletes ---

def test_scenario_14_donnees_incompletes(db_session):
    # flux/CCT/package hors de toute plage plausible des donnees reelles deja importees en base,
    # pour garantir qu'aucun driver/module/lentille reel n'interfere avec ce scenario synthetique.
    make_driver(db_session, ambient_temperature_max_c=None)
    make_module(
        db_session,
        luminous_flux_nominal_lm=999999,
        cct_nominal_k=4321,
        led_package="TESTPKG_UNIQUE",
        led_quantity=None,
        input_voltage_nominal_v=None,
        current_nominal_ma=None,
        power_nominal_w=None,
    )
    req = make_requirement(db_session, persist=True, required_flux_lm=999999, required_cct_k=4321)

    run = run_recommendation(db_session, req)

    assert run.status == "data_incomplete"


# --- 15 : aucune configuration disponible ---

def test_scenario_15_aucune_configuration_disponible(db_session):
    make_module(db_session, luminous_flux_nominal_lm=500, cct_nominal_k=2700)
    req = make_requirement(db_session, persist=True, required_flux_lm=50000, required_cct_k=6500)

    run = run_recommendation(db_session, req)

    assert run.status == "impossible"
    assert len(run.blocking_reasons) > 0


# --- 16 : plusieurs configurations avec classement ---

def test_scenario_16_plusieurs_configurations_classees(db_session):
    module = make_module(db_session, luminous_flux_nominal_lm=6000, cct_nominal_k=4000, power_nominal_w=50, led_package="3535")
    make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    make_driver(db_session, output_power_max_w=60)  # marge faible
    make_driver(db_session, output_power_max_w=150)  # marge large -> meilleur score electrique
    req = make_requirement(db_session, persist=True, required_flux_lm=6000, required_cct_k=4000, max_power_w=60)

    run = run_recommendation(db_session, req)

    results = (
        db_session.query(RecommendationResult)
        .filter_by(run_id=run.id)
        .order_by(RecommendationResult.rank)
        .all()
    )

    assert len(results) >= 2
    assert results[0].rank == 1
    assert results[0].overall_score >= results[1].overall_score
