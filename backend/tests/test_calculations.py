"""Tests du calculateur technique (V1).

Couvre : exemples numeriques exacts (section 21 du cahier des charges),
cas limites (division par zero, valeurs negatives/nulles, donnees
manquantes, tres grandes valeurs, profil dimming invalide), et une
verification de non-regression confirmant que le refactor DRY de
`driver_module_matcher.py` (reutilisation de `calculate_power_margin_percent`)
ne modifie ni le statut ni le message produits par le moteur existant.
"""

import math

import pytest

from app.calculations import electrical, energy, geometry, photometric, thermal
from app.calculations.models import CalculationInput, DimmingProfileEntry
from app.calculations.service import CalculationService
from app.core.config import get_settings
from app.services.driver_module_matcher import evaluate_driver_for_module
from tests.factories import make_driver, make_module, make_requirement

settings = get_settings()


# --- A. Puissance electrique du module ---


def test_module_power_w_exact_example():
    assert electrical.calculate_module_power_w(48, 700) == pytest.approx(33.6)


def test_module_power_w_missing_inputs_returns_none():
    assert electrical.calculate_module_power_w(None, 700) is None
    assert electrical.calculate_module_power_w(48, None) is None
    assert electrical.calculate_module_power_w(None, None) is None


def test_power_consistency_diff_percent():
    assert electrical.calculate_power_consistency_diff_percent(33.6, 32) == pytest.approx(5.0, rel=1e-3)
    assert electrical.calculate_power_consistency_diff_percent(33.6, None) is None
    assert electrical.calculate_power_consistency_diff_percent(33.6, 0) is None  # division par zero -> None


# --- B. Puissance minimale requise du driver (reutilise settings.safety_factor) ---


def test_driver_required_power_w_uses_safety_factor():
    assert electrical.calculate_driver_required_power_w(80, 1.20) == pytest.approx(96.0)


def test_driver_required_power_w_missing_module_power():
    assert electrical.calculate_driver_required_power_w(None, 1.20) is None


# --- C. Taux de charge du driver ---


def test_driver_loading_percent_exact_example():
    assert electrical.calculate_driver_loading_percent(80, 100) == pytest.approx(80.0)


def test_driver_loading_percent_zero_driver_power_returns_none():
    assert electrical.calculate_driver_loading_percent(80, 0) is None


# --- D. Marge de puissance du driver ---


def test_power_margin_percent_exact_example():
    assert electrical.calculate_power_margin_percent(100, 80) == pytest.approx(25.0)


def test_power_margin_percent_zero_and_negative():
    assert electrical.calculate_power_margin_percent(100, 0) is None
    assert electrical.calculate_power_margin_percent(50, 100) == pytest.approx(-50.0)  # marge negative : legitime


# --- E. Efficacite lumineuse ---


def test_luminous_efficacy_exact_example():
    assert photometric.calculate_luminous_efficacy_lm_w(15000, 100) == pytest.approx(150.0)


def test_luminous_efficacy_missing_power():
    assert photometric.calculate_luminous_efficacy_lm_w(15000, None) is None
    assert photometric.calculate_luminous_efficacy_lm_w(15000, 0) is None


# --- F. Ratio espacement / hauteur ---


def test_spacing_height_ratio_exact_example():
    assert geometry.calculate_spacing_height_ratio(30, 10) == pytest.approx(3.0)


def test_spacing_height_ratio_zero_height():
    assert geometry.calculate_spacing_height_ratio(30, 0) is None


# --- G. Surface routiere elementaire ---


def test_road_segment_area_exact_example():
    assert geometry.calculate_road_segment_area_m2(7, 30) == pytest.approx(210.0)


def test_road_segment_area_missing_width():
    assert geometry.calculate_road_segment_area_m2(None, 30) is None


# --- H. Marge thermique ---


def test_thermal_margin_exact_example():
    assert thermal.calculate_thermal_margin_c(60, 45) == pytest.approx(15.0)


def test_thermal_margin_can_be_negative():
    # Une marge negative est un signal legitime (le moteur bloque deja ce cas ailleurs) :
    # le calculateur ne doit pas masquer l'information en la forcant a 0.
    assert thermal.calculate_thermal_margin_c(40, 45) == pytest.approx(-5.0)


def test_thermal_margin_missing_data_returns_none():
    assert thermal.calculate_thermal_margin_c(None, 45) is None


# --- I. Nombre estimatif de luminaires ---


def test_estimate_luminaire_count_unilateral():
    count = geometry.estimate_luminaire_count(1000, 30, "unilateral")
    assert count == math.ceil(1000 / 30) + 1


def test_estimate_luminaire_count_opposite_doubles():
    unilateral = geometry.estimate_luminaire_count(1000, 30, "unilateral")
    opposite = geometry.estimate_luminaire_count(1000, 30, "opposite")
    assert opposite == 2 * unilateral


def test_estimate_luminaire_count_zero_spacing_returns_none():
    assert geometry.estimate_luminaire_count(1000, 0, "unilateral") is None


# --- J-K. Puissance totale installee / consommation annuelle ---


def test_total_installed_power_kw():
    assert energy.calculate_total_installed_power_kw(50, 100) == pytest.approx(5.0)


def test_annual_energy_kwh():
    assert energy.calculate_annual_energy_kwh(50, 100, 4000) == pytest.approx(20000.0)


def test_annual_energy_kwh_missing_hours_returns_none():
    assert energy.calculate_annual_energy_kwh(50, 100, None) is None


# --- L. Consommation avec profil de dimming ---


def test_daily_energy_with_dimming_profile():
    profile = [
        DimmingProfileEntry(duration_hours=4, level_percent=100),
        DimmingProfileEntry(duration_hours=2, level_percent=80),
        DimmingProfileEntry(duration_hours=5, level_percent=50),
    ]
    # (100*1*4 + 100*0.8*2 + 100*0.5*5) / 1000 = (400 + 160 + 250) / 1000
    daily = energy.calculate_daily_energy_with_dimming_kwh(100, profile, number_of_luminaires=1)
    assert daily == pytest.approx(0.81)


def test_dimming_profile_exceeding_24h_is_invalid():
    profile = [DimmingProfileEntry(duration_hours=20, level_percent=100), DimmingProfileEntry(duration_hours=10, level_percent=50)]
    assert energy.calculate_daily_energy_with_dimming_kwh(100, profile) is None


def test_dimming_profile_empty_returns_none():
    assert energy.calculate_daily_energy_with_dimming_kwh(100, None) is None
    assert energy.calculate_daily_energy_with_dimming_kwh(100, []) is None


def test_annual_energy_with_dimming_multiplies_by_365():
    assert energy.calculate_annual_energy_with_dimming_kwh(1.0) == pytest.approx(365.0)


# --- M. Economie energetique ---


def test_energy_saving_percent():
    assert energy.calculate_energy_saving_percent(8000, 10000) == pytest.approx(20.0)


def test_energy_saved_kwh():
    assert energy.calculate_energy_saved_kwh(8000, 10000) == pytest.approx(2000.0)


def test_energy_saving_missing_reference_returns_none():
    assert energy.calculate_energy_saving_percent(8000, None) is None


# --- N. Cout energetique (jamais un tarif invente) ---


def test_annual_energy_cost():
    assert energy.calculate_annual_energy_cost(20000, 1.2) == pytest.approx(24000.0)


def test_annual_energy_cost_without_price_returns_none():
    assert energy.calculate_annual_energy_cost(20000, None) is None


# --- Tres grandes valeurs (pas d'overflow / comportement lineaire attendu) ---


def test_large_values_do_not_break_calculations():
    huge_flux = 5_000_000_000
    result = photometric.calculate_luminous_efficacy_lm_w(huge_flux, 100)
    assert result == pytest.approx(huge_flux / 100)


# --- Service : preview() gere les donnees manquantes sans jamais inventer de zero ---


def test_service_preview_reports_not_calculable_without_inventing_zero():
    result = CalculationService().preview(CalculationInput())
    assert result.electrical.module_power_w.status == "not_calculable"
    assert result.electrical.module_power_w.value is None
    assert "manquant" in result.electrical.module_power_w.warning.lower()


def test_service_preview_computes_electrical_and_geometry_together():
    data = CalculationInput(
        module_voltage_v=48,
        module_current_ma=700,
        required_flux_lm=15000,
        road_width_m=7,
        pole_height_m=10,
        pole_spacing_m=30,
        ambient_temperature_c=40,
    )
    result = CalculationService().preview(data)

    assert result.electrical.module_power_w.value == pytest.approx(33.6)
    assert result.electrical.module_power_w.status == "calculated"
    assert result.geometry.spacing_height_ratio.value == pytest.approx(3.0)
    assert result.geometry.road_segment_area_m2.value == pytest.approx(210.0)
    # Aucun driver fourni : charge/marge non calculables, jamais 0.
    assert result.electrical.driver_loading_percent.status == "not_calculable"
    assert result.electrical.driver_loading_percent.value is None


def test_service_estimate_flags_are_set_on_estimative_values():
    data = CalculationInput(road_length_m=1000, pole_spacing_m=30, layout_type="unilateral")
    result = CalculationService().preview(data)
    assert result.geometry.estimated_luminaire_count.is_estimate is True
    assert "pre-dimensionnement" in result.geometry.estimated_luminaire_count.warning.lower()


def test_service_for_configuration_uses_real_product_data(db_session):
    driver = make_driver(db_session, output_power_max_w=120, ambient_temperature_max_c=60)
    module = make_module(
        db_session,
        input_voltage_nominal_v=48,
        current_nominal_ma=700,
        power_nominal_w=33.6,
        luminous_flux_nominal_lm=6000,
    )
    requirement = make_requirement(ambient_temperature_c=40, pole_height_m=10, pole_spacing_m=30)

    result = CalculationService().for_configuration(requirement, driver, module, None)

    assert result.electrical.module_power_w.value == pytest.approx(33.6)
    assert result.electrical.driver_power_margin_percent.value == pytest.approx(
        (120 / 33.6 - 1) * 100, rel=1e-3
    )
    assert result.thermal.driver_thermal_margin_c.value == pytest.approx(20.0)
    assert result.geometry.spacing_height_ratio.value == pytest.approx(3.0)


# --- Non-regression : le refactor DRY (driver_module_matcher -> calculate_power_margin_percent)
# ne change ni le statut, ni le message, ni les regles bloquantes du moteur existant. ---


def test_driver_module_matcher_power_margin_unchanged(db_session):
    driver = make_driver(db_session, output_power_max_w=100)
    module = make_module(db_session, power_nominal_w=80)
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is True
    assert any("Marge de puissance de 25%" in r for r in result.validated_rules)


def test_driver_module_matcher_blocks_when_margin_insufficient(db_session):
    driver = make_driver(db_session, output_power_max_w=52)
    module = make_module(db_session, power_nominal_w=50)  # 50 * 1.10 = 55 > 52
    req = make_requirement()

    result = evaluate_driver_for_module(driver, module, req, settings)

    assert result.is_compatible is False
    assert any("Puissance" in r for r in result.blocking_reasons)
