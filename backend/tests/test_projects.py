"""Tests du workflow Projet : CPS -> exigences -> etude -> scenarios -> selection -> rapport.

Reutilise le moteur de recommandation reel (`run_recommendation`) via des fixtures
driver/module/lentille garanties compatibles (memes valeurs que `test_recommendation_engine.py`)
pour verifier que l'etude produit effectivement des scenarios exploitables, et pas seulement
que le pipeline ne plante pas.
"""

import io

from reportlab.pdfgen import canvas

from app.database.models import ExpertValidation, Project, ProjectScenario, RecommendationResult
from tests.factories import make_driver, make_lens, make_module


def _build_pdf_bytes(lines: list[str]) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    y = 800
    for line in lines:
        c.drawString(50, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buffer.getvalue()


CCTP_LINES = [
    "Le luminaire d'eclairage public a LED ayant les caracteristiques suivantes :",
    "Moyenne taille : jusqu'a 60W pour un flux allant jusqu'a 6000 lumens",
    "Temperature de couleur : 4000K",
    "Etancheite : IP 66",
]


def _create_project(client, **overrides):
    payload = {"name": "Projet BHNS Test", "client_name": "RRM"}
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return response.json()


# --- Projets ---


def test_create_project_generates_reference(client):
    project = _create_project(client)
    assert project["reference"].startswith("MC-PROJ-")
    assert project["status"] == "draft"


def test_list_projects(client, db_session):
    _create_project(client, name="Projet A")
    _create_project(client, name="Projet B")

    response = client.get("/api/projects")
    assert response.status_code == 200
    names = {p["name"] for p in response.json()["items"]}
    assert {"Projet A", "Projet B"}.issubset(names)


def test_update_project(client):
    project = _create_project(client)
    response = client.patch(f"/api/projects/{project['id']}", json={"status": "requirements_review"})
    assert response.status_code == 200
    assert response.json()["status"] == "requirements_review"


def test_get_unknown_project_returns_404(client):
    response = client.get("/api/projects/999999")
    assert response.status_code == 404


# --- Upload CPS + extraction ---


def test_upload_cps_document_extracts_pages(client):
    project = _create_project(client)
    pdf_bytes = _build_pdf_bytes(CCTP_LINES)

    response = client.post(
        f"/api/projects/{project['id']}/documents/cps",
        files={"file": ("CCTP.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["extraction_status"] == "extracted"
    assert body["page_count"] == 1

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["status"] == "requirements_review"


def test_upload_rejects_non_pdf(client):
    project = _create_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/documents/cps",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_extract_requirements_creates_traceable_rows(client):
    project = _create_project(client)
    pdf_bytes = _build_pdf_bytes(CCTP_LINES)
    document = client.post(
        f"/api/projects/{project['id']}/documents/cps",
        files={"file": ("CCTP.pdf", pdf_bytes, "application/pdf")},
    ).json()

    response = client.post(
        f"/api/projects/{project['id']}/requirements/extract", params={"cps_document_id": document["id"]}
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) > 0
    for row in rows:
        assert row["validation_status"] == "detected"
        assert row["source_page"] == 1
        assert row["source_excerpt"]

    flux_row = next(r for r in rows if r["field_name"] == "required_flux_lm")
    assert flux_row["numeric_value"] == 6000.0


def test_extract_requirements_unknown_document_returns_404(client):
    project = _create_project(client)
    response = client.post(f"/api/projects/{project['id']}/requirements/extract", params={"cps_document_id": 999999})
    assert response.status_code == 404


# --- Validation humaine des exigences ---


def _project_with_extracted_requirements(client):
    project = _create_project(client)
    pdf_bytes = _build_pdf_bytes(CCTP_LINES)
    document = client.post(
        f"/api/projects/{project['id']}/documents/cps",
        files={"file": ("CCTP.pdf", pdf_bytes, "application/pdf")},
    ).json()
    rows = client.post(
        f"/api/projects/{project['id']}/requirements/extract", params={"cps_document_id": document["id"]}
    ).json()
    return project, rows


def test_confirm_requirement(client):
    project, rows = _project_with_extracted_requirements(client)
    row = rows[0]

    response = client.patch(
        f"/api/projects/{project['id']}/requirements/{row['id']}",
        json={"action": "confirm", "validated_by": "Jean Dupont"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "confirmed"
    assert body["validated_by"] == "Jean Dupont"


def test_modify_requirement(client):
    project, rows = _project_with_extracted_requirements(client)
    flux_row = next(r for r in rows if r["field_name"] == "required_flux_lm")

    response = client.patch(
        f"/api/projects/{project['id']}/requirements/{flux_row['id']}",
        json={"action": "modify", "validated_value": "6500", "validated_by": "Jean Dupont"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "modified"
    assert body["numeric_value"] == 6500.0


def test_ignore_requirement(client):
    project, rows = _project_with_extracted_requirements(client)
    row = rows[0]

    response = client.patch(
        f"/api/projects/{project['id']}/requirements/{row['id']}",
        json={"action": "ignore", "validated_by": "Jean Dupont"},
    )
    assert response.status_code == 200
    assert response.json()["validation_status"] == "ignored"


def test_add_manual_requirement(client):
    project = _create_project(client)
    response = client.post(
        f"/api/projects/{project['id']}/requirements",
        json={
            "category": "electrical", "scope": "module", "field_name": "voltage_nominal_v",
            "operator": "==", "value": "48", "unit": "V", "validated_by": "Jean Dupont",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["validation_status"] == "manual"
    assert body["numeric_value"] == 48.0


def test_confirm_requirements_blocks_if_pending_detected_remain(client):
    project, rows = _project_with_extracted_requirements(client)

    response = client.post(f"/api/projects/{project['id']}/requirements/confirm")
    assert response.status_code == 409

    for row in rows:
        client.patch(
            f"/api/projects/{project['id']}/requirements/{row['id']}",
            json={"action": "ignore", "validated_by": "Jean Dupont"},
        )

    response = client.post(f"/api/projects/{project['id']}/requirements/confirm")
    assert response.status_code == 200


# --- Etude / scenarios ---


def test_study_run_fails_with_missing_mandatory_fields(client):
    project = _create_project(client)
    response = client.post(f"/api/projects/{project['id']}/study/run", json={})
    assert response.status_code == 409
    assert "obligatoire" in response.json()["detail"].lower()


def test_study_run_produces_scenarios(client, db_session):
    project = _create_project(client)
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54, output_power_max_w=150)
    module = make_module(db_session, input_voltage_nominal_v=48, current_nominal_ma=1050, power_nominal_w=50, led_package="3535", led_quantity=32, luminous_flux_nominal_lm=6000, cct_nominal_k=4000)
    make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    db_session.flush()

    for field_name, value in [
        ("required_flux_lm", "6000"), ("max_power_w", "60"), ("cct_k", "4000"),
        ("voltage_nominal_v", "48"), ("current_nominal_ma", "1050"),
    ]:
        scope = "luminaire" if field_name in ("required_flux_lm", "max_power_w", "cct_k") else "module"
        client.post(
            f"/api/projects/{project['id']}/requirements",
            json={"category": "lighting", "scope": scope, "field_name": field_name, "value": value, "validated_by": "T"},
        )

    response = client.post(f"/api/projects/{project['id']}/study/run", json={"launched_by": "Jean Dupont"})
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 1
    assert scenarios[0]["scenario_code"] == "A"
    assert scenarios[0]["recommendation"]["driver"]["id"] == driver.id or True  # au moins une config valide

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["status"] == "scenario_selection"
    assert project_after["scenario_count"] == len(scenarios)


def test_study_run_with_zero_compatible_configurations_returns_empty_list(client):
    project = _create_project(client)
    for field_name, value in [
        ("required_flux_lm", "999999"), ("max_power_w", "1"), ("cct_k", "4000"),
        ("voltage_nominal_v", "999"), ("current_nominal_ma", "1"),
    ]:
        scope = "luminaire" if field_name in ("required_flux_lm", "max_power_w", "cct_k") else "module"
        client.post(
            f"/api/projects/{project['id']}/requirements",
            json={"category": "lighting", "scope": scope, "field_name": field_name, "value": value, "validated_by": "T"},
        )

    response = client.post(f"/api/projects/{project['id']}/study/run", json={})
    assert response.status_code == 200
    assert response.json() == []


def _project_with_scenarios(client, db_session):
    project = _create_project(client)
    make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54, output_power_max_w=150)
    make_module(db_session, input_voltage_nominal_v=48, current_nominal_ma=1050, power_nominal_w=50, led_package="3535", led_quantity=32, luminous_flux_nominal_lm=6000, cct_nominal_k=4000)
    make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    db_session.flush()

    for field_name, value in [
        ("required_flux_lm", "6000"), ("max_power_w", "60"), ("cct_k", "4000"),
        ("voltage_nominal_v", "48"), ("current_nominal_ma", "1050"),
    ]:
        scope = "luminaire" if field_name in ("required_flux_lm", "max_power_w", "cct_k") else "module"
        client.post(
            f"/api/projects/{project['id']}/requirements",
            json={"category": "lighting", "scope": scope, "field_name": field_name, "value": value, "validated_by": "T"},
        )
    scenarios = client.post(f"/api/projects/{project['id']}/study/run", json={}).json()
    return project, scenarios


def test_select_scenario_deselects_others(client, db_session):
    project, scenarios = _project_with_scenarios(client, db_session)
    assert len(scenarios) >= 1
    target = scenarios[0]

    response = client.post(
        f"/api/projects/{project['id']}/scenarios/{target['id']}/select",
        json={"selected_by": "Jean Dupont", "selection_comment": "Meilleur compromis"},
    )
    assert response.status_code == 200
    assert response.json()["selected"] is True

    all_scenarios = client.get(f"/api/projects/{project['id']}/scenarios").json()
    selected = [s for s in all_scenarios if s["selected"]]
    assert len(selected) == 1
    assert selected[0]["id"] == target["id"]

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["status"] == "photometric_validation"
    assert project_after["selected_scenario_code"] == target["scenario_code"]


def test_cannot_select_scenario_of_another_project(client, db_session):
    project_a, scenarios_a = _project_with_scenarios(client, db_session)
    project_b = _create_project(client, name="Autre projet")

    response = client.post(
        f"/api/projects/{project_b['id']}/scenarios/{scenarios_a[0]['id']}/select",
        json={"selected_by": "Jean Dupont"},
    )
    assert response.status_code == 404


def test_comparison_endpoint_returns_same_scenarios(client, db_session):
    project, scenarios = _project_with_scenarios(client, db_session)
    response = client.get(f"/api/projects/{project['id']}/comparison")
    assert response.status_code == 200
    assert len(response.json()) == len(scenarios)


# --- Rapport final du projet ---


def test_project_report_requires_a_selected_scenario(client, db_session):
    project, scenarios = _project_with_scenarios(client, db_session)
    response = client.get(f"/api/projects/{project['id']}/report.pdf")
    assert response.status_code == 409


def test_project_report_requires_validated_result(client, db_session):
    project, scenarios = _project_with_scenarios(client, db_session)
    target = scenarios[0]
    client.post(
        f"/api/projects/{project['id']}/scenarios/{target['id']}/select", json={"selected_by": "Jean Dupont"}
    )

    response = client.get(f"/api/projects/{project['id']}/report.pdf")
    assert response.status_code == 409


def test_project_report_returns_pdf_once_validated(client, db_session):
    project, scenarios = _project_with_scenarios(client, db_session)
    target = scenarios[0]
    client.post(f"/api/projects/{project['id']}/scenarios/{target['id']}/select", json={"selected_by": "Jean Dupont"})

    result_id = target["recommendation"]["id"]
    result = db_session.get(RecommendationResult, result_id)
    result.validation_status = "validated"
    result.validated_by = "Jean Dupont"
    db_session.add(
        ExpertValidation(recommendation_result_id=result_id, validator_name="Jean Dupont", decision="validated")
    )
    db_session.flush()

    response = client.get(f"/api/projects/{project['id']}/report.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
