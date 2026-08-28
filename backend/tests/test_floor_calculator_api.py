def test_reference_points_seeded_for_all_ground_types(client):
    res = client.get("/api/floor-u-value/reference-points")
    assert res.status_code == 200
    points = res.get_json()
    ground_types = {p["ground_type"] for p in points}
    assert ground_types == {"clay_soil", "sand_or_gravel", "homogeneous_rock"}
    # clay soil is tabulated at 5 resistance columns (0, 0.5, 1.0, 1.5, 2.0) x 20 ratio rows
    assert len([p for p in points if p["ground_type"] == "clay_soil"]) == 100
    # sand/gravel and rock are tabulated at 4 resistance columns x 20 ratio rows
    assert len([p for p in points if p["ground_type"] == "sand_or_gravel"]) == 80
    assert len([p for p in points if p["ground_type"] == "homogeneous_rock"]) == 80


def test_reference_points_filtered_by_ground_type(client):
    res = client.get("/api/floor-u-value/reference-points?ground_type=homogeneous_rock")
    points = res.get_json()
    assert len(points) == 80
    assert all(p["ground_type"] == "homogeneous_rock" for p in points)


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
    assert body["ground_type"] == "sand_or_gravel"  # default when not specified


def test_calculate_different_ratios_give_different_u_values(client):
    # regression: with only 2 sparse reference rows, any ratio above 0.10 used to clamp
    # to the same value regardless of the true perimeter/area ratio
    compact = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 42.9, "area_m2": 109.05, "k_value": 1.63, "thickness_m": 0.1},
    ).get_json()
    sprawling = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 103.28, "area_m2": 493.61, "k_value": 1.63, "thickness_m": 0.1},
    ).get_json()
    assert compact["u_value"] != sprawling["u_value"]
    assert compact["u_value"] > sprawling["u_value"]  # higher perimeter/area ratio loses more heat


def test_calculate_ground_type_changes_result(client):
    payload = {"perimeter_m": 40, "area_m2": 100, "k_value": 1.63, "thickness_m": 0.1}
    clay = client.post("/api/floor-u-value/calculate", json={**payload, "ground_type": "clay_soil"}).get_json()
    rock = client.post("/api/floor-u-value/calculate", json={**payload, "ground_type": "homogeneous_rock"}).get_json()
    assert clay["u_value"] != rock["u_value"]


def test_calculate_extrapolates_beyond_ratio_1_without_crashing(client):
    res = client.post(
        "/api/floor-u-value/calculate",
        json={"perimeter_m": 500, "area_m2": 100, "k_value": 1.63, "thickness_m": 0.1},
    )
    assert res.status_code == 200
    assert res.get_json()["u_value"] is not None
