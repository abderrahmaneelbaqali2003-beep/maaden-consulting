"""Fabriques de donnees de test pour le moteur de recommandation."""

from app.database.models import Driver, LedModule, Lens, Manufacturer, ProjectRequirement

_counter = {"n": 0}


def _next_ref(prefix: str) -> str:
    _counter["n"] += 1
    return f"{prefix}-{_counter['n']:04d}"


def make_manufacturer(db, name: str | None = None) -> Manufacturer:
    name = name or _next_ref("MFR")
    existing = db.query(Manufacturer).filter(Manufacturer.name == name).one_or_none()
    if existing:
        return existing
    m = Manufacturer(name=name)
    db.add(m)
    db.flush()
    return m


def make_driver(db, **overrides) -> Driver:
    manufacturer = overrides.pop("manufacturer", None) or make_manufacturer(db)
    defaults = dict(
        external_ref=_next_ref("DRV-T"),
        manufacturer_id=manufacturer.id,
        reference=_next_ref("DRV-REF"),
        output_voltage_min_v=30,
        output_voltage_max_v=54,
        output_current_min_ma=700,
        output_current_max_ma=1050,
        output_power_max_w=150,
        dali_2=False,
        d4i=False,
        dimming_0_10v=False,
        dimming_1_10v=False,
        ambient_temperature_max_c=50,
        needs_manual_validation=False,
        is_active=True,
    )
    defaults.update(overrides)
    driver = Driver(**defaults)
    db.add(driver)
    db.flush()
    return driver


def make_module(db, **overrides) -> LedModule:
    manufacturer = overrides.pop("manufacturer", None) or make_manufacturer(db)
    defaults = dict(
        external_ref=_next_ref("MOD-T"),
        manufacturer_id=manufacturer.id,
        reference=_next_ref("MOD-REF"),
        input_voltage_nominal_v=48,
        current_nominal_ma=1050,
        power_nominal_w=50,
        luminous_flux_nominal_lm=6000,
        cct_nominal_k=4000,
        led_package="3535",
        led_quantity=32,
        needs_manual_validation=False,
        is_active=True,
    )
    defaults.update(overrides)
    module = LedModule(**defaults)
    db.add(module)
    db.flush()
    return module


def make_lens(db, **overrides) -> Lens:
    manufacturer = overrides.pop("manufacturer", None) or make_manufacturer(db)
    defaults = dict(
        external_ref=_next_ref("LEN-T"),
        manufacturer_id=manufacturer.id,
        reference=_next_ref("LEN-REF"),
        compatible_led_package="3535",
        optical_cells_quantity=32,
        ies_file_available=False,
        ldt_file_available=False,
        needs_manual_validation=False,
        is_active=True,
    )
    defaults.update(overrides)
    lens = Lens(**defaults)
    db.add(lens)
    db.flush()
    return lens


def make_requirement(db=None, persist: bool = False, **overrides) -> ProjectRequirement:
    defaults = dict(
        required_flux_lm=6000,
        max_power_w=60,
        required_cct_k=4000,
        voltage_nominal_v=48,
        current_nominal_ma=1050,
    )
    defaults.update(overrides)
    requirement = ProjectRequirement(**defaults)
    if persist:
        db.add(requirement)
        db.flush()
    return requirement
