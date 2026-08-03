from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database.models import Driver, Manufacturer

PROTOCOL_COLUMN_MAP = {
    "dali-2": "dali_2",
    "dali_2": "dali_2",
    "d4i": "d4i",
    "0-10v": "dimming_0_10v",
    "1-10v": "dimming_1_10v",
}


def list_drivers(
    db: Session,
    *,
    manufacturer: str | None = None,
    power_min_w: float | None = None,
    power_max_w: float | None = None,
    voltage_min_v: float | None = None,
    voltage_max_v: float | None = None,
    protocol: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
    sort_by: str = "reference",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(Driver).options(joinedload(Driver.manufacturer)).join(Manufacturer)

    if not include_inactive:
        query = query.filter(Driver.is_active.is_(True))
    if manufacturer:
        query = query.filter(Manufacturer.name.ilike(f"%{manufacturer}%"))
    if power_min_w is not None:
        query = query.filter(Driver.output_power_max_w >= power_min_w)
    if power_max_w is not None:
        query = query.filter(Driver.output_power_max_w <= power_max_w)
    if voltage_min_v is not None:
        query = query.filter(Driver.output_voltage_max_v >= voltage_min_v)
    if voltage_max_v is not None:
        query = query.filter(Driver.output_voltage_min_v <= voltage_max_v)
    if protocol:
        column_name = PROTOCOL_COLUMN_MAP.get(protocol.lower())
        if column_name:
            query = query.filter(getattr(Driver, column_name).is_(True))
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Driver.reference.ilike(like), Driver.product_name.ilike(like), Driver.product_family.ilike(like))
        )

    sort_column = getattr(Driver, sort_by, None) or Driver.reference
    query = query.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return items, total, total_pages


def get_driver(db: Session, driver_id: int) -> Driver | None:
    return db.query(Driver).options(joinedload(Driver.manufacturer)).filter(Driver.id == driver_id).one_or_none()
