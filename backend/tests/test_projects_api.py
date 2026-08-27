def test_create_project_requires_name(client):
    res = client.post("/api/projects", json={"address": "no name here"})
    assert res.status_code == 400


def test_create_project_success(client):
    res = client.post("/api/projects", json={"name": "Oaklands", "address": "1 Main St"})
    assert res.status_code == 201
    body = res.get_json()
    assert body["name"] == "Oaklands"
    assert body["plant_room_count"] == 0


def test_list_projects(client, project):
    res = client.get("/api/projects")
    assert res.status_code == 200
    assert any(p["id"] == project["id"] for p in res.get_json())


def test_get_project_not_found(client):
    res = client.get("/api/projects/9999")
    assert res.status_code == 404


def test_get_project_includes_plant_rooms(client, project, plant_room):
    res = client.get(f"/api/projects/{project['id']}")
    body = res.get_json()
    assert len(body["plant_rooms"]) == 1
    assert body["plant_rooms"][0]["id"] == plant_room["id"]


def test_update_project(client, project):
    res = client.put(f"/api/projects/{project['id']}", json={"name": "Renamed"})
    assert res.status_code == 200
    assert res.get_json()["name"] == "Renamed"


def test_update_project_latitude_out_of_range_rejected(client, project):
    res = client.put(f"/api/projects/{project['id']}", json={"latitude": 200})
    assert res.status_code == 400
    assert "latitude" in res.get_json()["errors"]


def test_update_project_longitude_out_of_range_rejected(client, project):
    res = client.put(f"/api/projects/{project['id']}", json={"longitude": -400})
    assert res.status_code == 400
    assert "longitude" in res.get_json()["errors"]


def test_update_project_valid_uk_coordinates_accepted(client, project):
    res = client.put(f"/api/projects/{project['id']}", json={"latitude": 50.9, "longitude": -1.35})
    assert res.status_code == 200


def test_delete_project_cascades_plant_rooms(client, project, plant_room):
    res = client.delete(f"/api/projects/{project['id']}")
    assert res.status_code == 204
    assert client.get(f"/api/plant-rooms/{plant_room['id']}").status_code == 404
