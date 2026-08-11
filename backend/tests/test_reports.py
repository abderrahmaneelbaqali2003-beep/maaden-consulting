"""Tests du rapport PDF de consulting (generation, garde-fou de validation, contenu,
non-regression). `ReportService`/`PdfGenerator` sont exerces via l'endpoint HTTP reel
pour couvrir toute la chaine (route -> service -> generateur PDF)."""

from pypdf import PdfReader
import io

from app.database.models import ExpertValidation, RecommendationResult
from tests.factories import make_driver, make_lens, make_module, make_requirement, make_result, make_run


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _build_full_configuration(db_session, **result_overrides):
    requirement = make_requirement(db_session, persist=True, road_type="urban", pole_height_m=8, pole_spacing_m=30)
    driver = make_driver(db_session, output_power_max_w=150, ip_rating="IP66")
    module = make_module(db_session, led_package="3535", cri_min=80)
    lens = make_lens(db_session, compatible_led_package="3535")
    run = make_run(db_session, requirement)
    result = make_result(db_session, run, driver, module, lens, **result_overrides)
    db_session.flush()
    return requirement, driver, module, lens, run, result


def _validate(db_session, result: RecommendationResult, validator_name: str = "Jean Dupont", comment: str | None = "RAS"):
    result.validation_status = "validated"
    result.validated_by = validator_name
    db_session.add(
        ExpertValidation(
            recommendation_result_id=result.id, validator_name=validator_name, decision="validated", comment=comment
        )
    )
    db_session.flush()


# --- Garde-fou de validation ---


def test_cannot_generate_report_for_pending_result(client, db_session):
    *_rest, result = _build_full_configuration(db_session, validation_status="pending")

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 409
    assert response.json()["detail"] == "La configuration doit etre validee avant la generation du rapport final."


def test_cannot_generate_report_for_rejected_result(client, db_session):
    *_rest, result = _build_full_configuration(db_session, validation_status="rejected")

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 409


def test_generate_report_for_validated_result(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 200
    assert len(response.content) > 1000


# --- Format de la reponse ---


def test_report_content_type_is_pdf(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.headers["content-type"] == "application/pdf"


def test_report_filename(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    disposition = response.headers["content-disposition"]
    assert "attachment" in disposition
    assert "MAADEN_Consulting_Report_MC-" in disposition
    assert ".pdf" in disposition


def test_report_contains_report_reference(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert f"MC-" in text
    assert f"{result.id:06d}" in text


# --- Contenu ---


def test_report_contains_driver(client, db_session):
    requirement, driver, module, lens, run, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert driver.reference in text


def test_report_contains_module(client, db_session):
    requirement, driver, module, lens, run, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert module.reference in text


def test_report_contains_lens(client, db_session):
    requirement, driver, module, lens, run, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert lens.reference in text


def test_report_contains_technical_score(client, db_session):
    *_rest, result = _build_full_configuration(db_session, overall_score=91.0)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert "91" in text
    assert "Score technique" in text or "Score global" in text


def test_report_contains_calculations(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert "Calculs techniques" in text


def test_report_contains_validator(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result, validator_name="Amine Consultant")

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    text = _pdf_text(response.content)
    assert "Amine Consultant" in text


# --- Robustesse aux donnees manquantes ---


def test_report_handles_missing_lens(client, db_session):
    requirement = make_requirement(db_session, persist=True)
    driver = make_driver(db_session)
    module = make_module(db_session)
    run = make_run(db_session, requirement)
    result = make_result(db_session, run, driver, module, None)
    db_session.flush()
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Non renseigne" in text or "Aucune lentille" in text


def test_report_handles_missing_documentary_evidence(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "Aucune preuve documentaire" in text


def test_report_handles_missing_optional_project_fields(client, db_session):
    requirement = make_requirement(
        db_session,
        persist=True,
        pole_height_m=None,
        pole_spacing_m=None,
        road_type=None,
        road_width_m=None,
        road_length_m=None,
    )
    driver = make_driver(db_session)
    module = make_module(db_session)
    run = make_run(db_session, requirement)
    result = make_result(db_session, run, driver, module, None)
    db_session.flush()
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")

    assert response.status_code == 200
    text = _pdf_text(response.content)
    assert "None" not in text
    assert "null" not in text
    assert "Non renseigne" in text


# --- Non-regression / lecture seule ---


def test_pdf_generation_does_not_modify_score(client, db_session):
    *_rest, result = _build_full_configuration(db_session, overall_score=77.5)
    _validate(db_session, result)
    result_id = result.id

    response = client.get(f"/api/recommendation-results/{result_id}/report.pdf")
    assert response.status_code == 200

    db_session.expire_all()
    refreshed = db_session.get(RecommendationResult, result_id)
    assert refreshed.overall_score == 77.5


def test_pdf_generation_does_not_modify_validation_rules(client, db_session):
    rules = ["Tension compatible avec la plage du driver.", "Marge de puissance de 25% (minimum requis : 10%)."]
    *_rest, result = _build_full_configuration(db_session, validated_rules=rules)
    _validate(db_session, result)
    result_id = result.id

    response = client.get(f"/api/recommendation-results/{result_id}/report.pdf")
    assert response.status_code == 200

    db_session.expire_all()
    refreshed = db_session.get(RecommendationResult, result_id)
    assert refreshed.validated_rules == rules


def test_report_generation_is_fully_read_only(client, db_session):
    """Non-regression : technical_score, driver/module/lens et validated_rules identiques
    avant et apres generation du PDF (preuve que le generateur ne fait que lire)."""
    requirement, driver, module, lens, run, result = _build_full_configuration(db_session)
    _validate(db_session, result)
    result_id = result.id

    before = (result.overall_score, result.driver_id, result.module_id, result.lens_id, list(result.validated_rules))

    response = client.get(f"/api/recommendation-results/{result_id}/report.pdf")
    assert response.status_code == 200

    db_session.expire_all()
    refreshed = db_session.get(RecommendationResult, result_id)
    after = (refreshed.overall_score, refreshed.driver_id, refreshed.module_id, refreshed.lens_id, list(refreshed.validated_rules))

    assert before == after


# --- Validation par resultat (bug rank-1 corrige) ---


def test_validate_targets_the_requested_result_not_rank_one(client, db_session):
    requirement = make_requirement(db_session, persist=True)
    driver = make_driver(db_session)
    module = make_module(db_session)
    run = make_run(db_session, requirement)
    result_rank1 = make_result(db_session, run, driver, module, None, rank=1)
    result_rank2 = make_result(db_session, run, driver, module, None, rank=2)
    db_session.flush()

    response = client.post(
        f"/api/recommendation-results/{result_rank2.id}/validate",
        json={"validator_name": "Sara Ingenieur", "comment": "Choix consultant"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(RecommendationResult, result_rank2.id).validation_status == "validated"
    assert db_session.get(RecommendationResult, result_rank1.id).validation_status == "pending"


def test_validate_requires_validator_name(client, db_session):
    *_rest, result = _build_full_configuration(db_session)

    response = client.post(f"/api/recommendation-results/{result.id}/validate", json={"comment": "sans nom"})

    assert response.status_code == 422


def test_rejected_result_cannot_be_validated_into_a_report(client, db_session):
    *_rest, result = _build_full_configuration(db_session)

    reject_response = client.post(
        f"/api/recommendation-results/{result.id}/reject", json={"validator_name": "Sara Ingenieur"}
    )
    assert reject_response.status_code == 200

    report_response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")
    assert report_response.status_code == 409


# --- CORS : localhost et 127.0.0.1 sont deux origines distinctes pour le navigateur ---
# (root cause d'un bug de telechargement PDF signale en production : le frontend etait
# ouvert via 127.0.0.1:5173 alors que seul localhost:5173 etait autorise cote backend.)


def test_cors_allows_localhost_frontend(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(
        f"/api/recommendation-results/{result.id}/report.pdf", headers={"Origin": "http://localhost:5173"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_allows_127_frontend(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(
        f"/api/recommendation-results/{result.id}/report.pdf", headers={"Origin": "http://127.0.0.1:5173"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_exposes_content_disposition_header(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(
        f"/api/recommendation-results/{result.id}/report.pdf", headers={"Origin": "http://localhost:5173"}
    )

    assert "Content-Disposition" in response.headers.get("access-control-expose-headers", "")


def test_report_pdf_does_not_duplicate_pages(client, db_session):
    """Non-regression : le canvas ReportLab a 2 passes (`_NumberedCanvas`, pour la
    pagination "Page X / Y") ne doit committer chaque page qu'une seule fois. Un bug
    precedent appelait `super().showPage()` dans l'override, ce qui validait la page
    immediatement PUIS une seconde fois dans `save()` -> rapport entierement duplique."""
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(f"/api/recommendation-results/{result.id}/report.pdf")
    assert response.status_code == 200

    reader = PdfReader(io.BytesIO(response.content))
    texts = [page.extract_text() or "" for page in reader.pages]

    cover_occurrences = sum(1 for t in texts if "RAPPORT DE RECOMMANDATION" in t)
    assert cover_occurrences == 1

    section1_occurrences = sum(1 for t in texts if "Informations du projet" in t)
    assert section1_occurrences == 1

    section10_occurrences = sum(1 for t in texts if "Validation du consultant" in t)
    assert section10_occurrences == 1

    last_page_text = texts[-1]
    assert f"Page {len(reader.pages)} / {len(reader.pages)}" in last_page_text


def test_cors_rejects_unlisted_origin(client, db_session):
    *_rest, result = _build_full_configuration(db_session)
    _validate(db_session, result)

    response = client.get(
        f"/api/recommendation-results/{result.id}/report.pdf", headers={"Origin": "http://evil.example.com"}
    )

    # La reponse applicative reste 200 (CORSMiddleware ne bloque pas la requete cote serveur),
    # mais l'en-tete d'autorisation est absent : c'est le navigateur qui bloquera la lecture de
    # la reponse cote JS. On verifie ici que le backend n'echoue jamais une origine non listee.
    assert "access-control-allow-origin" not in response.headers
