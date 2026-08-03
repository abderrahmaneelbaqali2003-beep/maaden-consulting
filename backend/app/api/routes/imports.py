import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.database.models import DataIssue, ImportHistory
from app.schemas.common import PaginatedResponse
from app.schemas.import_schema import AnalyzeResponse, DataIssueRead, ImportHistoryRead, ImportResponse
from app.services.import_service import analyze_file, import_drivers, import_lenses, import_modules
from app.utils.file_readers import is_allowed_file

router = APIRouter(prefix="/api/imports", tags=["imports"])

IMPORTERS = {"drivers": import_drivers, "modules": import_modules, "lenses": import_lenses}


async def _save_upload_to_temp(file: UploadFile) -> Path:
    settings = get_settings()

    if not file.filename or not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=400, detail="Extension de fichier non autorisee. Utilisez .xlsx, .xls ou .csv."
        )

    content = await file.read()
    max_bytes = settings.max_import_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400, detail=f"Fichier trop volumineux (max {settings.max_import_file_size_mb} Mo)."
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")

    suffix = Path(file.filename).suffix.lower()
    temp_dir = Path(tempfile.gettempdir()) / "smart_lighting_imports"
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}{suffix}"
    temp_path.write_bytes(content)
    return temp_path


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_import_file(file: UploadFile = File(...)):
    temp_path = await _save_upload_to_temp(file)
    try:
        result = analyze_file(str(temp_path), file.filename)
        return AnalyzeResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Impossible d'analyser le fichier : {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def _run_import(entity_key: str):
    async def handler(file: UploadFile = File(...), db: Session = Depends(get_db)):
        temp_path = await _save_upload_to_temp(file)
        try:
            importer = IMPORTERS[entity_key]
            result = importer(db, str(temp_path), file.filename)
            db.commit()
            return ImportResponse(
                entity_type=result.entity_type,
                file_name=result.file_name,
                rows_total=result.rows_total,
                rows_imported=result.rows_imported,
                rows_updated=result.rows_updated,
                rows_rejected=result.rows_rejected,
                import_history_id=result.import_history_id,
                issues=result.issues,
            )
        except Exception as exc:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Echec de l'import : {exc}") from exc
        finally:
            temp_path.unlink(missing_ok=True)

    return handler


router.add_api_route("/drivers", _run_import("drivers"), methods=["POST"], response_model=ImportResponse)
router.add_api_route("/modules", _run_import("modules"), methods=["POST"], response_model=ImportResponse)
router.add_api_route("/lenses", _run_import("lenses"), methods=["POST"], response_model=ImportResponse)


@router.get("/history", response_model=PaginatedResponse[ImportHistoryRead])
def get_import_history(
    db: Session = Depends(get_db), page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)
):
    query = db.query(ImportHistory).order_by(ImportHistory.started_at.desc())
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


@router.get("/{import_id}/issues", response_model=list[DataIssueRead])
def get_import_issues(import_id: int, db: Session = Depends(get_db)):
    history = db.get(ImportHistory, import_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Historique d'import introuvable.")
    return db.query(DataIssue).filter(DataIssue.import_history_id == import_id).all()
