"""Service d'import des catalogues Drivers / Modules LED / Lentilles (section 9 du cahier des charges).

Principe : chaque colonne de la feuille source '*_cleaned' est mappee vers un champ du
modele SQLAlchemy correspondant. Une valeur absente de la source reste NULL en base
(jamais convertie en zero). Les lignes sans les champs strictement indispensables au
moteur de compatibilite (ex: tension de sortie d'un driver) sont rejetees et journalisees
comme anomalie plutot que d'etre importees avec des donnees inventees.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.database.models import (
    CompatibilityRule,
    DataIssue,
    Driver,
    ImportHistory,
    LedModule,
    Lens,
)
from app.repositories.manufacturer_repository import get_or_create_manufacturer
from app.utils.file_readers import detect_main_sheet, read_dataframe
from app.utils.value_cleaning import clean_bool, clean_float, clean_int, clean_str


@dataclass
class ImportResult:
    entity_type: str
    file_name: str
    rows_total: int = 0
    rows_imported: int = 0
    rows_updated: int = 0
    rows_rejected: int = 0
    issues: list[dict] = field(default_factory=list)
    import_history_id: int | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def analyze_file(file_path: str, file_name: str) -> dict:
    """Etape 'analyse des colonnes + apercu' du pipeline d'import (section 9), avant toute ecriture en base."""
    sheet_name = detect_main_sheet(file_path, "cleaned")
    df = read_dataframe(file_path, sheet_name=sheet_name)

    columns = []
    for col in df.columns:
        missing = int(df[col].isna().sum())
        columns.append(
            {
                "name": str(col),
                "dtype": str(df[col].dtype),
                "missing_count": missing,
                "missing_percent": round(100 * missing / len(df), 1) if len(df) else 0.0,
                "unique_count": int(df[col].nunique(dropna=True)),
            }
        )

    preview_df = df.head(10).where(pd.notna(df.head(10)), None)
    preview = preview_df.to_dict(orient="records")

    return {
        "file_name": file_name,
        "sheet_name": sheet_name,
        "row_count": len(df),
        "duplicate_rows": int(df.duplicated().sum()),
        "columns": columns,
        "preview": preview,
    }


def _map_row(row: pd.Series, field_map: dict) -> dict:
    """Applique un field_map {champ_modele: (colonne_source, fonction_nettoyage)} a une ligne pandas."""
    result = {}
    for model_field, (source_column, cleaner) in field_map.items():
        raw_value = row[source_column] if source_column in row.index else None
        result[model_field] = cleaner(raw_value) if cleaner else raw_value
    return result


def _record_issue(
    session: Session,
    import_history_id: int,
    entity_type: str,
    external_ref: str | None,
    row_number: int,
    description: str,
    severity: str = "high",
    column_name: str | None = None,
) -> dict:
    issue = DataIssue(
        import_history_id=import_history_id,
        entity_type=entity_type,
        entity_external_ref=external_ref,
        row_number=row_number,
        column_name=column_name,
        issue_category="import_rejection",
        description=description,
        severity=severity,
        manual_review_required=True,
        resolution_status="open",
    )
    session.add(issue)
    return {"row_number": row_number, "external_ref": external_ref, "description": description}


# --- Field maps : champ modele -> (colonne source dans la feuille *_cleaned, fonction de nettoyage) ---

DRIVER_FIELD_MAP = {
    "reference": ("reference", clean_str),
    "product_family": ("product_family", clean_str),
    "product_name": ("product_name", clean_str),
    "driver_type": ("driver_type", clean_str),
    "application": ("application", clean_str),
    "input_voltage_nominal_v": ("input_voltage_nominal_v", clean_float),
    "output_type": ("output_type", clean_str),
    "output_voltage_min_v": ("output_voltage_min_v", clean_float),
    "output_voltage_nominal_v": ("output_voltage_nominal_v", clean_float),
    "output_voltage_max_v": ("output_voltage_max_v", clean_float),
    "output_current_min_ma": ("output_current_min_ma", clean_float),
    "output_current_nominal_ma": ("output_current_nominal_ma", clean_float),
    "output_current_max_ma": ("output_current_max_ma", clean_float),
    "output_power_nominal_w": ("output_power_nominal_w", clean_float),
    "output_power_max_w": ("output_power_max_w", clean_float),
    "efficiency_percent": ("efficiency_percent", clean_float),
    "power_factor": ("power_factor", clean_float),
    "thd_percent": ("thd_percent", clean_float),
    "dimmable": ("dimmable", clean_bool),
    "dimming_0_10v": ("dimming_0_10v", clean_bool),
    "dimming_1_10v": ("dimming_1_10v", clean_bool),
    "dali_2": ("dali_2", clean_bool),
    "d4i": ("d4i", clean_bool),
    "pwm_dimming": ("pwm_dimming", clean_bool),
    "resistance_dimming": ("resistance_dimming", clean_bool),
    "ambient_temperature_min_c": ("ambient_temperature_min_c", clean_float),
    "ambient_temperature_max_c": ("ambient_temperature_max_c", clean_float),
    "tc_max_c": ("tc_max_c", clean_float),
    "ip_rating": ("ip_rating", clean_str),
    "electrical_class": ("electrical_class", clean_str),
    "surge_line_to_line_kv": ("surge_line_to_line_kv", clean_float),
    "surge_line_to_earth_kv": ("surge_line_to_earth_kv", clean_float),
    "warranty_years": ("warranty_years", clean_int),
    "ce_certified": ("ce_certified", clean_bool),
    "enec_certified": ("enec_certified", clean_bool),
    "ul_certified": ("ul_certified", clean_bool),
    "rohs_compliant": ("rohs_compliant", clean_bool),
    "certifications": ("certifications", clean_str),
    "standards": ("standards", clean_str),
    "outdoor_direct": ("outdoor_direct", clean_str),
    "outdoor_robustness_score_10": ("outdoor_robustness_score_10", clean_float),
    "smart_lighting_level": ("smart_lighting_level", clean_int),
    "benchmark_score": ("benchmark_final_score", clean_float),
    "benchmark_rank": ("benchmark_rank", clean_int),
    "datasheet_url": ("datasheet_url", clean_str),
    "validation_status": ("validation_status", clean_str),
    "validation_message": ("validation_message", clean_str),
    "source_name": ("source_name", clean_str),
    "notes": ("notes", clean_str),
    "data_quality_score": ("overall_data_quality_score", clean_float),
    "data_quality_level": ("data_quality_level", clean_str),
}

MODULE_FIELD_MAP = {
    "reference": ("reference", clean_str),
    "product_family": ("product_family", clean_str),
    "product_name": ("product_name", clean_str),
    "module_type": ("module_type", clean_str),
    "application": ("application", clean_str),
    "module_status": ("module_status", clean_str),
    "led_manufacturer": ("led_manufacturer", clean_str),
    "led_reference": ("led_reference", clean_str),
    "led_package": ("led_package", clean_str),
    "led_power_category": ("led_power_category", clean_str),
    "led_quantity": ("led_quantity", clean_int),
    "series_parallel_configuration": ("series_parallel_configuration", clean_str),
    "electrical_configuration": ("electrical_configuration", clean_str),
    "constant_current_required": ("constant_current_required", clean_bool),
    "constant_voltage_required": ("constant_voltage_required", clean_bool),
    "input_voltage_nominal_v": ("input_voltage_nominal_v", clean_float),
    "current_nominal_ma": ("current_nominal_ma", clean_float),
    "power_nominal_w": ("power_nominal_w", clean_float),
    "luminous_flux_nominal_lm": ("luminous_flux_nominal_lm", clean_float),
    "luminous_efficacy_nominal_lm_w": ("luminous_efficacy_nominal_lm_w", clean_float),
    "cct_nominal_k": ("cct_nominal_k", clean_int),
    "cct_options": ("cct_options", clean_str),
    "cri_min": ("cri_min", clean_int),
    "tc_point_temperature_max_c": ("tc_point_temperature_max_c", clean_float),
    "pcb_type": ("pcb_type", clean_str),
    "pcb_base_material": ("pcb_base_material", clean_str),
    "length_mm": ("length_mm", clean_float),
    "width_mm": ("width_mm", clean_float),
    "height_mm": ("height_mm", clean_float),
    "lifetime_hours": ("lifetime_hours", clean_int),
    "lumen_maintenance_standard": ("lumen_maintenance_standard", clean_str),
    "l70_hours": ("l70_hours", clean_float),
    "reliability_notes": ("reliability_notes", clean_str),
    "ce_certified": ("ce_certified", clean_bool),
    "enec_certified": ("enec_certified", clean_bool),
    "ul_certified": ("ul_certified", clean_bool),
    "rohs_compliant": ("rohs_compliant", clean_bool),
    "certifications": ("certifications", clean_str),
    "standards": ("standards", clean_str),
    "ip_rating": ("ip_rating", clean_str),
    "ik_rating": ("ik_rating", clean_str),
    "driver_compatibility_notes": ("driver_compatibility_notes", clean_str),
    "driver_compat_current_min_ma": ("driver_compat_current_min_ma", clean_float),
    "driver_compat_current_max_ma": ("driver_compat_current_max_ma", clean_float),
    "surface_area_mm2": ("surface_area_mm2", clean_float),
    "luminous_density_lm_mm2": ("luminous_density_lm_mm2", clean_float),
    "power_density_w_mm2": ("power_density_w_mm2", clean_float),
    "benchmark_score": ("benchmark_score", clean_float),
    "benchmark_rank": ("benchmark_rank", clean_int),
    "datasheet_url": ("datasheet_url", clean_str),
    "validation_status": ("validation_status", clean_str),
    "validation_message": ("validation_message", clean_str),
    "source_name": ("source_name", clean_str),
    "notes": ("notes", clean_str),
    "data_quality_score": ("overall_data_quality_score", clean_float),
    "data_quality_level": ("data_quality_level", clean_str),
}

LENS_FIELD_MAP = {
    "reference": ("reference", clean_str),
    "product_family": ("product_family", clean_str),
    "product_name": ("product_name", clean_str),
    "lens_type": ("lens_type", clean_str),
    "application": ("application", clean_str),
    "product_status": ("product_status", clean_str),
    "catalog_level": ("catalog_level", clean_str),
    "compatible_led_package": ("compatible_led_package", clean_str),
    "compatible_led_power_category": ("compatible_led_power_category", clean_str),
    "compatibility_status": ("compatibility_status", clean_str),
    "compatibility_source": ("compatibility_source", clean_str),
    "compatibility_notes": ("compatibility_notes", clean_str),
    "compat_2835": ("compat_2835", clean_bool),
    "compat_3030": ("compat_3030", clean_bool),
    "compat_3535": ("compat_3535", clean_bool),
    "compat_5050": ("compat_5050", clean_bool),
    "compat_7070": ("compat_7070", clean_bool),
    "compat_csp": ("compat_csp", clean_bool),
    "compat_cob": ("compat_cob", clean_bool),
    "optical_cells_quantity": ("optical_cells_quantity", clean_int),
    "rows_count": ("rows_count", clean_int),
    "columns_count": ("columns_count", clean_int),
    "configuration_description": ("configuration_description", clean_str),
    "lens_pitch_x_mm": ("lens_pitch_x_mm", clean_float),
    "lens_pitch_y_mm": ("lens_pitch_y_mm", clean_float),
    "iesna_distribution_type": ("iesna_distribution_type", clean_str),
    "beam_distribution_name": ("beam_distribution_name", clean_str),
    "beam_angle_horizontal_deg": ("beam_angle_horizontal_deg", clean_float),
    "asymmetry_type": ("asymmetry_type", clean_str),
    "photometric_classification": ("photometric_classification", clean_str),
    "photometric_notes": ("photometric_notes", clean_str),
    "ies_file_available": ("ies_file_available", clean_bool),
    "ldt_file_available": ("ldt_file_available", clean_bool),
    "road_application": ("road_application", clean_str),
    "road_application_notes": ("road_application_notes", clean_str),
    "app_highway": ("app_highway", clean_bool),
    "app_national_road": ("app_national_road", clean_bool),
    "app_urban_road": ("app_urban_road", clean_bool),
    "optical_material": ("optical_material", clean_str),
    "uv_resistant": ("uv_resistant", clean_bool),
    "operating_temperature_max_c": ("operating_temperature_max_c", clean_float),
    "length_mm": ("length_mm", clean_float),
    "width_mm": ("width_mm", clean_float),
    "height_mm": ("height_mm", clean_float),
    "diameter_mm": ("diameter_mm", clean_float),
    "mounting_hole_pitch_x_mm": ("mounting_hole_pitch_x_mm", clean_float),
    "mounting_hole_pitch_y_mm": ("mounting_hole_pitch_y_mm", clean_float),
    "compatible_led_height_mm": ("compatible_led_height_mm", clean_float),
    "gasket_required": ("gasket_required", clean_bool),
    "outdoor_use": ("outdoor_use", clean_bool),
    "standards": ("standards", clean_str),
    "compliance_status": ("compliance_status", clean_str),
    "product_url": ("product_url", clean_str),
    "distribution_detail": ("distribution_detail", clean_str),
    "distribution_status_raw": ("distribution_status_raw", clean_str),
    "validation_status": ("validation_status", clean_str),
    "validation_message": ("validation_message", clean_str),
    "source_name": ("source_name", clean_str),
    "notes": ("notes", clean_str),
    "data_quality_score": ("overall_data_quality_score", clean_float),
    "data_quality_level": ("data_quality_level", clean_str),
}


def _import_entity(
    session: Session,
    file_path: str,
    file_name: str,
    entity_type: str,
    model_cls,
    field_map: dict,
    external_ref_column: str,
    required_fields: list[str],
    boolean_defaults_false: list[str],
) -> ImportResult:
    started_at = _now()
    sheet_name = detect_main_sheet(file_path, "cleaned")
    df = read_dataframe(file_path, sheet_name=sheet_name)

    history = ImportHistory(
        entity_type=entity_type,
        file_name=file_name,
        rows_total=len(df),
        status="running",
        started_at=started_at,
    )
    session.add(history)
    session.flush()

    result = ImportResult(entity_type=entity_type, file_name=file_name, rows_total=len(df))

    seen_refs: set[str] = set()

    for idx, row in df.iterrows():
        row_number = int(idx) + 2  # +2 : ligne d'entete Excel + index pandas base 0
        external_ref = clean_str(row.get(external_ref_column))

        if not external_ref:
            result.issues.append(
                _record_issue(
                    session, history.id, entity_type, None, row_number,
                    f"Ligne ignoree : identifiant '{external_ref_column}' manquant.",
                )
            )
            result.rows_rejected += 1
            continue

        if external_ref in seen_refs:
            result.issues.append(
                _record_issue(
                    session, history.id, entity_type, external_ref, row_number,
                    f"Doublon d'identifiant '{external_ref}' dans le fichier : ligne ignoree.",
                    severity="medium",
                )
            )
            result.rows_rejected += 1
            continue

        manufacturer_name = clean_str(row.get("manufacturer"))
        manufacturer = get_or_create_manufacturer(session, manufacturer_name)
        if manufacturer is None:
            result.issues.append(
                _record_issue(
                    session, history.id, entity_type, external_ref, row_number,
                    "Fabricant manquant : ligne ignoree.", column_name="manufacturer",
                )
            )
            result.rows_rejected += 1
            continue

        values = _map_row(row, field_map)

        missing_required = [f for f in required_fields if values.get(f) is None]
        if missing_required:
            result.issues.append(
                _record_issue(
                    session, history.id, entity_type, external_ref, row_number,
                    f"Champ(s) indispensable(s) manquant(s) pour le moteur de compatibilite : {', '.join(missing_required)}.",
                    column_name=",".join(missing_required),
                )
            )
            result.rows_rejected += 1
            continue

        for bool_field in boolean_defaults_false:
            if values.get(bool_field) is None:
                values[bool_field] = False

        values["needs_manual_validation"] = bool(clean_bool(row.get("manual_review_required")) or False)

        existing = (
            session.query(model_cls).filter(model_cls.external_ref == external_ref).one_or_none()
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            existing.manufacturer_id = manufacturer.id
            result.rows_updated += 1
        else:
            instance = model_cls(external_ref=external_ref, manufacturer_id=manufacturer.id, **values)
            session.add(instance)
            result.rows_imported += 1

        seen_refs.add(external_ref)

    history.rows_imported = result.rows_imported + result.rows_updated
    history.rows_rejected = result.rows_rejected
    history.status = "success" if result.rows_rejected == 0 else "partial"
    history.finished_at = _now()
    session.flush()
    result.import_history_id = history.id
    return result


def import_drivers(session: Session, file_path: str, file_name: str) -> ImportResult:
    return _import_entity(
        session, file_path, file_name, "driver", Driver, DRIVER_FIELD_MAP,
        external_ref_column="driver_id",
        required_fields=["output_voltage_min_v", "output_voltage_max_v", "output_power_max_w"],
        boolean_defaults_false=[
            "dimmable", "dimming_0_10v", "dimming_1_10v", "dali_2", "d4i", "pwm_dimming",
            "resistance_dimming", "ce_certified", "enec_certified", "ul_certified", "rohs_compliant",
        ],
    )


def import_modules(session: Session, file_path: str, file_name: str) -> ImportResult:
    return _import_entity(
        session, file_path, file_name, "led_module", LedModule, MODULE_FIELD_MAP,
        external_ref_column="module_id",
        required_fields=["luminous_flux_nominal_lm", "cct_nominal_k"],
        boolean_defaults_false=[
            "constant_current_required", "constant_voltage_required", "ce_certified",
            "enec_certified", "ul_certified", "rohs_compliant",
        ],
    )


def import_lenses(session: Session, file_path: str, file_name: str) -> ImportResult:
    return _import_entity(
        session, file_path, file_name, "lens", Lens, LENS_FIELD_MAP,
        external_ref_column="lens_id",
        required_fields=["reference"],
        boolean_defaults_false=["ies_file_available", "ldt_file_available"],
    )


# --- Import des regles de compatibilite (feuilles *_compatibility_rules) ---

RULE_ENTITY_SHEETS = {
    "driver": ("driver_compatibility_rules", "driver_field"),
    "module": ("module_compatibility_rules", "module_field"),
    "lens": ("lens_compatibility_rules", "lens_field"),
}


def import_compatibility_rules(session: Session, file_path: str, entity_type: str) -> int:
    sheet_name, field_column = RULE_ENTITY_SHEETS[entity_type]
    df = read_dataframe(file_path, sheet_name=sheet_name)

    count = 0
    for _, row in df.iterrows():
        external_rule_id = clean_str(row.get("rule_id"))
        if not external_rule_id:
            continue

        requirement_field_col = "requirement_field" if "requirement_field" in row.index else "module_or_project_field"

        values = {
            "rule_category": clean_str(row.get("rule_category")),
            "rule_name": clean_str(row.get("rule_name")) or external_rule_id,
            "field_name": clean_str(row.get(field_column)) or "",
            "operator": clean_str(row.get("operator")),
            "requirement_field": clean_str(row.get(requirement_field_col)) or "",
            "tolerance_value": clean_float(row.get("tolerance_value")),
            "tolerance_unit": clean_str(row.get("tolerance_unit")),
            "severity": clean_str(row.get("severity")) or "warning",
            "error_message": clean_str(row.get("error_message")) or "",
            "enabled": clean_bool(row.get("enabled")) if clean_bool(row.get("enabled")) is not None else True,
            "notes": clean_str(row.get("notes")),
        }

        existing = (
            session.query(CompatibilityRule)
            .filter(
                CompatibilityRule.entity_type == entity_type,
                CompatibilityRule.external_rule_id == external_rule_id,
            )
            .one_or_none()
        )
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
        else:
            session.add(
                CompatibilityRule(entity_type=entity_type, external_rule_id=external_rule_id, **values)
            )
        count += 1

    session.flush()
    return count
