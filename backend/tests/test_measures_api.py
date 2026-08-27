def test_list_measures_seeded(client):
    res = client.get("/api/measures")
    assert res.status_code == 200
    names = [m["name"] for m in res.get_json()]
    assert "Cavity wall insulation" in names


def test_create_measure_requires_name(client):
    res = client.post("/api/measures", json={})
    assert res.status_code == 400


def test_create_measure_success(client):
    res = client.post("/api/measures", json={"name": "Custom insulation", "applies_to": ["wall"], "cost_per_m2": 50})
    assert res.status_code == 201
    body = res.get_json()
    assert body["is_custom"] is True
    assert body["applies_to"] == ["wall"]


def test_create_measure_negative_cost_rejected(client):
    res = client.post("/api/measures", json={"name": "Bad measure", "cost_per_m2": -10})
    assert res.status_code == 400
    assert "cost_per_m2" in res.get_json()["errors"]


def test_create_measure_negative_lifetime_rejected(client):
    res = client.post("/api/measures", json={"name": "Bad measure", "lifetime_years": -5})
    assert res.status_code == 400


def test_update_measure_negative_typical_u_value_rejected(client):
    created = client.post("/api/measures", json={"name": "Editable measure"}).get_json()
    res = client.put(f"/api/measures/{created['id']}", json={"typical_u_value": -0.5})
    assert res.status_code == 400


def test_delete_measure(client):
    created = client.post("/api/measures", json={"name": "Temp measure"}).get_json()
    res = client.delete(f"/api/measures/{created['id']}")
    assert res.status_code == 204


def test_list_emission_factors_seeded(client):
    res = client.get("/api/emission-factors")
    assert res.status_code == 200
    fuels = [f["fuel_type"] for f in res.get_json()]
    assert "Natural gas" in fuels


def test_update_emission_factor_negative_rate_rejected(client):
    factor = client.get("/api/emission-factors").get_json()[0]
    res = client.put(f"/api/emission-factors/{factor['id']}", json={"unit_rate_per_kwh": -0.05})
    assert res.status_code == 400


def test_update_emission_factor_success(client):
    factor = client.get("/api/emission-factors").get_json()[0]
    res = client.put(f"/api/emission-factors/{factor['id']}", json={"unit_rate_per_kwh": 0.075})
    assert res.status_code == 200
    assert res.get_json()["unit_rate_per_kwh"] == 0.075


def test_list_age_band_u_values_seeded_and_unchanged(client):
    res = client.get("/api/age-band-u-values")
    assert res.status_code == 200
    labels = [a["period_label"] for a in res.get_json()]
    assert labels == [
        "Pre-1976", "1976-1982", "1983-1990", "1991-2001", "2002-2005",
        "2006-2009", "2010-2012", "2013 & 2016",
    ]


def test_create_age_band_requires_label(client):
    res = client.post("/api/age-band-u-values", json={})
    assert res.status_code == 400


def test_create_age_band_negative_u_value_rejected(client):
    res = client.post("/api/age-band-u-values", json={"period_label": "2020+", "wall_u": -0.1})
    assert res.status_code == 400
    assert "wall_u" in res.get_json()["errors"]


def test_create_age_band_success(client):
    res = client.post("/api/age-band-u-values", json={"period_label": "2020+", "wall_u": 0.18})
    assert res.status_code == 201


def test_delete_age_band(client):
    created = client.post("/api/age-band-u-values", json={"period_label": "Temp band"}).get_json()
    res = client.delete(f"/api/age-band-u-values/{created['id']}")
    assert res.status_code == 204
