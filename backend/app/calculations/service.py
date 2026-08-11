"""Service central du calculateur technique.

`CalculationService` est le seul point d'entree : `preview()` (donnees projet
saisies, aucune donnee produit encore choisie) et `for_configuration()`
(donnees reelles d'une configuration Driver + Module + Lentille retenue).
Les deux methodes convergent vers `_compute()`, qui applique la meme logique
de calcul et le meme arrondi (uniquement a l'affichage) dans les deux cas.

Precision d'affichage (section 20) : puissance/energie/efficacite/temperature
= 1 decimale, pourcentage = 1 decimale, ratio S/H = 2 decimales.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.calculations import electrical, energy, geometry, photometric, thermal
from app.calculations.models import (
    CalculationInput,
    CalculationResult,
    CalculationValue,
    ElectricalCalculationResult,
    EnergyCalculationResult,
    GeometryCalculationResult,
    PhotometricEstimateResult,
    ThermalCalculationResult,
)
from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from app.database.models import Driver, LedModule, Lens, ProjectRequirement


def _r(value: float | None, ndigits: int) -> float | None:
    return None if value is None else round(value, ndigits)


class CalculationService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Points d'entree publics
    # ------------------------------------------------------------------

    def preview(self, data: CalculationInput) -> CalculationResult:
        """Etape 'Calculs techniques' du formulaire Nouveau calcul (aucun produit choisi)."""
        return self._compute(data)

    def for_configuration(
        self,
        requirement: "ProjectRequirement",
        driver: "Driver | None",
        module: "LedModule",
        lens: "Lens | None",
    ) -> CalculationResult:
        """Configuration retenue par le moteur : utilise les donnees produit reelles."""
        data = CalculationInput(
            pole_height_m=requirement.pole_height_m,
            pole_spacing_m=requirement.pole_spacing_m,
            required_flux_lm=module.luminous_flux_nominal_lm,
            module_voltage_v=module.input_voltage_nominal_v,
            module_current_ma=module.current_nominal_ma,
            module_power_nominal_w=module.power_nominal_w,
            driver_power_max_w=driver.output_power_max_w if driver else None,
            driver_max_temperature_c=driver.ambient_temperature_max_c if driver else None,
            lens_max_temperature_c=lens.operating_temperature_max_c if lens else None,
            ambient_temperature_c=requirement.ambient_temperature_c,
        )
        return self._compute(data)

    # ------------------------------------------------------------------
    # Calcul
    # ------------------------------------------------------------------

    def _compute(self, data: CalculationInput) -> CalculationResult:
        warnings: list[str] = []

        elec = self._compute_electrical(data, warnings)
        geo = self._compute_geometry(data)
        therm = self._compute_thermal(data)
        nrg = self._compute_energy(data, elec, geo, warnings)
        photo = self._compute_photometric(data, geo, warnings)

        return CalculationResult(
            electrical=elec, geometry=geo, thermal=therm, energy=nrg, photometric=photo, warnings=warnings
        )

    def _compute_electrical(self, data: CalculationInput, warnings: list[str]) -> ElectricalCalculationResult:
        module_power_w = electrical.calculate_module_power_w(data.module_voltage_v, data.module_current_ma)

        power_value = CalculationValue(
            key="module_power_w",
            label="Puissance module",
            value=_r(module_power_w, 1),
            unit="W",
            status="calculated" if module_power_w is not None else "not_calculable",
            formula="P = V x I(mA) / 1000",
            inputs={"voltage_v": data.module_voltage_v, "current_ma": data.module_current_ma},
            warning=None
            if module_power_w is not None
            else "Puissance electrique non calculable : tension et/ou courant du module manquant(s).",
        )

        consistency = electrical.calculate_power_consistency_diff_percent(module_power_w, data.module_power_nominal_w)
        consistency_warning = None
        if consistency is not None and abs(consistency) >= 10:
            consistency_warning = (
                f"Ecart de {consistency:.1f}% entre la puissance calculee (V x I) et la puissance nominale "
                "fabricant : a verifier (la valeur fabricant n'est jamais remplacee automatiquement)."
            )
            warnings.append(consistency_warning)
        consistency_value = CalculationValue(
            key="module_power_consistency_percent",
            label="Ecart puissance calculee / nominale",
            value=_r(consistency, 1),
            unit="%",
            status="calculated" if consistency is not None else "not_calculable",
            formula="(P_calculee - P_nominale) / P_nominale x 100",
            inputs={"calculated_w": _r(module_power_w, 1), "nominal_w": data.module_power_nominal_w},
            warning=consistency_warning
            or (None if consistency is not None else "Puissance nominale fabricant non fournie : comparaison impossible."),
        )

        required_power = electrical.calculate_driver_required_power_w(module_power_w, self.settings.safety_factor)
        required_value = CalculationValue(
            key="driver_required_power_w",
            label="Puissance driver requise",
            value=_r(required_power, 1),
            unit="W",
            status="calculated" if required_power is not None else "not_calculable",
            formula="P_driver_required = P_module x safety_factor",
            inputs={"module_power_w": _r(module_power_w, 1), "safety_factor": self.settings.safety_factor},
            warning=None if required_power is not None else "Puissance module non calculable : marge driver requise indisponible.",
        )

        loading = electrical.calculate_driver_loading_percent(module_power_w, data.driver_power_max_w)
        loading_value = CalculationValue(
            key="driver_loading_percent",
            label="Charge driver",
            value=_r(loading, 1),
            unit="%",
            status="calculated" if loading is not None else "not_calculable",
            formula="driver_loading_percent = P_module / P_driver_max x 100",
            inputs={"module_power_w": _r(module_power_w, 1), "driver_power_max_w": data.driver_power_max_w},
            warning=None if loading is not None else "Puissance module ou puissance max. driver manquante : charge non calculable.",
        )

        margin = electrical.calculate_power_margin_percent(data.driver_power_max_w, module_power_w)
        margin_value = CalculationValue(
            key="driver_power_margin_percent",
            label="Marge driver",
            value=_r(margin, 1),
            unit="%",
            status="calculated" if margin is not None else "not_calculable",
            formula="power_margin_percent = (P_driver_max / P_module - 1) x 100",
            inputs={"driver_power_max_w": data.driver_power_max_w, "module_power_w": _r(module_power_w, 1)},
            warning=None if margin is not None else "Puissance module ou puissance max. driver manquante : marge non calculable.",
        )

        efficacy = photometric.calculate_luminous_efficacy_lm_w(data.required_flux_lm, module_power_w)
        efficacy_value = CalculationValue(
            key="luminous_efficacy_lm_w",
            label="Efficacite lumineuse",
            value=_r(efficacy, 1),
            unit="lm/W",
            status="calculated" if efficacy is not None else "not_calculable",
            formula="efficacy_lm_per_w = flux_lm / power_w",
            inputs={"flux_lm": data.required_flux_lm, "power_w": _r(module_power_w, 1)},
            is_estimate=False,
            warning=(
                None
                if efficacy is not None
                else "Flux lumineux ou puissance module manquant(e) : efficacite non calculable."
            ),
        )

        return ElectricalCalculationResult(
            module_power_w=power_value,
            module_power_consistency_percent=consistency_value,
            driver_required_power_w=required_value,
            driver_loading_percent=loading_value,
            driver_power_margin_percent=margin_value,
            luminous_efficacy_lm_w=efficacy_value,
        )

    def _compute_geometry(self, data: CalculationInput) -> GeometryCalculationResult:
        ratio = geometry.calculate_spacing_height_ratio(data.pole_spacing_m, data.pole_height_m)
        ratio_value = CalculationValue(
            key="spacing_height_ratio",
            label="Ratio espacement / hauteur",
            value=_r(ratio, 2),
            unit=None,
            status="calculated" if ratio is not None else "not_calculable",
            formula="S/H = pole_spacing_m / pole_height_m",
            inputs={"spacing_m": data.pole_spacing_m, "height_m": data.pole_height_m},
            warning=(
                "Indicateur geometrique — validation photometrique necessaire."
                if ratio is not None
                else "Espacement ou hauteur de mat manquant(e) : ratio non calculable."
            ),
        )

        area = geometry.calculate_road_segment_area_m2(data.road_width_m, data.pole_spacing_m)
        area_value = CalculationValue(
            key="road_segment_area_m2",
            label="Surface routiere elementaire",
            value=_r(area, 1),
            unit="m2",
            status="calculated" if area is not None else "not_calculable",
            formula="A = road_width_m x pole_spacing_m",
            inputs={"width_m": data.road_width_m, "spacing_m": data.pole_spacing_m},
            warning=None if area is not None else "Largeur de chaussee ou espacement manquant(e) : surface non calculable.",
        )

        count = geometry.estimate_luminaire_count(data.road_length_m, data.pole_spacing_m, data.layout_type)
        count_value = CalculationValue(
            key="estimated_luminaire_count",
            label="Nombre estimatif de luminaires",
            value=count,
            unit=None,
            status="estimate" if count is not None else "not_calculable",
            formula="base_positions = ceil(road_length_m / pole_spacing_m) + 1 (x2 si implantation vis-a-vis)",
            inputs={"road_length_m": data.road_length_m, "pole_spacing_m": data.pole_spacing_m, "layout_type": data.layout_type},
            is_estimate=True,
            warning=(
                "Estimation de pre-dimensionnement — la geometrie reelle du projet peut modifier ce resultat."
                if count is not None
                else "Longueur de route ou espacement manquant(e) : nombre de luminaires non estimable."
            ),
        )

        return GeometryCalculationResult(
            spacing_height_ratio=ratio_value, road_segment_area_m2=area_value, estimated_luminaire_count=count_value
        )

    def _compute_thermal(self, data: CalculationInput) -> ThermalCalculationResult:
        driver_margin = thermal.calculate_thermal_margin_c(data.driver_max_temperature_c, data.ambient_temperature_c)
        driver_value = CalculationValue(
            key="driver_thermal_margin_c",
            label="Marge thermique driver",
            value=_r(driver_margin, 1),
            unit="C",
            status="calculated" if driver_margin is not None else "not_calculable",
            formula="marge = temperature_max_driver - temperature_ambiante_projet",
            inputs={"driver_max_temperature_c": data.driver_max_temperature_c, "ambient_temperature_c": data.ambient_temperature_c},
            warning=None if driver_margin is not None else "Temperature max. driver ou ambiante projet manquante : marge non calculable.",
        )

        lens_margin = thermal.calculate_thermal_margin_c(data.lens_max_temperature_c, data.ambient_temperature_c)
        lens_value = CalculationValue(
            key="lens_thermal_margin_c",
            label="Marge thermique lentille",
            value=_r(lens_margin, 1),
            unit="C",
            status="calculated" if lens_margin is not None else "not_calculable",
            formula="marge = temperature_max_lentille - temperature_ambiante_projet",
            inputs={"lens_max_temperature_c": data.lens_max_temperature_c, "ambient_temperature_c": data.ambient_temperature_c},
            warning=None if lens_margin is not None else "Temperature max. lentille ou ambiante projet manquante : marge non calculable.",
        )

        margins = [m for m in (driver_margin, lens_margin) if m is not None]
        tightest = min(margins) if margins else None
        tightest_value = CalculationValue(
            key="tightest_thermal_margin_c",
            label="Marge thermique la plus contraignante",
            value=_r(tightest, 1),
            unit="C",
            status="calculated" if tightest is not None else "not_calculable",
            formula="min(marge driver, marge lentille)",
            inputs={"driver_margin_c": _r(driver_margin, 1), "lens_margin_c": _r(lens_margin, 1)},
            warning=None if tightest is not None else "Aucune marge thermique calculable (donnees manquantes).",
        )

        return ThermalCalculationResult(
            driver_thermal_margin_c=driver_value, lens_thermal_margin_c=lens_value, tightest_thermal_margin_c=tightest_value
        )

    def _compute_energy(
        self,
        data: CalculationInput,
        elec: ElectricalCalculationResult,
        geo: GeometryCalculationResult,
        warnings: list[str],
    ) -> EnergyCalculationResult:
        # Puissance par luminaire : valeur nominale fabricant si connue, sinon estimation V x I.
        luminaire_power_w = data.module_power_nominal_w
        power_is_estimate = luminaire_power_w is None
        if luminaire_power_w is None:
            luminaire_power_w = elec.module_power_w.value

        n_luminaires = geo.estimated_luminaire_count.value

        total_power = energy.calculate_total_installed_power_kw(n_luminaires, luminaire_power_w)
        total_power_value = CalculationValue(
            key="total_installed_power_kw",
            label="Puissance totale installee",
            value=_r(total_power, 1),
            unit="kW",
            status="estimate" if total_power is not None else "not_calculable",
            formula="P_total = N_luminaires x P_luminaire / 1000",
            inputs={"number_of_luminaires": n_luminaires, "luminaire_power_w": luminaire_power_w},
            is_estimate=True,
            warning=(
                "Nombre de luminaires ou puissance par luminaire manquant(e) : puissance totale non calculable."
                if total_power is None
                else ("Base sur la puissance module calculee (hors pertes driver)." if power_is_estimate else None)
            ),
        )

        annual = energy.calculate_annual_energy_kwh(n_luminaires, luminaire_power_w, data.operating_hours_per_year)
        annual_value = CalculationValue(
            key="annual_energy_kwh",
            label="Consommation annuelle",
            value=_r(annual, 1),
            unit="kWh/an",
            status="estimate" if annual is not None else "not_calculable",
            formula="annual_energy_kwh = N x P(W) x heures / 1000",
            inputs={"number_of_luminaires": n_luminaires, "power_w": luminaire_power_w, "operating_hours_per_year": data.operating_hours_per_year},
            is_estimate=True,
            warning=(
                "Nombre de luminaires, puissance ou heures de fonctionnement manquant(e) : consommation non calculable."
                if annual is None
                else None
            ),
        )

        daily_dimming = energy.calculate_daily_energy_with_dimming_kwh(luminaire_power_w, data.dimming_profile, n_luminaires)
        annual_dimming = energy.calculate_annual_energy_with_dimming_kwh(daily_dimming)
        dimming_invalid = data.dimming_profile is not None and daily_dimming is None
        annual_dimming_value = CalculationValue(
            key="annual_energy_with_dimming_kwh",
            label="Consommation annuelle avec gradation",
            value=_r(annual_dimming, 1),
            unit="kWh/an",
            status="estimate" if annual_dimming is not None else "not_calculable",
            formula="daily = somme(P x niveau% x duree_h) ; annuel = daily x 365",
            inputs={"power_w": luminaire_power_w, "profile_entries": len(data.dimming_profile) if data.dimming_profile else 0},
            is_estimate=True,
            warning=(
                "Profil de gradation invalide (duree totale nulle ou superieure a 24h)."
                if dimming_invalid
                else (
                    "Estimation energetique basee sur le profil de gradation (relation proportionnelle, "
                    "ne reproduit pas la courbe electrique reelle du driver)."
                    if annual_dimming is not None
                    else "Puissance luminaire ou profil de gradation non fourni : estimation non calculable."
                )
            ),
        )
        if dimming_invalid:
            warnings.append("Profil de gradation invalide fourni : consommation avec gradation non calculee.")

        saving_percent = energy.calculate_energy_saving_percent(annual, data.reference_energy_kwh)
        saving_value = CalculationValue(
            key="energy_saving_percent",
            label="Economie energetique",
            value=_r(saving_percent, 1),
            unit="%",
            status="calculated" if saving_percent is not None else "not_calculable",
            formula="(1 - proposed_energy / reference_energy) x 100",
            inputs={"proposed_energy_kwh": _r(annual, 1), "reference_energy_kwh": data.reference_energy_kwh},
            warning=None if saving_percent is not None else "Consommation de reference non fournie : economie non calculable.",
        )

        saved_kwh = energy.calculate_energy_saved_kwh(annual, data.reference_energy_kwh)
        saved_value = CalculationValue(
            key="energy_saved_kwh_year",
            label="Energie economisee",
            value=_r(saved_kwh, 1),
            unit="kWh/an",
            status="calculated" if saved_kwh is not None else "not_calculable",
            formula="reference_energy_kwh - proposed_energy_kwh",
            inputs={"proposed_energy_kwh": _r(annual, 1), "reference_energy_kwh": data.reference_energy_kwh},
            warning=None if saved_kwh is not None else "Consommation de reference non fournie : economie non calculable.",
        )

        cost = energy.calculate_annual_energy_cost(annual, data.energy_price_per_kwh)
        cost_value = CalculationValue(
            key="annual_energy_cost",
            label="Cout energetique annuel",
            value=_r(cost, 1),
            unit=None,
            status="estimate" if cost is not None else "not_calculable",
            formula="annual_energy_cost = annual_energy_kwh x energy_price_per_kwh",
            inputs={"annual_energy_kwh": _r(annual, 1), "energy_price_per_kwh": data.energy_price_per_kwh},
            is_estimate=True,
            warning=None if cost is not None else "Tarif energetique non fourni : cout non calcule (jamais invente).",
        )

        return EnergyCalculationResult(
            total_installed_power_kw=total_power_value,
            annual_energy_kwh=annual_value,
            annual_energy_with_dimming_kwh=annual_dimming_value,
            energy_saving_percent=saving_value,
            energy_saved_kwh_year=saved_value,
            annual_energy_cost=cost_value,
        )

    def _compute_photometric(
        self, data: CalculationInput, geo: GeometryCalculationResult, warnings: list[str]
    ) -> PhotometricEstimateResult:
        area = geo.road_segment_area_m2.value
        illuminance = photometric.calculate_estimated_illuminance_lux(
            data.required_flux_lm, data.utilization_factor, data.maintenance_factor, area
        )
        illuminance_warning = (
            "Eclairement moyen estimatif — cette estimation ne remplace pas une simulation photometrique "
            "DIALux basee sur un fichier IES/LDT."
            if illuminance is not None
            else "Flux, facteur d'utilisation, facteur de maintenance ou surface manquant(e) : eclairement non estimable."
        )
        if illuminance is not None:
            warnings.append(illuminance_warning)
        illuminance_value = CalculationValue(
            key="estimated_average_illuminance_lux",
            label="Eclairement moyen estimatif",
            value=_r(illuminance, 1),
            unit="lux",
            status="estimate" if illuminance is not None else "not_calculable",
            formula="E_moy = (flux x CU x MF) / area",
            inputs={
                "flux_lm": data.required_flux_lm,
                "utilization_factor": data.utilization_factor,
                "maintenance_factor": data.maintenance_factor,
                "area_m2": area,
            },
            is_estimate=True,
            warning=illuminance_warning,
        )

        u0 = photometric.calculate_uniformity_u0(data.illuminance_min_lux, data.illuminance_avg_lux)
        u0_value = CalculationValue(
            key="uniformity_u0",
            label="Uniformite U0",
            value=_r(u0, 2),
            unit=None,
            status="calculated" if u0 is not None else "not_calculable",
            formula="U0 = E_min / E_avg",
            inputs={"e_min": data.illuminance_min_lux, "e_avg": data.illuminance_avg_lux},
            warning=None if u0 is not None else "E_min / E_avg non fournis (ex: import DIALux) : uniformite non calculable.",
        )

        return PhotometricEstimateResult(estimated_average_illuminance_lux=illuminance_value, uniformity_u0=u0_value)
