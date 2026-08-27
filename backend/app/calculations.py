from dataclasses import dataclass

VENTILATION_CONSTANT = 1.2 * 1.005 / 3.6


@dataclass
class ElementResult:
    area: float
    u_value: float

    @property
    def ua(self) -> float:
        return self.area * self.u_value


def wall_area(height: float, width: float, window_pct: float) -> float:
    return height * width * (1 - window_pct)


def window_area(height: float, width: float, window_pct: float) -> float:
    return height * width * window_pct


def hwq_area(height: float, width: float, qty: float) -> float:
    return height * width * qty


def category_summary(results: list[ElementResult]) -> dict:
    total_area = sum(r.area for r in results)
    total_ua = sum(r.ua for r in results)
    avg_u = (total_ua / total_area) if total_area else 0.0
    return {"area": total_area, "ua": total_ua, "avg_u": avg_u}


def category_ua_for_heat_loss(avg_u: float, area: float) -> float:
    ua = avg_u * area
    return ua if ua > 0 else 0.0


def building_thermal_capacity(category_uas: dict) -> float:
    return sum(category_uas.values())


def ventilation_loss(volume_m3: float, ach: float) -> float:
    return volume_m3 * ach * VENTILATION_CONSTANT


def heat_loss_coefficient(thermal_capacity_ua: float, vent_loss: float) -> float:
    return thermal_capacity_ua + vent_loss


def peak_heat_loss_kw(hlc_w_per_k: float, internal_temp_c: float, external_temp_c: float) -> float:
    return (hlc_w_per_k / 1000.0) * (internal_temp_c - external_temp_c)


def floor_thermal_resistance(thickness_m: float, k_value: float) -> float:
    return thickness_m / k_value if k_value else 0.0


def floor_perimeter_area_ratio(perimeter_m: float, area_m2: float) -> float:
    return perimeter_m / area_m2 if area_m2 else 0.0


def _linear_interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)


def interpolate_floor_u_value(p_a_ratio: float, resistance: float, reference_points: list[dict]) -> dict:
    if len(reference_points) < 2:
        return {"u_value": None, "error": "Need at least two reference points to interpolate."}

    resistances = sorted({p["resistance"] for p in reference_points})
    r_lo = max([r for r in resistances if r <= resistance], default=resistances[0])
    r_hi = min([r for r in resistances if r >= resistance], default=resistances[-1])

    def col_value(r_col):
        pts = sorted([p for p in reference_points if p["resistance"] == r_col], key=lambda p: p["p_a_ratio"])
        if not pts:
            return None
        if len(pts) == 1:
            return pts[0]["u_value"]
        p_lo = max([p for p in pts if p["p_a_ratio"] <= p_a_ratio], key=lambda p: p["p_a_ratio"], default=pts[0])
        p_hi = min([p for p in pts if p["p_a_ratio"] >= p_a_ratio], key=lambda p: p["p_a_ratio"], default=pts[-1])
        return _linear_interp(p_a_ratio, p_lo["p_a_ratio"], p_hi["p_a_ratio"], p_lo["u_value"], p_hi["u_value"])

    val_lo = col_value(r_lo)
    val_hi = col_value(r_hi)
    if val_lo is None or val_hi is None:
        return {"u_value": None, "error": "Reference data does not cover this resistance value."}

    u_value = _linear_interp(resistance, r_lo, r_hi, val_lo, val_hi)
    return {"u_value": round(u_value, 4), "r_lo": r_lo, "r_hi": r_hi, "p_a_ratio": p_a_ratio, "resistance": resistance}


def dhw_summer_baseload_kwh(monthly_baseload_kwh: float, kitchen_kwh: float = 0.0) -> float:
    return monthly_baseload_kwh * 12 - kitchen_kwh


def dhw_tank_size_kwh(tank_volume_litres: float, temp_rise_c: float, cycles_per_day: float, efficiency: float) -> float:
    daily_kwh = (tank_volume_litres * 4.186 * temp_rise_c * cycles_per_day) / 3600
    annual_kwh = daily_kwh * 365
    return annual_kwh / efficiency if efficiency else annual_kwh


def kitchen_gas_usage_kwh(total_annual_kwh: float, kitchen_pct: float) -> float:
    return total_annual_kwh * kitchen_pct


def space_heating_gas_usage_kwh(total_annual_kwh: float, dhw_kwh: float, kitchen_kwh: float = 0.0) -> float:
    return max(total_annual_kwh - dhw_kwh - kitchen_kwh, 0.0)


def pct_heat_loss_reduction(existing_ua: float, improved_ua: float, total_existing_hlc: float) -> float:
    return (existing_ua - improved_ua) / total_existing_hlc if total_existing_hlc else 0.0


def thermal_energy_saving_kwh(pct_reduction: float, annual_space_heating_kwh: float) -> float:
    return pct_reduction * annual_space_heating_kwh


def co2_saving_tonnes(thermal_saving_kwh: float, emission_factor_kg_per_kwh: float) -> float:
    return thermal_saving_kwh * emission_factor_kg_per_kwh / 1000.0


def cost_saving_gbp(thermal_saving_kwh: float, unit_rate_per_kwh: float) -> float:
    return thermal_saving_kwh * unit_rate_per_kwh


def cost_of_improvement_gbp(area_m2: float, cost_per_m2: float) -> float:
    return area_m2 * cost_per_m2


def lifetime_carbon_saving_tonnes(co2_saving_tonnes_per_yr: float, lifetime_years: float) -> float:
    return co2_saving_tonnes_per_yr * lifetime_years


def payback_period_years(cost_gbp: float, annual_cost_saving_gbp: float):
    return (cost_gbp / annual_cost_saving_gbp) if annual_cost_saving_gbp else None


def cost_per_tonne_co2e(cost_gbp: float, lifetime_carbon_saving: float):
    return (cost_gbp / lifetime_carbon_saving) if lifetime_carbon_saving else None
