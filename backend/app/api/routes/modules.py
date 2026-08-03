from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.database.models import LedModule
from app.repositories.manufacturer_repository import get_or_create_manufacturer
from app.repositories.module_repository import get_module, list_modules
from app.schemas.common import PaginatedResponse
from app.schemas.module import ModuleCreate, ModuleRead, ModuleUpdate

router = APIRouter(prefix="/api/modules", tags=["modules"])


@router.get("", response_model=PaginatedResponse[ModuleRead])
def list_modules_endpoint(
    db: Session = Depends(get_db),
    manufacturer: str | None = Query(None),
    flux_min_lm: float | None = Query(None, ge=0),
    flux_max_lm: float | None = Query(None, ge=0),
    power_min_w: float | None = Query(None, ge=0),
    power_max_w: float | None = Query(None, ge=0),
    cct_k: int | None = Query(None, gt=0),
    voltage_min_v: float | None = Query(None, ge=0),
    voltage_max_v: float | None = Query(None, ge=0),
    current_min_ma: float | None = Query(None, ge=0),
    current_max_ma: float | None = Query(None, ge=0),
    led_package: str | None = Query(None),
    search: str | None = Query(None),
    include_inactive: bool = Query(False),
    sort_by: str = Query("reference"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    items, total, total_pages = list_modules(
        db,
        manufacturer=manufacturer,
        flux_min_lm=flux_min_lm,
        flux_max_lm=flux_max_lm,
        power_min_w=power_min_w,
        power_max_w=power_max_w,
        cct_k=cct_k,
        voltage_min_v=voltage_min_v,
        voltage_max_v=voltage_max_v,
        current_min_ma=current_min_ma,
        current_max_ma=current_max_ma,
        led_package=led_package,
        search=search,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{module_id}", response_model=ModuleRead)
def get_module_endpoint(module_id: int, db: Session = Depends(get_db)):
    module = get_module(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module LED introuvable.")
    return module


@router.post("", response_model=ModuleRead, status_code=201)
def create_module_endpoint(payload: ModuleCreate, db: Session = Depends(get_db)):
    existing = db.query(LedModule).filter(LedModule.external_ref == payload.external_ref).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"Un module avec la reference '{payload.external_ref}' existe deja."
        )

    manufacturer = get_or_create_manufacturer(db, payload.manufacturer)
    data = payload.model_dump(exclude={"manufacturer"})
    module = LedModule(manufacturer_id=manufacturer.id, **data)
    db.add(module)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Donnees invalides pour la creation du module.") from exc
    db.refresh(module)
    return module


@router.put("/{module_id}", response_model=ModuleRead)
def update_module_endpoint(module_id: int, payload: ModuleUpdate, db: Session = Depends(get_db)):
    module = get_module(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module LED introuvable.")

    update_data = payload.model_dump(exclude_unset=True)
    manufacturer_name = update_data.pop("manufacturer", None)
    if manufacturer_name:
        manufacturer = get_or_create_manufacturer(db, manufacturer_name)
        module.manufacturer_id = manufacturer.id
    for field_name, value in update_data.items():
        setattr(module, field_name, value)

    db.commit()
    db.refresh(module)
    return module


@router.delete("/{module_id}", status_code=204)
def delete_module_endpoint(module_id: int, db: Session = Depends(get_db)):
    module = get_module(db, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module LED introuvable.")
    module.is_active = False
    db.commit()
