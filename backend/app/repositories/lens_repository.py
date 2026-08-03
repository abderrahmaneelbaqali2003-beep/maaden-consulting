from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.database.models import Lens, Manufacturer


def list_lenses(
    db: Session,
    *,
    manufacturer: str | None = None,
    led_package: str | None = None,
    optical_cells_quantity: int | None = None,
    distribution: str | None = None,
    search: str | None = None,
    include_inactive: bool = False,
    sort_by: str = "reference",
    sort_dir: str = "asc",
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(Lens).options(joinedload(Lens.manufacturer)).join(Manufacturer)

    if not include_inactive:
        query = query.filter(Lens.is_active.is_(True))
    if manufacturer:
        query = query.filter(Manufacturer.name.ilike(f"%{manufacturer}%"))
    if led_package:
        query = query.filter(Lens.compatible_led_package.ilike(f"%{led_package}%"))
    if optical_cells_quantity is not None:
        query = query.filter(Lens.optical_cells_quantity == optical_cells_quantity)
    if distribution:
        query = query.filter(Lens.iesna_distribution_type.ilike(f"%{distribution}%"))
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Lens.reference.ilike(like), Lens.product_name.ilike(like), Lens.product_family.ilike(like))
        )

    sort_column = getattr(Lens, sort_by, None) or Lens.reference
    query = query.order_by(sort_column.desc() if sort_dir == "desc" else sort_column.asc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return items, total, total_pages


def get_lens(db: Session, lens_id: int) -> Lens | None:
    return db.query(Lens).options(joinedload(Lens.manufacturer)).filter(Lens.id == lens_id).one_or_none()
