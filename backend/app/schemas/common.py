from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ManufacturerRead(BaseModel):
    id: int
    name: str
    country: str | None = None
    website_url: str | None = None

    model_config = {"from_attributes": True}


def paginate(query, page: int = Field(1, ge=1), page_size: int = Field(20, ge=1, le=200)):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return items, total, total_pages
