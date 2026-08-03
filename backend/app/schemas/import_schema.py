from datetime import datetime

from pydantic import BaseModel


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    missing_count: int
    missing_percent: float
    unique_count: int


class AnalyzeResponse(BaseModel):
    file_name: str
    sheet_name: str
    row_count: int
    duplicate_rows: int
    columns: list[ColumnInfo]
    preview: list[dict]


class ImportIssueOut(BaseModel):
    row_number: int
    external_ref: str | None
    description: str


class ImportResponse(BaseModel):
    entity_type: str
    file_name: str
    rows_total: int
    rows_imported: int
    rows_updated: int
    rows_rejected: int
    import_history_id: int | None
    issues: list[ImportIssueOut]


class ImportHistoryRead(BaseModel):
    id: int
    entity_type: str
    file_name: str
    rows_total: int
    rows_imported: int
    rows_rejected: int
    status: str
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class DataIssueRead(BaseModel):
    id: int
    entity_type: str
    entity_external_ref: str | None
    row_number: int | None
    column_name: str | None
    issue_category: str | None
    description: str
    severity: str
    recommended_action: str | None
    manual_review_required: bool
    resolution_status: str

    model_config = {"from_attributes": True}
