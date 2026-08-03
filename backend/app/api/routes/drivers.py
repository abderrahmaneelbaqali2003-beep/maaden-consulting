from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.database.models import Driver
from app.repositories.driver_repository import get_driver, list_drivers
from app.repositories.manufacturer_repository import get_or_create_manufacturer
from app.schemas.common import PaginatedResponse
from app.schemas.driver import DriverCreate, DriverRead, DriverUpdate

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.get("", response_model=PaginatedResponse[DriverRead])
def list_drivers_endpoint(
    db: Session = Depends(get_db),
    manufacturer: str | None = Query(None, description="Filtre par nom de fabricant (recherche partielle)"),
    power_min_w: float | None = Query(None, ge=0, description="Puissance maximale du driver >= cette valeur (W)"),
    power_max_w: float | None = Query(None, ge=0, description="Puissance maximale du driver <= cette valeur (W)"),
    voltage_min_v: float | None = Query(None, ge=0),
    voltage_max_v: float | None = Query(None, ge=0),
    protocol: str | None = Query(None, description="dali-2 / d4i / 0-10v / 1-10v"),
    search: str | None = Query(None, description="Recherche sur reference / famille / nom produit"),
    include_inactive: bool = Query(False),
    sort_by: str = Query("reference"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    items, total, total_pages = list_drivers(
        db,
        manufacturer=manufacturer,
        power_min_w=power_min_w,
        power_max_w=power_max_w,
        voltage_min_v=voltage_min_v,
        voltage_max_v=voltage_max_v,
        protocol=protocol,
        search=search,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{driver_id}", response_model=DriverRead)
def get_driver_endpoint(driver_id: int, db: Session = Depends(get_db)):
    driver = get_driver(db, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver introuvable.")
    return driver


@router.post("", response_model=DriverRead, status_code=201)
def create_driver_endpoint(payload: DriverCreate, db: Session = Depends(get_db)):
    existing = db.query(Driver).filter(Driver.external_ref == payload.external_ref).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Un driver avec la reference '{payload.external_ref}' existe deja.")

    manufacturer = get_or_create_manufacturer(db, payload.manufacturer)
    data = payload.model_dump(exclude={"manufacturer"})
    driver = Driver(manufacturer_id=manufacturer.id, **data)
    db.add(driver)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Donnees invalides pour la creation du driver.") from exc
    db.refresh(driver)
    return driver


@router.put("/{driver_id}", response_model=DriverRead)
def update_driver_endpoint(driver_id: int, payload: DriverUpdate, db: Session = Depends(get_db)):
    driver = get_driver(db, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver introuvable.")

    update_data = payload.model_dump(exclude_unset=True)
    manufacturer_name = update_data.pop("manufacturer", None)
    if manufacturer_name:
        manufacturer = get_or_create_manufacturer(db, manufacturer_name)
        driver.manufacturer_id = manufacturer.id
    for field_name, value in update_data.items():
        setattr(driver, field_name, value)

    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{driver_id}", status_code=204)
def delete_driver_endpoint(driver_id: int, db: Session = Depends(get_db)):
    """Suppression logique : le driver est desactive (is_active=False), jamais supprime physiquement."""
    driver = get_driver(db, driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver introuvable.")
    driver.is_active = False
    db.commit()
