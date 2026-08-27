import pytest


def wall_payload(**overrides):
    payload = {"location": "North", "height": 3, "width": 10, "window_pct": 0.2, "wall_u_value": 1.0, "window_u_value": 2.0}
    payload.update(overrides)
    return payload


def test_unknown_element_type_404(client, plant_room):
    assert client.get(f"/api/plant-rooms/{plant_room['id']}/chimneys").status_code == 404
    assert client.post(f"/api/plant-rooms/{plant_room['id']}/chimneys", json={}).status_code == 404


def test_create_element_unknown_plant_room_404(client):
    res = client.post("/api/plant-rooms/9999/walls", json=wall_payload())
    assert res.status_code == 404


def test_create_wall_success(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload())
    assert res.status_code == 201
    body = res.get_json()
    assert body["height"] == 3
    assert body["plant_room_id"] == plant_room["id"]


@pytest.mark.parametrize("field", ["height", "width", "wall_u_value", "window_u_value"])
def test_create_wall_zero_measurement_rejected(client, plant_room, field):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(**{field: 0}))
    assert res.status_code == 400
    assert field in res.get_json()["errors"]


@pytest.mark.parametrize("field", ["height", "width", "wall_u_value", "window_u_value"])
def test_create_wall_negative_measurement_rejected(client, plant_room, field):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(**{field: -5}))
    assert res.status_code == 400
    assert field in res.get_json()["errors"]


def test_create_wall_without_measurements_is_allowed(client, plant_room):
    # a row can be created before it's fully measured - only explicit zero/negative is rejected
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json={"location": "North"})
    assert res.status_code == 201


def test_create_wall_window_pct_zero_is_valid(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(window_pct=0))
    assert res.status_code == 201


def test_create_wall_window_pct_over_one_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(window_pct=1.5))
    assert res.status_code == 400
    assert "window_pct" in res.get_json()["errors"]


def test_create_wall_window_pct_negative_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(window_pct=-0.1))
    assert res.status_code == 400


def test_create_wall_proposed_u_value_zero_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(proposed_wall_u_value=0))
    assert res.status_code == 400
    assert "proposed_wall_u_value" in res.get_json()["errors"]


def test_create_wall_proposed_u_value_null_allowed(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/walls", json=wall_payload(proposed_wall_u_value=None))
    assert res.status_code == 201


def test_update_wall_negative_height_rejected(client, wall):
    res = client.put(f"/api/walls/{wall['id']}", json={"height": -1})
    assert res.status_code == 400


def test_update_wall_clears_height_to_null_rejected(client, wall):
    res = client.put(f"/api/walls/{wall['id']}", json={"height": None})
    assert res.status_code == 400


def test_update_wall_unrelated_field_not_validated(client, wall):
    res = client.put(f"/api/walls/{wall['id']}", json={"notes": "inspected 2026"})
    assert res.status_code == 200
    assert res.get_json()["notes"] == "inspected 2026"


def test_delete_wall(client, wall, plant_room):
    res = client.delete(f"/api/walls/{wall['id']}")
    assert res.status_code == 204
    remaining = client.get(f"/api/plant-rooms/{plant_room['id']}/walls").get_json()
    assert all(w["id"] != wall["id"] for w in remaining)


def test_delete_wall_twice_404s(client, wall):
    assert client.delete(f"/api/walls/{wall['id']}").status_code == 204
    assert client.delete(f"/api/walls/{wall['id']}").status_code == 404


def test_create_roof_zero_area_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/roofs", json={"location": "Main", "area": 0, "u_value": 0.5})
    assert res.status_code == 400
    assert "area" in res.get_json()["errors"]


def test_create_roof_success(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/roofs", json={"location": "Main", "area": 200, "u_value": 0.5})
    assert res.status_code == 201


def test_create_rooflight_zero_qty_rejected(client, plant_room):
    res = client.post(
        f"/api/plant-rooms/{plant_room['id']}/rooflights",
        json={"location": "Main", "height": 1, "width": 1, "qty": 0, "u_value": 2.0},
    )
    assert res.status_code == 400
    assert "qty" in res.get_json()["errors"]


def test_create_rooflight_linked_to_roof(client, plant_room):
    roof = client.post(f"/api/plant-rooms/{plant_room['id']}/roofs", json={"location": "Main", "area": 200, "u_value": 0.5}).get_json()
    res = client.post(
        f"/api/plant-rooms/{plant_room['id']}/rooflights",
        json={"roof_id": roof["id"], "location": "Main", "height": 1, "width": 1, "qty": 2, "u_value": 2.0},
    )
    assert res.status_code == 201
    assert res.get_json()["roof_id"] == roof["id"]


def test_create_floor_negative_u_value_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/floors", json={"location": "Ground", "area": 100, "u_value": -0.2})
    assert res.status_code == 400


def test_create_floor_without_u_value_allowed(client, plant_room):
    # matches the "copy area from roof" flow which leaves u_value for later entry
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/floors", json={"location": "Ground", "area": 100})
    assert res.status_code == 201
    assert res.get_json()["u_value"] == 0.0


def test_create_door_zero_height_rejected(client, plant_room):
    res = client.post(
        f"/api/plant-rooms/{plant_room['id']}/doors",
        json={"location": "Main", "height": 0, "width": 1, "qty": 1, "u_value": 2.0},
    )
    assert res.status_code == 400


def test_create_door_success(client, plant_room):
    res = client.post(
        f"/api/plant-rooms/{plant_room['id']}/doors",
        json={"location": "Main", "height": 2.1, "width": 1, "qty": 1, "u_value": 2.0},
    )
    assert res.status_code == 201


def test_create_zone_negative_area_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/zones", json={"name": "Office", "area_m2": -10, "height_m": 3})
    assert res.status_code == 400
    assert "area_m2" in res.get_json()["errors"]


def test_create_zone_zero_height_rejected(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/zones", json={"name": "Office", "area_m2": 50, "height_m": 0})
    assert res.status_code == 400
    assert "height_m" in res.get_json()["errors"]


def test_create_zone_without_height_allowed(client, plant_room):
    # matches the "copy area from floors" flow which leaves height for later entry
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/zones", json={"name": "Office", "area_m2": 50})
    assert res.status_code == 201


def test_create_zone_success(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/zones", json={"name": "Office", "area_m2": 50, "height_m": 3})
    assert res.status_code == 201
    assert res.get_json()["volume_m3"] == 150
