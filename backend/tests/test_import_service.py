"""Tests du service d'import (section 17, scenarios 17 a 20 du cahier des charges)."""

import pandas as pd

from app.database.models import Driver
from app.services.import_service import import_drivers

BASE_ROW = {
    "driver_id": "DRV-TEST-001",
    "manufacturer": "TestManufacturer",
    "reference": "TEST-REF-1",
    "output_voltage_min_v": 30,
    "output_voltage_max_v": 54,
    "output_power_max_w": 150,
    "output_power_nominal_w": 150,
}


def _write_drivers_xlsx(tmp_path, rows: list[dict], filename: str = "drivers.xlsx"):
    df = pd.DataFrame(rows)
    path = tmp_path / filename
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="drivers_cleaned", index=False)
    return path


def test_import_new_reference_success(db_session, tmp_path):
    path = _write_drivers_xlsx(tmp_path, [BASE_ROW])

    result = import_drivers(db_session, str(path), "drivers.xlsx")

    assert result.rows_imported == 1
    assert result.rows_rejected == 0
    driver = db_session.query(Driver).filter(Driver.external_ref == "DRV-TEST-001").one()
    assert driver.reference == "TEST-REF-1"
    assert driver.output_voltage_min_v == 30
    assert driver.manufacturer.name == "TestManufacturer"


def test_import_duplicate_external_ref_rejected(db_session, tmp_path):
    rows = [BASE_ROW, {**BASE_ROW, "reference": "TEST-REF-1-BIS"}]
    path = _write_drivers_xlsx(tmp_path, rows)

    result = import_drivers(db_session, str(path), "drivers.xlsx")

    assert result.rows_imported == 1
    assert result.rows_rejected == 1
    assert "Doublon" in result.issues[0]["description"]


def test_import_missing_required_field_rejected(db_session, tmp_path):
    incomplete_row = {**BASE_ROW, "driver_id": "DRV-TEST-002", "output_voltage_min_v": None}
    path = _write_drivers_xlsx(tmp_path, [incomplete_row])

    result = import_drivers(db_session, str(path), "drivers.xlsx")

    assert result.rows_imported == 0
    assert result.rows_rejected == 1
    assert "output_voltage_min_v" in result.issues[0]["description"]
    count = db_session.query(Driver).filter(Driver.external_ref == "DRV-TEST-002").count()
    assert count == 0


def test_import_invalid_numeric_value_rejected(db_session, tmp_path):
    invalid_row = {**BASE_ROW, "driver_id": "DRV-TEST-003", "output_power_max_w": "non_numerique"}
    path = _write_drivers_xlsx(tmp_path, [invalid_row])

    result = import_drivers(db_session, str(path), "drivers.xlsx")

    assert result.rows_imported == 0
    assert result.rows_rejected == 1


def test_import_rerun_updates_instead_of_duplicating(db_session, tmp_path):
    path = _write_drivers_xlsx(tmp_path, [BASE_ROW])

    first = import_drivers(db_session, str(path), "drivers.xlsx")
    db_session.flush()
    second = import_drivers(db_session, str(path), "drivers.xlsx")

    assert first.rows_imported == 1
    assert second.rows_imported == 0
    assert second.rows_updated == 1
    count = db_session.query(Driver).filter(Driver.external_ref == "DRV-TEST-001").count()
    assert count == 1


def test_import_missing_manufacturer_rejected(db_session, tmp_path):
    row = {**BASE_ROW, "driver_id": "DRV-TEST-004", "manufacturer": None}
    path = _write_drivers_xlsx(tmp_path, [row])

    result = import_drivers(db_session, str(path), "drivers.xlsx")

    assert result.rows_rejected == 1
    assert result.rows_imported == 0
