"""Endpoint de generation du rapport PDF de consulting. Reste volontairement mince :
toute la logique (recuperation des donnees, garde-fou de validation, mise en page)
vit dans `app/reports/` (`ReportService`, `PdfGenerator`). Ne genere jamais un fichier
temporaire sur disque : le PDF est produit en memoire puis renvoye directement.
"""

import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.reports.formatting import sanitize_filename
from app.reports.pdf_generator import PdfGenerator
from app.reports.report_service import ReportNotValidatedError, ReportResultNotFoundError, ReportService

router = APIRouter(prefix="/api/recommendation-results", tags=["reports"])
logger = logging.getLogger(__name__)

TEMPLATE_VERSION = "1.0"


@router.get("/{result_id}/report.pdf")
def download_recommendation_report(result_id: int, db: Session = Depends(get_db)):
    service = ReportService(db)
    try:
        report_data = service.build_report_data(result_id)
    except ReportResultNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReportNotValidatedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    try:
        pdf_bytes = PdfGenerator().generate(report_data)
    except Exception:
        logger.exception("Echec de generation du rapport PDF pour recommendation_result_id=%s.", result_id)
        raise HTTPException(status_code=500, detail="Impossible de generer le rapport PDF.") from None

    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    try:
        service.record_generation(
            result_id=result_id,
            reference=report_data.reference,
            generated_by=report_data.validation.validator_name,
            content_hash=content_hash,
            version=TEMPLATE_VERSION,
        )
    except Exception:
        db.rollback()
        logger.warning("Tracabilite du rapport non enregistree (non bloquant).", exc_info=True)

    filename = sanitize_filename(f"MAADEN_Consulting_Report_{report_data.reference}") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
