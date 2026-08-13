"""Tests de la pre-analyse CPS automatique (import -> extraction -> jusqu'a 3 scenarios
provisoires si les donnees le permettent). Reutilise le moteur de recommandation reel :
aucune duplication de logique de compatibilite/scoring n'est testee ici, seulement
l'orchestration (CpsAnalysisService) et le garde-fou preliminary/final."""

import io

from reportlab.pdfgen import canvas

from app.database.models import ExtractedRequirement, Project, ProjectScenario, RecommendationRun
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


COMPLETE_CCTP_LINES = [
    "Flux allant jusqu'a 6000 lumens, puissance jusqu'a 60W.",
    "Temperature de couleur : 4000K",
    "Tension nominale : 48 V.",
    "Courant nominal : 1050 mA.",
]

MISSING_CURRENT_LINES = [
    "Flux allant jusqu'a 6000 lumens, puissance jusqu'a 60W.",
    "Temperature de couleur : 4000K",
    "Tension nominale : 48 V.",
]

MISSING_VOLTAGE_LINES = [
    "Flux allant jusqu'a 6000 lumens, puissance jusqu'a 60W.",
    "Temperature de couleur : 4000K",
    "Courant nominal : 1050 mA.",
]

EXTREME_CCTP_LINES = [
    "Flux allant jusqu'a 999999 lumens, puissance jusqu'a 1W.",
    "Temperature de couleur : 4000K",
    "Tension nominale : 999 V.",
    "Courant nominal : 1 mA.",
]


def _create_project(client, **overrides):
    payload = {"name": "Projet pre-analyse", "client_name": "RRM"}
    payload.update(overrides)
    response = client.post("/api/projects", json=payload)
    assert response.status_code == 201
    return response.json()


def _analyze(client, project_id: int, lines: list[str]):
    pdf_bytes = _build_pdf_bytes(lines)
    return client.post(
        f"/api/projects/{project_id}/cps/analyze",
        files={"file": ("CCTP.pdf", pdf_bytes, "application/pdf")},
    )


def _make_compatible_catalog(db_session, flux=6000, power=60, cct=4000, voltage=48, current=1050):
    driver = make_driver(db_session, output_voltage_min_v=30, output_voltage_max_v=54, output_power_max_w=150)
    module = make_module(
        db_session, input_voltage_nominal_v=voltage, current_nominal_ma=current, power_nominal_w=power - 10,
        led_package="3535", led_quantity=32, luminous_flux_nominal_lm=flux, cct_nominal_k=cct,
    )
    lens = make_lens(db_session, compatible_led_package="3535", optical_cells_quantity=32)
    return driver, module, lens


# --- Pre-analyse reussie / donnees manquantes ---


def test_analyze_cps_with_complete_data_runs_preliminary_study_successfully(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)

    response = _analyze(client, project["id"], COMPLETE_CCTP_LINES)

    assert response.status_code == 201
    body = response.json()
    assert body["analysis"]["can_run_preliminary_study"] is True
    assert body["analysis"]["missing_fields"] == []
    assert len(body["scenarios"]) >= 1
    assert all(s["run_type"] == "preliminary" for s in body["scenarios"])
    assert all(s["scenario_code"] for s in body["scenarios"])

    project_after = client.get(f"/api/projects/{project['id']}").json()
    assert project_after["status"] == "preliminary_analysis"
    assert project_after["preliminary_scenario_count"] == len(body["scenarios"])


def test_analyze_cps_missing_current_lists_it_in_missing_fields(client, db_session):
    project = _create_project(client)

    response = _analyze(client, project["id"], MISSING_CURRENT_LINES)

    assert response.status_code == 201
    body = response.json()
    assert body["analysis"]["can_run_preliminary_study"] is False
    missing = {f["field"] for f in body["analysis"]["missing_fields"]}
    assert "current_nominal_ma" in missing
    assert body["scenarios"] == []


def test_analyze_cps_missing_voltage_prevents_preliminary_study(client, db_session):
    project = _create_project(client)

    response = _analyze(client, project["id"], MISSING_VOLTAGE_LINES)

    assert response.status_code == 201
    body = response.json()
    assert body["analysis"]["can_run_preliminary_study"] is False
    missing = {f["field"] for f in body["analysis"]["missing_fields"]}
    assert "voltage_nominal_v" in missing
    assert body["scenarios"] == []


def test_preliminary_study_with_extreme_requirements_returns_empty_list(client, db_session):
    project = _create_project(client)

    response = _analyze(client, project["id"], EXTREME_CCTP_LINES)

    assert response.status_code == 201
    body = response.json()
    assert body["analysis"]["can_run_preliminary_study"] is True
    assert body["scenarios"] == []


def test_preliminary_study_never_exceeds_max_results(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)

    response = _analyze(client, project["id"], COMPLETE_CCTP_LINES)

    assert response.status_code == 201
    assert len(response.json()["scenarios"]) <= 3


# --- Regles metier : preliminaire ne confirme jamais, etude finale ignore "detected" ---


def test_preliminary_analysis_never_confirms_requirements_automatically(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)

    _analyze(client, project["id"], COMPLETE_CCTP_LINES)

    requirements = client.get(f"/api/projects/{project['id']}/requirements").json()
    assert len(requirements) > 0
    assert all(r["validation_status"] == "detected" for r in requirements)


def test_final_study_ignores_detected_requirements_not_yet_validated(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    _analyze(client, project["id"], COMPLETE_CCTP_LINES)  # laisse toutes les exigences "detected"

    response = client.post(f"/api/projects/{project['id']}/study/run", json={})

    assert response.status_code == 409
    assert "obligatoire" in response.json()["detail"].lower()


# --- Completion manuelle -> etude relancable ---


def test_manual_completion_of_missing_field_allows_rerunning_preliminary_study(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    first = _analyze(client, project["id"], MISSING_CURRENT_LINES)
    assert first.json()["analysis"]["can_run_preliminary_study"] is False

    add_response = client.post(
        f"/api/projects/{project['id']}/requirements",
        json={
            "category": "electrical", "scope": "module", "field_name": "current_nominal_ma",
            "operator": "==", "value": "1050", "unit": "mA", "validated_by": "Jean Dupont",
        },
    )
    assert add_response.status_code == 201

    rerun = client.post(f"/api/projects/{project['id']}/cps/preliminary-study")

    assert rerun.status_code == 200
    body = rerun.json()
    assert body["analysis"]["can_run_preliminary_study"] is True
    assert len(body["scenarios"]) >= 1


# --- Distinction preliminary / final ---


def test_run_type_tagged_correctly_on_preliminary_and_final_runs(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    _analyze(client, project["id"], COMPLETE_CCTP_LINES)

    requirements = client.get(f"/api/projects/{project['id']}/requirements").json()
    for r in requirements:
        client.patch(
            f"/api/projects/{project['id']}/requirements/{r['id']}",
            json={"action": "confirm", "validated_by": "Jean Dupont"},
        )

    final_response = client.post(f"/api/projects/{project['id']}/study/run", json={})
    assert final_response.status_code == 200
    final_scenarios = final_response.json()
    assert len(final_scenarios) >= 1
    assert all(s["run_type"] == "final" for s in final_scenarios)

    all_scenarios = client.get(f"/api/projects/{project['id']}/scenarios").json()
    preliminary_ones = [s for s in all_scenarios if s["run_type"] == "preliminary"]
    final_ones = [s for s in all_scenarios if s["run_type"] == "final"]
    assert len(preliminary_ones) >= 1
    assert len(final_ones) >= 1


def test_cannot_select_a_preliminary_scenario(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    analyze_response = _analyze(client, project["id"], COMPLETE_CCTP_LINES)
    preliminary_scenario = analyze_response.json()["scenarios"][0]

    response = client.post(
        f"/api/projects/{project['id']}/scenarios/{preliminary_scenario['id']}/select",
        json={"selected_by": "Jean Dupont"},
    )

    assert response.status_code == 409
    assert "definitive" in response.json()["detail"].lower() or "preliminaire" in response.json()["detail"].lower()


def test_repeated_preliminary_analysis_does_not_accumulate_displayed_scenarios(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)

    _analyze(client, project["id"], COMPLETE_CCTP_LINES)
    second = client.post(f"/api/projects/{project['id']}/cps/preliminary-study")
    third = client.post(f"/api/projects/{project['id']}/cps/preliminary-study")

    assert third.status_code == 200
    scenarios = client.get(f"/api/projects/{project['id']}/scenarios").json()
    preliminary_ones = [s for s in scenarios if s["run_type"] == "preliminary"]
    # Un seul run "preliminary" doit rester actif malgre 3 relances successives.
    assert len({s["run_id"] for s in preliminary_ones}) == 1


# --- Non-regression : le moteur/le scoring ne sont jamais modifies par la pre-analyse ---


def test_preliminary_scenario_scores_have_the_same_structure_as_final(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    body = _analyze(client, project["id"], COMPLETE_CCTP_LINES).json()

    scenario = body["scenarios"][0]
    scores = scenario["recommendation"]["scores"]
    assert set(scores.keys()) == {"electrical", "photometric", "mechanical", "thermal", "data_quality"}
    assert 0 <= scenario["recommendation"]["overall_score"] <= 100


def test_preliminary_run_persisted_with_run_type_column(client, db_session):
    project = _create_project(client)
    _make_compatible_catalog(db_session)
    body = _analyze(client, project["id"], COMPLETE_CCTP_LINES).json()

    run_id = body["scenarios"][0]["run_id"]
    run = db_session.get(RecommendationRun, run_id)
    assert run.run_type == "preliminary"
