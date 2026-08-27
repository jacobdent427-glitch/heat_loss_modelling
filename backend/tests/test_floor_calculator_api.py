def test_reference_points_seeded(client):
    res = client.get("/api/floor-u-value/reference-points")
    assert res.status_code == 200
    assert len(res.get_json()) == 4


def test_create_reference_point_missing_field(client):
    res = client.post("/api/floor-u-value/reference-points", json={"p_a_ratio": 0.1, "resistance": 0.5})
    assert res.status_code == 400


def test_create_reference_point_zero_u_value_rejected(client):
    res = client.post("/api/floor-u-value/reference-points", json={"p_a_ratio": 0.1, "resistance": 0.5, "u_value": 0})
    assert res.status_code == 400
    assert "u_value" in res.get_json()["errors"]


def test_create_reference_point_zero_resistance_allowed(client):
    # 0.0 resistance is a real reference value already present in the seed data
    res = client.post("/api/floor-u-value/reference-points", json={"p_a_ratio": 0.2, "resistance": 0.0, "u_value": 0.3})
    assert res.status_code == 201


def test_create_reference_point_negative_p_a_ratio_rejected(client):
    res = client.post("/api/floor-u-value/reference-points", json={"p_a_ratio": -0.1, "resistance": 0.5, "u_value": 0.2})
    assert res.status_code == 400


def test_delete_reference_point(client):
    created = client.post(
        "/api/floor-u-value/reference-points", json={"p_a_ratio": 0.2, "resistance": 1.0, "u_value": 0.1}
    ).get_json()
    res = client.delete(f"/api/floor-u-value/reference-points/{created['id']}")
    assert res.status_code == 204


def test_calculate_missing_fields(client):
    res = client.post("/api/floor-u-value/calculate", json={"perimeter_m": 40, "area_m2": 100})
    assert res.status_code == 400
    assert "Missing fields" in res.get_json()["error"]


def test_calculate_zero_area_rejected(client):
    res = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 40, "area_m2": 0, "k_value": 1.5, "thickness_m": 0.2},
    )
    assert res.status_code == 400
    assert "area_m2" in res.get_json()["errors"]


def test_calculate_negative_thickness_rejected(client):
    res = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 40, "area_m2": 100, "k_value": 1.5, "thickness_m": -0.2},
    )
    assert res.status_code == 400


def test_calculate_success(client):
    res = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 40, "area_m2": 100, "k_value": 1.5, "thickness_m": 0.2},
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["u_value"] is not None
    assert body["thermal_resistance"] > 0
