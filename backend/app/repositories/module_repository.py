from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database.models import LedModule, Manufacturer


def list_modules(
    db: Session,
    *,
    manufacturer: str | None = None,
    flux_min_lm: float | None = None,
    flux_max_lm: float | None = None,
    power_min_w: float | None = None,
    power_max_w: float | None = None,
    cct_k: int | None = None,
    voltage_min_v: float | None = None,
    voltage_max_v: float | None = None,
    current_min_ma: float | None = None,
    current_max_ma: float | None = None,
    led_package: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
    sort_by: str = "reference",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(LedModule).options(joinedload(LedModule.manufacturer)).join(Manufacturer)

    if not include_inactive:
        query = query.filter(LedModule.is_active.is_(True))
    if manufacturer:
        query = query.filter(Manufacturer.name.ilike(f"%{manufacturer}%"))
    if flux_min_lm is not None:
        query = query.filter(LedModule.luminous_flux_nominal_lm >= flux_min_lm)
    if flux_max_lm is not None:
        query = query.filter(LedModule.luminous_flux_nominal_lm <= flux_max_lm)
    if power_min_w is not None:
        query = query.filter(LedModule.power_nominal_w >= power_min_w)
    if power_max_w is not None:
        query = query.filter(LedModule.power_nominal_w <= power_max_w)
    if cct_k is not None:
        query = query.filter(LedModule.cct_nominal_k == cct_k)
    if voltage_min_v is not None:
        query = query.filter(LedModule.input_voltage_nominal_v >= voltage_min_v)
    if voltage_max_v is not None:
        query = query.filter(LedModule.input_voltage_nominal_v <= voltage_max_v)
    if current_min_ma is not None:
        query = query.filter(LedModule.current_nominal_ma >= current_min_ma)
    if current_max_ma is not None:
        query = query.filter(LedModule.current_nominal_ma <= current_max_ma)
    if led_package:
        query = query.filter(LedModule.led_package == led_package)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                LedModule.reference.ilike(like),
                LedModule.product_name.ilike(like),
                LedModule.product_family.ilike(like),
            )
        )

    sort_column = getattr(LedModule, sort_by, None) or LedModule.reference
    query = query.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return items, total, total_pages


def get_module(db: Session, module_id: int) -> LedModule | None:
    return (
        db.query(LedModule)
        .options(joinedload(LedModule.manufacturer))
        .filter(LedModule.id == module_id)
        .one_or_none()
    )
