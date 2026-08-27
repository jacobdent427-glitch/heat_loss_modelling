import pytest


@pytest.fixture
def furnished_room(client, plant_room):
    client.post(
        f"/api/plant-rooms/{plant_room['id']}/walls",
        json={"location": "North", "height": 3, "width": 10, "window_pct": 0.2, "wall_u_value": 1.7, "window_u_value": 5.7},
    )
    client.post(
        f"/api/plant-rooms/{plant_room['id']}/roofs",
        json={"location": "Main", "area": 30, "u_value": 1.4},
    )
    client.post(
        f"/api/plant-rooms/{plant_room['id']}/zones",
        json={"name": "Main", "area_m2": 30, "height_m": 3},
    )
    return plant_room


def test_peak_heat_loss_acceptance(client, furnished_room):
    res = client.get(f"/api/plant-rooms/{furnished_room['id']}/results")
    assert res.status_code == 200
    body = res.get_json()

    # wall 24 m2 @ 1.7 + window 6 m2 @ 5.7 + roof 30 m2 @ 1.4 = 40.8 + 34.2 + 42.0
    assert body["thermal_capacity_ua_w_per_k"]["existing"] == pytest.approx(117.0)
    assert body["volume_m3"] == pytest.approx(90.0)

    vent_loss = body["ventilation_loss_w_per_k"]
    assert vent_loss == pytest.approx(90 * 0.5 * (1.2 * 1.005 / 3.6))

    hlc = body["heat_loss_coefficient_w_per_k"]["existing"]
    assert hlc == pytest.approx(117.0 + vent_loss)

    peak_kw = body["peak_heat_loss_kw"]["existing"]
    assert peak_kw == pytest.approx((hlc / 1000.0) * (20.0 - (-4.0)))


def test_improved_u_values_reduce_peak_heat_loss(client, furnished_room):
    wall = client.get(f"/api/plant-rooms/{furnished_room['id']}").get_json()["walls"][0]
    client.put(f"/api/walls/{wall['id']}", json={"proposed_wall_u_value": 0.3})

    res = client.get(f"/api/plant-rooms/{furnished_room['id']}/results").get_json()
    assert res["peak_heat_loss_kw"]["improved"] < res["peak_heat_loss_kw"]["existing"]


def test_measure_results_populated_when_measure_assigned(client, furnished_room, plant_room):
    wall = client.get(f"/api/plant-rooms/{plant_room['id']}").get_json()["walls"][0]
    measures = {m["name"]: m for m in client.get("/api/measures").get_json()}
    cavity = measures["Cavity wall insulation"]

    client.put(f"/api/walls/{wall['id']}", json={"proposed_wall_u_value": 0.55, "wall_measure_id": cavity["id"]})

    res = client.get(f"/api/plant-rooms/{furnished_room['id']}/results").get_json()
    assert len(res["measure_results"]) == 1
    assert res["measure_results"][0]["measure_id"] == cavity["id"]
    assert res["measure_results"][0]["heat_loss_reduction_w_per_k"] > 0


def test_auto_propose_fills_in_standard_measures(client, furnished_room):
    res = client.post(f"/api/plant-rooms/{furnished_room['id']}/auto-propose")
    body = res.get_json()
    assert body["updated_count"] > 0

    room = client.get(f"/api/plant-rooms/{furnished_room['id']}").get_json()
    wall = room["walls"][0]
    assert wall["proposed_wall_u_value"] is not None
    assert wall["wall_measure_id"] is not None


def test_auto_propose_never_overwrites_existing_proposal(client, furnished_room):
    wall = client.get(f"/api/plant-rooms/{furnished_room['id']}").get_json()["walls"][0]
    client.put(f"/api/walls/{wall['id']}", json={"proposed_wall_u_value": 0.99})

    client.post(f"/api/plant-rooms/{furnished_room['id']}/auto-propose")

    updated = client.get(f"/api/plant-rooms/{furnished_room['id']}").get_json()["walls"][0]
    assert updated["proposed_wall_u_value"] == 0.99


def test_rooflight_area_subtracted_from_roof(client, plant_room):
    roof = client.post(
        f"/api/plant-rooms/{plant_room['id']}/roofs", json={"location": "Main", "area": 50, "u_value": 1.0}
    ).get_json()
    client.post(
        f"/api/plant-rooms/{plant_room['id']}/rooflights",
        json={"roof_id": roof["id"], "location": "Main", "height": 2, "width": 2, "qty": 1, "u_value": 2.0},
    )

    res = client.get(f"/api/plant-rooms/{plant_room['id']}/results").get_json()
    assert res["categories"]["roof"]["existing"]["area"] == pytest.approx(46.0)
    assert res["categories"]["rooflight"]["existing"]["area"] == pytest.approx(4.0)


def test_dhw_manual_method_included_in_space_heating(client, plant_room):
    client.put(f"/api/plant-rooms/{plant_room['id']}", json={"annual_fuel_usage_kwh": 10000, "dhw_manual_kwh": 2000})
    res = client.get(f"/api/plant-rooms/{plant_room['id']}/results").get_json()
    assert res["energy_usage"]["dhw_kwh"] == 2000
    assert res["energy_usage"]["space_heating_kwh"] == 8000
