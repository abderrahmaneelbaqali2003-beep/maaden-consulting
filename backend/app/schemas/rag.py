from datetime import datetime

from pydantic import BaseModel, Field


class RagDocumentOut(BaseModel):
    id: int
    title: str
    file_name: str
    document_type: str
    standard_family: str | None
    domain: str | None
    language: str
    authority_level: str
    active: bool
    embedding_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RagSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(5, ge=1, le=20)
    document_type: str | None = None
    standard_family: str | None = None
    domain: str | None = None
    authority_level: str | None = None


class RagSearchResultOut(BaseModel):
    document_title: str
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float


class RagSearchResponse(BaseModel):
    results: list[RagSearchResultOut]


class RagReindexDocumentOut(BaseModel):
    title: str
    status: str
    pages: int
    chunks: int
    error_message: str | None = None


class RagReindexResponse(BaseModel):
    documents: list[RagReindexDocumentOut]
