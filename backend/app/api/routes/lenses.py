from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.database.models import Lens
from app.repositories.lens_repository import get_lens, list_lenses
from app.repositories.manufacturer_repository import get_or_create_manufacturer
from app.schemas.common import PaginatedResponse
from app.schemas.lens import LensCreate, LensRead, LensUpdate

router = APIRouter(prefix="/api/lenses", tags=["lenses"])


@router.get("", response_model=PaginatedResponse[LensRead])
def list_lenses_endpoint(
    db: Session = Depends(get_db),
    manufacturer: str | None = Query(None),
    led_package: str | None = Query(None, description="Package LED compatible (ex: 3535)"),
    optical_cells_quantity: int | None = Query(None, ge=0),
    distribution: str | None = Query(None, description="Type de distribution photometrique IESNA"),
    search: str | None = Query(None),
    include_inactive: bool = Query(False),
    sort_by: str = Query("reference"),
    sort_dir: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    items, total, total_pages = list_lenses(
        db,
        manufacturer=manufacturer,
        led_package=led_package,
        optical_cells_quantity=optical_cells_quantity,
        distribution=distribution,
        search=search,
        include_inactive=include_inactive,
        sort_by=sort_by,
        sort_dir=sort_dir,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{lens_id}", response_model=LensRead)
def get_lens_endpoint(lens_id: int, db: Session = Depends(get_db)):
    lens = get_lens(db, lens_id)
    if lens is None:
        raise HTTPException(status_code=404, detail="Lentille introuvable.")
    return lens


@router.post("", response_model=LensRead, status_code=201)
def create_lens_endpoint(payload: LensCreate, db: Session = Depends(get_db)):
    existing = db.query(Lens).filter(Lens.external_ref == payload.external_ref).one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=409, detail=f"Une lentille avec la reference '{payload.external_ref}' existe deja."
        )

    manufacturer = get_or_create_manufacturer(db, payload.manufacturer)
    data = payload.model_dump(exclude={"manufacturer"})
    lens = Lens(manufacturer_id=manufacturer.id, **data)
    db.add(lens)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Donnees invalides pour la creation de la lentille.") from exc
    db.refresh(lens)
    return lens


@router.put("/{lens_id}", response_model=LensRead)
def update_lens_endpoint(lens_id: int, payload: LensUpdate, db: Session = Depends(get_db)):
    lens = get_lens(db, lens_id)
    if lens is None:
        raise HTTPException(status_code=404, detail="Lentille introuvable.")

    update_data = payload.model_dump(exclude_unset=True)
    manufacturer_name = update_data.pop("manufacturer", None)
    if manufacturer_name:
        manufacturer = get_or_create_manufacturer(db, manufacturer_name)
        lens.manufacturer_id = manufacturer.id
    for field_name, value in update_data.items():
        setattr(lens, field_name, value)

    db.commit()
    db.refresh(lens)
    return lens


@router.delete("/{lens_id}", status_code=204)
def delete_lens_endpoint(lens_id: int, db: Session = Depends(get_db)):
    lens = get_lens(db, lens_id)
    if lens is None:
        raise HTTPException(status_code=404, detail="Lentille introuvable.")
    lens.is_active = False
    db.commit()
