import pytest

from app import calculations as calc


def test_wall_area_subtracts_windows():
    assert calc.wall_area(3, 10, 0.2) == pytest.approx(24.0)


def test_wall_area_no_windows():
    assert calc.wall_area(2, 5, 0) == 10.0


def test_window_area():
    assert calc.window_area(3, 10, 0.2) == pytest.approx(6.0)


def test_hwq_area():
    assert calc.hwq_area(2, 1.5, 3) == pytest.approx(9.0)


def test_category_summary_empty():
    summary = calc.category_summary([])
    assert summary == {"area": 0, "ua": 0, "avg_u": 0.0}


def test_category_summary_weighted_average():
    results = [calc.ElementResult(10, 1.0), calc.ElementResult(10, 2.0)]
    summary = calc.category_summary(results)
    assert summary["area"] == 20
    assert summary["ua"] == pytest.approx(30.0)
    assert summary["avg_u"] == pytest.approx(1.5)


def test_category_ua_for_heat_loss_never_negative():
    assert calc.category_ua_for_heat_loss(-1, 10) == 0.0
    assert calc.category_ua_for_heat_loss(2, 10) == 20.0


def test_building_thermal_capacity():
    assert calc.building_thermal_capacity({"wall": 10, "roof": 5}) == 15


def test_ventilation_loss():
    expected = 100 * 0.5 * calc.VENTILATION_CONSTANT
    assert calc.ventilation_loss(100, 0.5) == pytest.approx(expected)


def test_heat_loss_coefficient():
    assert calc.heat_loss_coefficient(100, 20) == 120


def test_peak_heat_loss_kw():
    result = calc.peak_heat_loss_kw(1000, 20, -4)
    assert result == pytest.approx(24.0)


def test_floor_thermal_resistance():
    assert calc.floor_thermal_resistance(0.2, 0.4) == pytest.approx(0.5)


def test_floor_thermal_resistance_zero_k_value_guarded():
    assert calc.floor_thermal_resistance(0.2, 0) == 0.0


def test_floor_perimeter_area_ratio():
    assert calc.floor_perimeter_area_ratio(40, 100) == pytest.approx(0.4)


def test_floor_perimeter_area_ratio_zero_area_guarded():
    assert calc.floor_perimeter_area_ratio(40, 0) == 0.0


def test_interpolate_floor_u_value_needs_two_points():
    result = calc.interpolate_floor_u_value(0.05, 0.0, [{"p_a_ratio": 0.05, "resistance": 0.0, "u_value": 0.16}])
    assert result["u_value"] is None
    assert "error" in result


def test_interpolate_floor_u_value_extrapolates_beyond_reference_range():
    # regression: p_a_ratio outside the stored points used to crash comparing dicts with max()/min()
    points = [
        {"p_a_ratio": 0.05, "resistance": 0.0, "u_value": 0.16},
        {"p_a_ratio": 0.05, "resistance": 0.5, "u_value": 0.14},
        {"p_a_ratio": 0.10, "resistance": 0.0, "u_value": 0.28},
        {"p_a_ratio": 0.10, "resistance": 0.5, "u_value": 0.22},
    ]
    result = calc.interpolate_floor_u_value(0.4, 0.1333, points)
    assert result["u_value"] is not None


def test_interpolate_floor_u_value_interpolates():
    points = [
        {"p_a_ratio": 0.05, "resistance": 0.0, "u_value": 0.16},
        {"p_a_ratio": 0.05, "resistance": 0.5, "u_value": 0.14},
        {"p_a_ratio": 0.10, "resistance": 0.0, "u_value": 0.28},
        {"p_a_ratio": 0.10, "resistance": 0.5, "u_value": 0.22},
    ]
    result = calc.interpolate_floor_u_value(0.075, 0.25, points)
    assert result["u_value"] is not None
    assert 0.14 < result["u_value"] < 0.28


def test_dhw_summer_baseload_kwh():
    assert calc.dhw_summer_baseload_kwh(100, 50) == pytest.approx(1150.0)


def test_dhw_tank_size_kwh():
    result = calc.dhw_tank_size_kwh(200, 45, 1, 0.85)
    assert result > 0


def test_dhw_tank_size_kwh_zero_efficiency_guarded():
    result = calc.dhw_tank_size_kwh(200, 45, 1, 0)
    assert result > 0


def test_kitchen_gas_usage_kwh():
    assert calc.kitchen_gas_usage_kwh(1000, 0.02) == pytest.approx(20.0)


def test_space_heating_gas_usage_kwh_never_negative():
    assert calc.space_heating_gas_usage_kwh(100, 80, 50) == 0.0
    assert calc.space_heating_gas_usage_kwh(1000, 100, 20) == pytest.approx(880.0)


def test_pct_heat_loss_reduction():
    assert calc.pct_heat_loss_reduction(50, 0, 100) == pytest.approx(0.5)


def test_pct_heat_loss_reduction_zero_hlc_guarded():
    assert calc.pct_heat_loss_reduction(50, 0, 0) == 0.0


def test_thermal_energy_saving_kwh():
    assert calc.thermal_energy_saving_kwh(0.5, 1000) == 500


def test_co2_saving_tonnes():
    assert calc.co2_saving_tonnes(1000, 0.1829) == pytest.approx(0.1829)


def test_cost_saving_gbp():
    assert calc.cost_saving_gbp(1000, 0.068) == pytest.approx(68.0)


def test_cost_of_improvement_gbp():
    assert calc.cost_of_improvement_gbp(50, 40) == 2000


def test_lifetime_carbon_saving_tonnes():
    assert calc.lifetime_carbon_saving_tonnes(2, 30) == 60


def test_payback_period_years():
    assert calc.payback_period_years(1000, 200) == pytest.approx(5.0)


def test_payback_period_years_zero_saving_guarded():
    assert calc.payback_period_years(1000, 0) is None


def test_cost_per_tonne_co2e():
    assert calc.cost_per_tonne_co2e(1000, 10) == pytest.approx(100.0)


def test_cost_per_tonne_co2e_zero_saving_guarded():
    assert calc.cost_per_tonne_co2e(1000, 0) is None
