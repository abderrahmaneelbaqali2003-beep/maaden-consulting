"""Orchestration du pipeline CPS : import -> extraction -> validation humaine ->
transformation vers `RecommendationRequest`. Ne decide jamais de compatibilite :
produit uniquement les entrees du calculateur/moteur deterministe existants.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.cps.extractor import CpsExtractor
from app.cps.storage import save_upload
from app.database.models import CpsDocument, CpsDocumentPage, ExtractedRequirement, ProjectHistory
from app.rag.parsing import ParsedPage, PdfDocumentParser
from app.schemas.recommendation import RecommendationRequest

# (scope, field_name) -> attribut de RecommendationRequest. Les exigences dont le couple
# n'a pas de correspondance ici restent tracees en base mais ne pilotent pas le moteur
# (ex: IP66/IK10 luminaire : verifiees ailleurs, jamais transformees en regle driver/module).
REQUEST_FIELD_MAP: dict[tuple[str, str], str] = {
    ("luminaire", "required_flux_lm"): "required_flux_lm",
    ("luminaire", "max_power_w"): "max_power_w",
    ("luminaire", "cct_k"): "required_cct_k",
    ("module", "voltage_nominal_v"): "voltage_nominal_v",
    ("module", "current_nominal_ma"): "current_nominal_ma",
    ("driver", "protocol"): "protocol",
    ("luminaire", "led_package"): "led_package",
    ("road", "road_type"): "road_type",
    ("road", "pole_height_m"): "pole_height_m",
    ("road", "pole_spacing_m"): "pole_spacing_m",
    ("road", "road_width_m"): "road_width_m",
    ("road", "road_length_m"): "road_length_m",
    ("system", "layout_type"): "layout_type",
    ("environment", "ambient_temperature_c"): "ambient_temperature_c",
    ("system", "operating_hours_per_year"): "operating_hours_per_year",
    ("system", "energy_price_per_kwh"): "energy_price_per_kwh",
}

MANDATORY_FIELDS = [
    "required_flux_lm",
    "max_power_w",
    "required_cct_k",
    "voltage_nominal_v",
    "current_nominal_ma",
]

MANDATORY_FIELD_LABELS = {
    "required_flux_lm": "Flux lumineux requis",
    "max_power_w": "Puissance maximale",
    "required_cct_k": "Temperature de couleur (CCT)",
    "voltage_nominal_v": "Tension nominale du module",
    "current_nominal_ma": "Courant nominal du module",
}

NUMERIC_FIELDS = {
    "required_flux_lm", "max_power_w", "required_cct_k", "voltage_nominal_v", "current_nominal_ma",
    "pole_height_m", "pole_spacing_m", "road_width_m", "road_length_m",
    "ambient_temperature_c", "operating_hours_per_year", "energy_price_per_kwh",
}


class CpsDocumentNotFoundError(Exception):
    pass


class RequirementNotFoundError(Exception):
    pass


class MissingMandatoryFieldsError(Exception):
    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields
        labels = ", ".join(MANDATORY_FIELD_LABELS.get(f, f) for f in missing_fields)
        super().__init__(f"Champs obligatoires manquants pour lancer l'etude : {labels}.")


def _log(db: Session, project_id: int, action: str, actor: str | None = None, details: dict | None = None) -> None:
    db.add(
        ProjectHistory(
            project_id=project_id, action=action, actor=actor, details=details or {},
            created_at=datetime.now(timezone.utc),
        )
    )


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
            _log(self.db, project_id, "cps_uploaded", details={"status": "failed"})
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
        _log(self.db, project_id, "cps_uploaded", details={"status": document.extraction_status, "pages": len(pages)})
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
            )
            self.db.add(row)
            created.append(row)

        self.db.flush()
        _log(self.db, project_id, "requirements_extracted", details={"count": len(created)})
        return created

    def add_manual_requirement(
        self, project_id: int, category: str, scope: str, field_name: str, operator: str, value: str, unit: str | None,
        actor: str | None,
    ) -> ExtractedRequirement:
        try:
            numeric_value = float(value.replace(",", "."))
        except ValueError:
            numeric_value = None

        row = ExtractedRequirement(
            project_id=project_id, cps_document_id=None, category=category, scope=scope, field_name=field_name,
            operator=operator, raw_value=value, numeric_value=numeric_value, unit=unit,
            extraction_confidence="high", validation_status="manual",
            validated_value=value, validated_by=actor, validated_at=datetime.now(timezone.utc),
        )
        self.db.add(row)
        self.db.flush()
        _log(self.db, project_id, "requirement_added_manually", actor=actor, details={"field_name": field_name})
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
        elif action == "modify":
            row.validation_status = "modified"
            row.validated_value = validated_value
            if validated_value:
                try:
                    row.numeric_value = float(validated_value.replace(",", "."))
                except ValueError:
                    pass
        elif action == "ignore":
            row.validation_status = "ignored"
        else:
            raise ValueError(f"Action de validation inconnue : {action}")

        row.validated_by = actor
        row.validated_at = datetime.now(timezone.utc)
        self.db.flush()
        _log(
            self.db, project_id, f"requirement_{action}",
            actor=actor, details={"requirement_id": requirement_id, "field_name": row.field_name},
        )
        return row

    # ------------------------------------------------------------------
    def build_recommendation_request(self, project_id: int) -> RecommendationRequest:
        rows = (
            self.db.query(ExtractedRequirement)
            .filter(
                ExtractedRequirement.project_id == project_id,
                ExtractedRequirement.validation_status.in_(["confirmed", "modified", "manual"]),
            )
            .all()
        )

        values: dict[str, object] = {}
        for row in rows:
            attr = REQUEST_FIELD_MAP.get((row.scope, row.field_name))
            if attr is None:
                continue
            effective_raw = row.validated_value or row.raw_value
            if attr in NUMERIC_FIELDS:
                if row.numeric_value is not None:
                    values[attr] = row.numeric_value
            else:
                values[attr] = effective_raw

        missing = [f for f in MANDATORY_FIELDS if f not in values]
        if missing:
            raise MissingMandatoryFieldsError(missing)

        if "required_cct_k" in values:
            values["required_cct_k"] = int(values["required_cct_k"])

        return RecommendationRequest(project_id=project_id, **values)
