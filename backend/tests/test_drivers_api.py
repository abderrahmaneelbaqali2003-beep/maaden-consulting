"""Tests des endpoints CRUD /api/drivers (section 10 du cahier des charges)."""

DRIVER_PAYLOAD = {
    "external_ref": "DRV-API-TEST-001",
    "manufacturer": "ApiTestManufacturer",
    "reference": "API-TEST-REF-1",
    "output_voltage_min_v": 30,
    "output_voltage_max_v": 54,
    "output_power_max_w": 150,
    "dali_2": True,
}


def test_create_and_get_driver(client):
    response = client.post("/api/drivers", json=DRIVER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["external_ref"] == "DRV-API-TEST-001"
    assert body["manufacturer"]["name"] == "ApiTestManufacturer"
    assert body["is_active"] is True

    driver_id = body["id"]
    get_response = client.get(f"/api/drivers/{driver_id}")
    assert get_response.status_code == 200
    assert get_response.json()["reference"] == "API-TEST-REF-1"


def test_create_duplicate_external_ref_returns_409(client):
    client.post("/api/drivers", json=DRIVER_PAYLOAD)
    response = client.post("/api/drivers", json=DRIVER_PAYLOAD)
    assert response.status_code == 409


def test_get_missing_driver_returns_404(client):
    response = client.get("/api/drivers/999999")
    assert response.status_code == 404


def test_list_drivers_pagination_structure(client):
    client.post("/api/drivers", json=DRIVER_PAYLOAD)
    response = client.get("/api/drivers", params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size", "total_pages"}
    assert body["page"] == 1
    assert body["page_size"] == 5


def test_list_drivers_filter_by_power(client):
    client.post("/api/drivers", json=DRIVER_PAYLOAD)
    response = client.get("/api/drivers", params={"power_max_w": 100})
    assert response.status_code == 200
    refs = [item["external_ref"] for item in response.json()["items"]]
    assert "DRV-API-TEST-001" not in refs


def test_update_driver(client):
    created = client.post("/api/drivers", json=DRIVER_PAYLOAD).json()
    response = client.put(f"/api/drivers/{created['id']}", json={"output_power_max_w": 200})
    assert response.status_code == 200
    assert response.json()["output_power_max_w"] == 200
    assert response.json()["reference"] == "API-TEST-REF-1"  # champs non fournis inchanges


def test_soft_delete_driver_hidden_from_default_list(client):
    created = client.post("/api/drivers", json=DRIVER_PAYLOAD).json()
    delete_response = client.delete(f"/api/drivers/{created['id']}")
    assert delete_response.status_code == 204

    list_response = client.get("/api/drivers", params={"search": "API-TEST-REF-1"})
    refs = [item["external_ref"] for item in list_response.json()["items"]]
    assert "DRV-API-TEST-001" not in refs

    still_exists = client.get(f"/api/drivers/{created['id']}")
    assert still_exists.status_code == 200
    assert still_exists.json()["is_active"] is False


def test_create_driver_missing_required_field_returns_422(client):
    invalid_payload = {**DRIVER_PAYLOAD, "output_voltage_min_v": None}
    response = client.post("/api/drivers", json=invalid_payload)
    assert response.status_code == 422
