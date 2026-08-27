from app.validation import validate


def test_strict_positive_rejects_zero():
    errors = validate({"height": 0}, strict_positive=["height"])
    assert "height" in errors


def test_strict_positive_rejects_negative():
    errors = validate({"height": -5}, strict_positive=["height"])
    assert "height" in errors


def test_strict_positive_rejects_null():
    errors = validate({"height": None}, strict_positive=["height"])
    assert "height" in errors


def test_strict_positive_accepts_positive():
    errors = validate({"height": 3.2}, strict_positive=["height"])
    assert errors == {}


def test_strict_positive_skips_missing_key():
    errors = validate({}, strict_positive=["height"])
    assert errors == {}


def test_strict_positive_rejects_non_numeric():
    errors = validate({"height": "tall"}, strict_positive=["height"])
    assert "height" in errors


def test_positive_if_set_allows_null():
    errors = validate({"proposed_u_value": None}, positive_if_set=["proposed_u_value"])
    assert errors == {}


def test_positive_if_set_rejects_zero_when_provided():
    errors = validate({"proposed_u_value": 0}, positive_if_set=["proposed_u_value"])
    assert "proposed_u_value" in errors


def test_positive_if_set_skips_missing_key():
    errors = validate({}, positive_if_set=["proposed_u_value"])
    assert errors == {}


def test_non_negative_if_set_allows_zero():
    errors = validate({"resistance": 0}, non_negative_if_set=["resistance"])
    assert errors == {}


def test_non_negative_if_set_rejects_negative():
    errors = validate({"annual_fuel_usage_kwh": -100}, non_negative_if_set=["annual_fuel_usage_kwh"])
    assert "annual_fuel_usage_kwh" in errors


def test_fraction_if_set_allows_zero_and_one():
    assert validate({"window_pct": 0}, fraction_if_set=["window_pct"]) == {}
    assert validate({"window_pct": 1}, fraction_if_set=["window_pct"]) == {}


def test_fraction_if_set_rejects_above_one():
    errors = validate({"window_pct": 1.5}, fraction_if_set=["window_pct"])
    assert "window_pct" in errors


def test_fraction_if_set_rejects_negative():
    errors = validate({"boiler_efficiency": -0.1}, fraction_if_set=["boiler_efficiency"])
    assert "boiler_efficiency" in errors


def test_range_if_set_rejects_out_of_bounds():
    errors = validate({"latitude": 95}, range_if_set=[("latitude", -90, 90)])
    assert "latitude" in errors


def test_range_if_set_accepts_in_bounds():
    errors = validate({"latitude": 50.9}, range_if_set=[("latitude", -90, 90)])
    assert errors == {}


def test_multiple_rules_combine_errors():
    errors = validate(
        {"height": -1, "window_pct": 2},
        strict_positive=["height"],
        fraction_if_set=["window_pct"],
    )
    assert set(errors.keys()) == {"height", "window_pct"}
