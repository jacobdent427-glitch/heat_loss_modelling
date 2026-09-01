def test_create_plant_room_requires_name(client, project):
    res = client.post(f"/api/projects/{project['id']}/plant-rooms", json={})
    assert res.status_code == 400


def test_create_plant_room_unknown_project_404(client):
    res = client.post("/api/projects/9999/plant-rooms", json={"name": "x"})
    assert res.status_code == 404


def test_create_plant_room_success(client, project):
    res = client.post(f"/api/projects/{project['id']}/plant-rooms", json={"name": "Cavell"})
    assert res.status_code == 201
    assert res.get_json()["fuel_type"] == "Natural gas"


def test_create_plant_room_negative_fuel_usage_rejected(client, project):
    res = client.post(
        f"/api/projects/{project['id']}/plant-rooms",
        json={"name": "Cavell", "annual_fuel_usage_kwh": -100},
    )
    assert res.status_code == 400
    assert "annual_fuel_usage_kwh" in res.get_json()["errors"]


def test_create_plant_room_boiler_efficiency_over_one_rejected(client, project):
    res = client.post(
        f"/api/projects/{project['id']}/plant-rooms",
        json={"name": "Cavell", "boiler_efficiency": 1.2},
    )
    assert res.status_code == 400
    assert "boiler_efficiency" in res.get_json()["errors"]


def test_create_plant_room_negative_ach_rejected(client, project):
    res = client.post(
        f"/api/projects/{project['id']}/plant-rooms",
        json={"name": "Cavell", "ach": -0.5},
    )
    assert res.status_code == 400


def test_external_design_temp_can_be_negative(client, project):
    res = client.post(
        f"/api/projects/{project['id']}/plant-rooms",
        json={"name": "Cavell", "external_design_temp_c": -4.0},
    )
    assert res.status_code == 201
    assert res.get_json()["external_design_temp_c"] == -4.0


def test_get_plant_room_includes_elements(client, plant_room):
    res = client.get(f"/api/plant-rooms/{plant_room['id']}")
    body = res.get_json()
    for key in ("walls", "roofs", "rooflights", "floors", "doors", "zones"):
        assert body[key] == []


def test_update_plant_room_kitchen_gas_pct_over_one_rejected(client, plant_room):
    res = client.put(f"/api/plant-rooms/{plant_room['id']}", json={"kitchen_gas_pct": 1.5})
    assert res.status_code == 400


def test_update_plant_room_valid_fraction_accepted(client, plant_room):
    res = client.put(f"/api/plant-rooms/{plant_room['id']}", json={"kitchen_gas_pct": 0.05})
    assert res.status_code == 200
    assert res.get_json()["kitchen_gas_pct"] == 0.05


def test_update_plant_room_science_lab_gas_pct_over_one_rejected(client, plant_room):
    res = client.put(f"/api/plant-rooms/{plant_room['id']}", json={"science_lab_gas_pct": 1.5})
    assert res.status_code == 400
    assert "science_lab_gas_pct" in res.get_json()["errors"]


def test_update_plant_room_science_lab_gas_settings(client, plant_room):
    res = client.put(
        f"/api/plant-rooms/{plant_room['id']}", json={"uses_gas_science_lab": True, "science_lab_gas_pct": 0.04}
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["uses_gas_science_lab"] is True
    assert body["science_lab_gas_pct"] == 0.04


def test_delete_plant_room(client, plant_room):
    res = client.delete(f"/api/plant-rooms/{plant_room['id']}")
    assert res.status_code == 204
    assert client.get(f"/api/plant-rooms/{plant_room['id']}").status_code == 404


def test_plant_room_results_empty_building(client, plant_room):
    res = client.get(f"/api/plant-rooms/{plant_room['id']}/results")
    assert res.status_code == 200
    body = res.get_json()
    assert body["volume_m3"] == 0
    assert body["peak_heat_loss_kw"]["existing"] == 0


def test_auto_propose_on_empty_room(client, plant_room):
    res = client.post(f"/api/plant-rooms/{plant_room['id']}/auto-propose")
    assert res.status_code == 200
    assert res.get_json()["updated_count"] == 0
