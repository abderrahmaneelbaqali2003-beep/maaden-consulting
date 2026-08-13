"""Pipeline CPS specifique : import de fichier -> extraction par regex -> validation
humaine des exigences. La logique d'analyse de suffisance et de construction du
`RecommendationRequest` (partagee avec l'assistant IA) vit dans `app/domain/`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.cps.extractor import CpsExtractor
from app.cps.storage import save_upload
from app.database.models import CpsDocument, CpsDocumentPage, ExtractedRequirement
from app.domain.history import log_project_event
from app.rag.parsing import ParsedPage, PdfDocumentParser


class CpsDocumentNotFoundError(Exception):
    pass


class RequirementNotFoundError(Exception):
    pass


class CpsService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    def import_document(self, project_id: int, original_filename: str, content: bytes) -> CpsDocument:
        path, stored_filename, file_hash = save_upload(project_id, original_filename, content)

        document = CpsDocument(
            project_id=project_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            document_type="pdf",
            file_hash=file_hash,
            page_count=0,
            uploaded_at=datetime.now(timezone.utc),
            extraction_status="pending",
        )
        self.db.add(document)
        self.db.flush()

        try:
            pages: list[ParsedPage] = PdfDocumentParser().parse(path)
        except Exception as exc:
            document.extraction_status = "failed"
            document.extraction_message = f"Lecture du PDF impossible : {exc}"
            self.db.flush()
            log_project_event(self.db, project_id, "cps_uploaded", details={"status": "failed"})
            return document

        document.page_count = len(pages)

        if not CpsExtractor().has_sufficient_text(pages):
            document.extraction_status = "insufficient_text"
            document.extraction_message = (
                "Document probablement scanne. Extraction automatique insuffisante. "
                "OCR ou saisie manuelle necessaire."
            )
        else:
            document.extraction_status = "extracted"
            for page in pages:
                if page.text.strip():
                    self.db.add(CpsDocumentPage(cps_document_id=document.id, page_number=page.page_number, text=page.text))

        self.db.flush()
        log_project_event(
            self.db, project_id, "cps_uploaded", details={"status": document.extraction_status, "pages": len(pages)}
        )
        return document

    def extract_requirements(self, project_id: int, cps_document_id: int) -> list[ExtractedRequirement]:
        document = self.db.get(CpsDocument, cps_document_id)
        if document is None or document.project_id != project_id:
            raise CpsDocumentNotFoundError(f"Document CPS {cps_document_id} introuvable pour ce projet.")

        pages_rows = (
            self.db.query(CpsDocumentPage)
            .filter(CpsDocumentPage.cps_document_id == cps_document_id)
            .order_by(CpsDocumentPage.page_number)
            .all()
        )
        pages = [ParsedPage(page_number=row.page_number, text=row.text) for row in pages_rows]

        drafts = CpsExtractor().extract(pages)
        created: list[ExtractedRequirement] = []
        for draft in drafts:
            row = ExtractedRequirement(
                project_id=project_id,
                cps_document_id=cps_document_id,
                category=draft.category,
                scope=draft.scope,
                field_name=draft.field_name,
                operator=draft.operator,
                raw_value=draft.raw_value,
                numeric_value=draft.numeric_value,
                unit=draft.unit,
                source_page=draft.source_page,
                source_excerpt=draft.source_excerpt,
                extraction_confidence=draft.extraction_confidence,
                validation_status="detected",
                source_type="cps",
            )
            self.db.add(row)
            created.append(row)

        self.db.flush()
        log_project_event(self.db, project_id, "requirements_extracted", details={"count": len(created)})
        return created

    def add_manual_requirement(
        self, project_id: int, category: str, scope: str, field_name: str, operator: str, value: str, unit: str | None,
        actor: str | None, source_type: str = "manual",
    ) -> ExtractedRequirement:
        try:
            numeric_value = float(value.replace(",", "."))
        except ValueError:
            numeric_value = None

        row = ExtractedRequirement(
            project_id=project_id, cps_document_id=None, category=category, scope=scope, field_name=field_name,
            operator=operator, raw_value=value, numeric_value=numeric_value, unit=unit,
            extraction_confidence="high", validation_status="manual", source_type=source_type,
            validated_value=value, validated_by=actor, validated_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.flush()
        log_project_event(self.db, project_id, "manual_requirement_added", actor=actor, details={"field_name": field_name})
        return row

    def update_requirement(
        self, project_id: int, requirement_id: int, action: str, validated_value: str | None, actor: str | None,
    ) -> ExtractedRequirement:
        row = self.db.get(ExtractedRequirement, requirement_id)
        if row is None or row.project_id != project_id:
            raise RequirementNotFoundError(f"Exigence {requirement_id} introuvable pour ce projet.")

        if action == "confirm":
            row.validation_status = "confirmed"
            row.validated_value = row.raw_value
            history_action = "requirement_confirmed"
        elif action == "modify":
            row.validation_status = "modified"
            row.validated_value = validated_value
            if validated_value:
                try:
                    row.numeric_value = float(validated_value.replace(",", "."))
                except ValueError:
                    pass
            history_action = "requirement_modified"
        elif action == "ignore":
            row.validation_status = "ignored"
            history_action = "requirement_ignored"
        else:
            raise ValueError(f"Action de validation inconnue : {action}")

        row.validated_by = actor
        row.validated_at = datetime.now(timezone.utc)
        self.db.flush()
        log_project_event(
            self.db, project_id, history_action,
            actor=actor, details={"requirement_id": requirement_id, "field_name": row.field_name},
        )
        return row
