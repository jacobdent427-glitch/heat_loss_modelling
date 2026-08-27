def test_overview_unknown_project_404(client):
    res = client.get("/api/projects/9999/overview")
    assert res.status_code == 404


def test_overview_empty_project(client, project):
    res = client.get(f"/api/projects/{project['id']}/overview")
    assert res.status_code == 200
    body = res.get_json()
    assert body["plant_rooms"] == []
    assert body["totals"]["blended_payback_period_years"] is None
    assert body["peak_heat_loss_kw_total"] == {"existing": 0.0, "improved": 0.0}


def test_overview_aggregates_measure_costs_and_payback(client, project, plant_room):
    client.put(f"/api/plant-rooms/{plant_room['id']}", json={"annual_fuel_usage_kwh": 20000})
    client.post(
        f"/api/plant-rooms/{plant_room['id']}/walls",
        json={"location": "North", "height": 3, "width": 10, "window_pct": 0, "wall_u_value": 1.7, "window_u_value": 5.7},
    )
    wall = client.get(f"/api/plant-rooms/{plant_room['id']}").get_json()["walls"][0]
    cavity = next(m for m in client.get("/api/measures").get_json() if m["name"] == "Cavity wall insulation")

    client.put(f"/api/walls/{wall['id']}", json={"proposed_wall_u_value": 0.55, "wall_measure_id": cavity["id"]})

    res = client.get(f"/api/projects/{project['id']}/overview")
    assert res.status_code == 200
    body = res.get_json()

    assert len(body["plant_rooms"]) == 1
    assert len(body["measures"]) == 1
    assert body["measures"][0]["plant_room_id"] == plant_room["id"]
    assert body["totals"]["total_cost_of_improvement_gbp"] > 0
    assert body["totals"]["blended_payback_period_years"] is not None


def test_overview_sums_across_multiple_plant_rooms(client, project):
    room_a = client.post(f"/api/projects/{project['id']}/plant-rooms", json={"name": "Room A"}).get_json()
    room_b = client.post(f"/api/projects/{project['id']}/plant-rooms", json={"name": "Room B"}).get_json()
    for room in (room_a, room_b):
        client.post(
            f"/api/plant-rooms/{room['id']}/roofs",
            json={"location": "Main", "area": 20, "u_value": 1.0},
        )

    res = client.get(f"/api/projects/{project['id']}/overview").get_json()
    assert len(res["plant_rooms"]) == 2
