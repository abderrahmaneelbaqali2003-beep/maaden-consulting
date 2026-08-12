from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.recommendation import RecommendationItem

PROJECT_STATUSES = [
    "draft",
    "requirements_review",
    "study_in_progress",
    "scenario_selection",
    "photometric_validation",
    "validated",
    "archived",
]


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    client_name: str | None = None
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectOut(BaseModel):
    id: int
    reference: str | None
    name: str
    client_name: str | None
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    cps_document_count: int = 0
    requirement_count: int = 0
    scenario_count: int = 0
    selected_scenario_code: str | None = None


class CpsDocumentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    original_filename: str
    document_type: str
    page_count: int
    uploaded_at: datetime
    extraction_status: str
    extraction_message: str | None


class ExtractedRequirementOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    project_id: int
    cps_document_id: int | None
    category: str
    scope: str
    field_name: str
    operator: str
    raw_value: str
    numeric_value: float | None
    unit: str | None
    source_page: int | None
    source_excerpt: str | None
    extraction_confidence: str
    validation_status: str
    validated_value: str | None
    validated_by: str | None
    validated_at: datetime | None


class RequirementUpdateRequest(BaseModel):
    action: str = Field(..., description="confirm, modify ou ignore")
    validated_value: str | None = None
    validated_by: str = Field(..., min_length=1)


class ManualRequirementCreate(BaseModel):
    category: str
    scope: str
    field_name: str
    operator: str = "=="
    value: str = Field(..., min_length=1)
    unit: str | None = None
    validated_by: str = Field(..., min_length=1)


class StudyRunRequest(BaseModel):
    launched_by: str | None = None


class ProjectScenarioOut(BaseModel):
    id: int
    project_id: int
    scenario_code: str
    selected: bool
    selected_by: str | None
    selected_at: datetime | None
    selection_comment: str | None
    recommendation: RecommendationItem
    run_id: int


class ScenarioSelectRequest(BaseModel):
    selected_by: str = Field(..., min_length=1)
    selection_comment: str | None = None
