"""Assemble les donnees du rapport PDF de consulting.

Regle absolue : ce service ne fait que LIRE des donnees deja calculees/persistees
par le moteur deterministe (`RecommendationResult`), le calculateur
(`CalculationService`, calcul pur reutilise tel quel) et l'enrichissement
documentaire (`RecommendationEvidence`). Il ne modifie jamais `overall_score`,
ne recalcule jamais la compatibilite, ne modifie jamais `is_compatible`, ne
change jamais le classement ni le driver/module/lentille retenus, et ne
transforme jamais une preuve documentaire en regle bloquante.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.calculations.service import CalculationService
from app.database.models import (
    Driver,
    ExpertValidation,
    GeneratedReport,
    LedModule,
    Lens,
    ProjectRequirement,
    RagDocument,
    RagDocumentChunk,
    RecommendationEvidence,
    RecommendationResult,
    RecommendationRun,
)
from app.reports.formatting import build_report_reference, relevance_label_by_rank
from app.reports.models import (
    ReportData,
    ReportDocumentaryData,
    ReportDriverData,
    ReportEvidenceData,
    ReportLensData,
    ReportModuleData,
    ReportProjectData,
    ReportScoresData,
    ReportValidationData,
)

logger = logging.getLogger(__name__)


class ReportResultNotFoundError(Exception):
    pass


class ReportNotValidatedError(Exception):
    pass


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    def build_report_data(self, result_id: int) -> ReportData:
        result = self.db.get(RecommendationResult, result_id)
        if result is None:
            raise ReportResultNotFoundError(f"Configuration recommandee {result_id} introuvable.")
        if result.validation_status != "validated":
            raise ReportNotValidatedError(
                "La configuration doit etre validee avant la generation du rapport final."
            )

        run = self.db.get(RecommendationRun, result.run_id)
        requirement = self.db.get(ProjectRequirement, run.requirement_id) if run else None
        driver = self.db.get(Driver, result.driver_id)
        module = self.db.get(LedModule, result.module_id)
        lens = self.db.get(Lens, result.lens_id) if result.lens_id else None

        calculations = CalculationService().for_configuration(requirement, driver, module, lens)

        validation = self._latest_validation(result.id)
        documentary = self._documentary(result.id)
        remaining_validations = self._remaining_validations(result, documentary)
        reference = build_report_reference(result.id, validation.validated_at.year if validation else datetime.now(timezone.utc).year)

        return ReportData(
            reference=reference,
            generated_at=datetime.now(timezone.utc),
            project=self._project_data(requirement),
            driver=self._driver_data(driver) if driver else None,
            module=self._module_data(module),
            lens=self._lens_data(lens) if lens else None,
            scores=ReportScoresData(
                overall=result.overall_score,
                electrical=result.score_electrical,
                photometric=result.score_photometric,
                mechanical=result.score_mechanical,
                thermal=result.score_thermal,
                data_quality=result.score_data_quality,
            ),
            calculations=calculations,
            validated_rules=result.validated_rules or [],
            warnings=result.warnings or [],
            blocking_reasons=result.blocking_reasons or [],
            documentary=documentary,
            remaining_validations=remaining_validations,
            conclusion=self._conclusion(result, documentary),
            validation=validation
            or ReportValidationData(validator_name=result.validated_by or "Non renseigne", validated_at=datetime.now(timezone.utc)),
        )

    def record_generation(
        self, result_id: int, reference: str, generated_by: str, content_hash: str, version: str
    ) -> GeneratedReport:
        record = GeneratedReport(
            recommendation_result_id=result_id,
            report_reference=reference,
            report_type="technical_recommendation",
            generated_by=generated_by,
            generated_at=datetime.now(timezone.utc),
            content_hash=content_hash,
            version=version,
        )
        self.db.add(record)
        self.db.commit()
        return record

    # ------------------------------------------------------------------
    # Construction des sous-sections
    # ------------------------------------------------------------------

    def _latest_validation(self, result_id: int) -> ReportValidationData | None:
        row = (
            self.db.query(ExpertValidation)
            .filter(ExpertValidation.recommendation_result_id == result_id, ExpertValidation.decision == "validated")
            .order_by(ExpertValidation.created_at.desc())
            .first()
        )
        if row is None or not row.validator_name:
            return None
        return ReportValidationData(
            validator_name=row.validator_name,
            validated_at=row.created_at,
            comment=row.comment,
        )

    def _project_data(self, requirement: ProjectRequirement | None) -> ReportProjectData:
        if requirement is None:
            raise ReportResultNotFoundError("Besoins projet introuvables pour cette recommandation.")
        return ReportProjectData(
            road_type=requirement.road_type,
            road_width_m=requirement.road_width_m,
            road_length_m=requirement.road_length_m,
            pole_height_m=requirement.pole_height_m,
            pole_spacing_m=requirement.pole_spacing_m,
            layout_type=requirement.layout_type,
            required_flux_lm=requirement.required_flux_lm,
            required_cct_k=requirement.required_cct_k,
            max_power_w=requirement.max_power_w,
            voltage_nominal_v=requirement.voltage_nominal_v,
            current_nominal_ma=requirement.current_nominal_ma,
            protocol=requirement.protocol,
            led_package=requirement.led_package,
            ambient_temperature_c=requirement.ambient_temperature_c,
        )

    def _driver_data(self, driver: Driver) -> ReportDriverData:
        protocols = []
        if driver.dimming_0_10v:
            protocols.append("0-10V")
        if driver.dimming_1_10v:
            protocols.append("1-10V")
        if driver.dali_2:
            protocols.append("DALI-2")
        if driver.d4i:
            protocols.append("D4i")
        if driver.pwm_dimming:
            protocols.append("PWM")
        if driver.resistance_dimming:
            protocols.append("Resistif")
        return ReportDriverData(
            manufacturer=driver.manufacturer.name,
            reference=driver.reference,
            product_family=driver.product_family,
            output_power_max_w=driver.output_power_max_w,
            output_voltage_min_v=driver.output_voltage_min_v,
            output_voltage_max_v=driver.output_voltage_max_v,
            output_current_min_ma=driver.output_current_min_ma,
            output_current_max_ma=driver.output_current_max_ma,
            efficiency_percent=driver.efficiency_percent,
            dimmable=driver.dimmable,
            dali_2=driver.dali_2,
            d4i=driver.d4i,
            protocols=protocols,
            ip_rating=driver.ip_rating,
            ce_certified=driver.ce_certified,
            enec_certified=driver.enec_certified,
            ul_certified=driver.ul_certified,
            rohs_compliant=driver.rohs_compliant,
            certifications=driver.certifications,
        )

    def _module_data(self, module: LedModule) -> ReportModuleData:
        return ReportModuleData(
            manufacturer=module.manufacturer.name,
            reference=module.reference,
            product_family=module.product_family,
            led_package=module.led_package,
            led_quantity=module.led_quantity,
            input_voltage_nominal_v=module.input_voltage_nominal_v,
            current_nominal_ma=module.current_nominal_ma,
            power_nominal_w=module.power_nominal_w,
            luminous_flux_nominal_lm=module.luminous_flux_nominal_lm,
            luminous_efficacy_nominal_lm_w=module.luminous_efficacy_nominal_lm_w,
            cct_nominal_k=module.cct_nominal_k,
            cri_min=module.cri_min,
            lifetime_hours=module.lifetime_hours,
            ce_certified=module.ce_certified,
            enec_certified=module.enec_certified,
            ul_certified=module.ul_certified,
            rohs_compliant=module.rohs_compliant,
            ip_rating=module.ip_rating,
            certifications=module.certifications,
        )

    def _lens_data(self, lens: Lens) -> ReportLensData:
        return ReportLensData(
            manufacturer=lens.manufacturer.name,
            reference=lens.reference,
            compatible_led_package=lens.compatible_led_package,
            optical_cells_quantity=lens.optical_cells_quantity,
            rows_count=lens.rows_count,
            columns_count=lens.columns_count,
            lens_pitch_x_mm=lens.lens_pitch_x_mm,
            lens_pitch_y_mm=lens.lens_pitch_y_mm,
            iesna_distribution_type=lens.iesna_distribution_type,
            beam_angle_horizontal_deg=lens.beam_angle_horizontal_deg,
            ies_file_available=lens.ies_file_available,
            ldt_file_available=lens.ldt_file_available,
            length_mm=lens.length_mm,
            width_mm=lens.width_mm,
            height_mm=lens.height_mm,
            diameter_mm=lens.diameter_mm,
            operating_temperature_max_c=lens.operating_temperature_max_c,
        )

    def _documentary(self, result_id: int) -> ReportDocumentaryData:
        try:
            rows = (
                self.db.query(RecommendationEvidence, RagDocumentChunk, RagDocument)
                .outerjoin(RagDocumentChunk, RecommendationEvidence.document_chunk_id == RagDocumentChunk.id)
                .outerjoin(RagDocument, RagDocumentChunk.document_id == RagDocument.id)
                .filter(RecommendationEvidence.recommendation_result_id == result_id)
                .order_by(RecommendationEvidence.relevance_score.desc())
                .all()
            )
        except Exception:
            logger.warning("Synthese documentaire indisponible pour recommendation_result_id=%s.", result_id, exc_info=True)
            return ReportDocumentaryData(confidence="insufficient_evidence")

        evidence: list[ReportEvidenceData] = []
        missing: list[str] = []
        rank = 0
        for rec_evidence, chunk, document in rows:
            if rec_evidence.evidence_type == "missing_evidence" or document is None:
                if rec_evidence.claim not in missing:
                    missing.append(rec_evidence.claim)
                continue
            evidence.append(
                ReportEvidenceData(
                    category=rec_evidence.evidence_type,
                    document=document.title,
                    section=chunk.section_title if chunk else None,
                    page=chunk.page_number if chunk else None,
                    summary=rec_evidence.claim,
                    verification_status=rec_evidence.verification_status,
                    relevance_label=relevance_label_by_rank(rank),
                )
            )
            rank += 1

        if not evidence and not missing:
            return ReportDocumentaryData(confidence="insufficient_evidence")

        from app.services.evidence_enrichment_service import compute_confidence

        categories = {item.category for item in evidence}
        confidence = (
            compute_confidence(
                has_product="module_standard" in categories or "driver_standard" in categories,
                has_photometric_or_road="road_lighting" in categories or "photometric" in categories,
                has_normative="luminaire_standard" in categories or "smart_lighting" in categories,
                missing_count=len(missing),
            )
            if evidence
            else "insufficient_evidence"
        )
        return ReportDocumentaryData(confidence=confidence, evidence=evidence, missing_evidence=missing)

    def _remaining_validations(self, result: RecommendationResult, documentary: ReportDocumentaryData) -> list[str]:
        items: list[str] = []
        for text in list(result.warnings or []) + documentary.missing_evidence:
            if text not in items:
                items.append(text)
        return items

    def _conclusion(self, result: RecommendationResult, documentary: ReportDocumentaryData) -> str:
        """Genere un paragraphe de conclusion 100% deterministe (aucun LLM) : un gabarit
        textuel dont les phrases s'activent/desactivent selon les donnees reellement
        disponibles pour cette configuration."""
        sentences: list[str] = []
        sentences.append(
            f"La configuration proposee obtient un score technique global de {result.overall_score}/100 "
            "au regard du moteur de compatibilite deterministe."
        )
        if result.validated_rules:
            sentences.append(
                f"{len(result.validated_rules)} critere(s) technique(s) ont ete valides sur les regles de "
                "compatibilite electrique, photometrique, mecanique et thermique."
            )
        if result.warnings:
            sentences.append(
                f"{len(result.warnings)} point(s) de vigilance ont ete identifies et doivent etre pris en "
                "compte avant la mise en oeuvre."
            )
        confidence_sentences = {
            "high": "La documentation normative disponible offre un niveau de confiance eleve pour cette configuration.",
            "medium": "La documentation normative disponible offre un niveau de confiance moyen : certains points restent a corroborer.",
            "low": "La documentation normative disponible reste limitee : une verification manuelle complementaire est recommandee.",
            "insufficient_evidence": "Aucune preuve documentaire suffisante n'a ete retrouvee pour cette configuration : une verification manuelle est necessaire.",
        }
        sentences.append(confidence_sentences.get(documentary.confidence, confidence_sentences["insufficient_evidence"]))
        sentences.append(
            "Cette conclusion est generee automatiquement a partir des donnees du moteur deterministe et de "
            "la base documentaire ; elle ne remplace pas l'analyse finale d'un ingenieur qualifie."
        )
        return " ".join(sentences)
