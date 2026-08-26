"""
Pure calculation functions replicating the logic of the Eastleigh College
heat-loss modelling workbook ("D Block" / "D Block Improved" / "Overview of
Heat Loss" / "U Value Floor Calculator" sheets).

No Flask/SQLAlchemy imports here on purpose - these are plain functions over
plain data so they can be unit tested in isolation and reused by any route.
"""
from dataclasses import dataclass

# Ventilation heat loss constant (W per m3 per ACH). The source workbook uses
# Volume * ACH / 3 for the per-plant-room calculator (~0.333) and the more
# precise air density/specific-heat constant 1.2 * 1.005 / 3.6 = 0.335 on the
# "Overview of Heat Loss" sheet. We use the precise constant throughout.
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
    """Matches the workbook's ΣUA / Area / Average-U-value summary rows
    (e.g. N21/O21/Q21 for walls, AO21/AP21/AQ21 for roofs)."""
    total_area = sum(r.area for r in results)
    total_ua = sum(r.ua for r in results)
    avg_u = (total_ua / total_area) if total_area else 0.0
    return {"area": total_area, "ua": total_ua, "avg_u": avg_u}


def category_ua_for_heat_loss(avg_u: float, area: float) -> float:
    """Matches BM5 = IF((BK5*BL5)>0, BK5*BL5, 0)."""
    ua = avg_u * area
    return ua if ua > 0 else 0.0


def building_thermal_capacity(category_uas: dict) -> float:
    """Sum of UA across categories (Roof, Roof lights, Wall, Windows, Floor,
    Doors) - matches BK11 / BK28."""
    return sum(category_uas.values())


def ventilation_loss(volume_m3: float, ach: float) -> float:
    """W/K. Matches the 'Ventilation Loss' row (BK33) generalised with the
    precise air constant instead of the /3 shorthand."""
    return volume_m3 * ach * VENTILATION_CONSTANT


def heat_loss_coefficient(thermal_capacity_ua: float, vent_loss: float) -> float:
    """W/K. Matches BK34 = BK28 + BK33."""
    return thermal_capacity_ua + vent_loss


def peak_heat_loss_kw(hlc_w_per_k: float, internal_temp_c: float, external_temp_c: float) -> float:
    """kW. Matches BK39 = (BK34/1000) * (BK37-BK38)."""
    return (hlc_w_per_k / 1000.0) * (internal_temp_c - external_temp_c)


# ---------------------------------------------------------------------------
# Floor U-value calculator (BS EN ISO 13370 / BRE "Table C1" method used on
# the "U Value Floor Calculator" sheet). The workbook only ever populated the
# two reference rows/columns needed for its own building, sourced by the
# surveyor from a published table. We keep the same bilinear-interpolation
# approach but the grid points themselves are stored data
# (FloorUValueReferencePoint) that the user maintains/extends, rather than a
# hard-coded full table, since we cannot verify a complete table's numbers to
# engineering precision without the source document.
# ---------------------------------------------------------------------------

def floor_thermal_resistance(thickness_m: float, k_value: float) -> float:
    return thickness_m / k_value if k_value else 0.0


def floor_perimeter_area_ratio(perimeter_m: float, area_m2: float) -> float:
    return perimeter_m / area_m2 if area_m2 else 0.0


def _linear_interp(x, x0, x1, y0, y1):
    if x1 == x0:
        return y0
    return y0 + ((x - x0) / (x1 - x0)) * (y1 - y0)


def interpolate_floor_u_value(p_a_ratio: float, resistance: float, reference_points: list[dict]) -> dict:
    """reference_points: list of {"p_a_ratio": float, "resistance": float, "u_value": float}

    Performs the same two-step interpolation as the workbook:
      1. For each of the two resistance columns bracketing `resistance`,
         interpolate along p/a ratio between the two bracketing rows.
      2. Interpolate the two column results across resistance.

    Returns a dict with the bracketing points used and the interpolated
    u_value, or an error message if there isn't enough reference data.
    """
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
        p_lo = max([p for p in pts if p["p_a_ratio"] <= p_a_ratio], default=pts[0])
        p_hi = min([p for p in pts if p["p_a_ratio"] >= p_a_ratio], default=pts[-1])
        return _linear_interp(p_a_ratio, p_lo["p_a_ratio"], p_hi["p_a_ratio"], p_lo["u_value"], p_hi["u_value"])

    val_lo = col_value(r_lo)
    val_hi = col_value(r_hi)
    if val_lo is None or val_hi is None:
        return {"u_value": None, "error": "Reference data does not cover this resistance value."}

    u_value = _linear_interp(resistance, r_lo, r_hi, val_lo, val_hi)
    return {"u_value": round(u_value, 4), "r_lo": r_lo, "r_hi": r_hi, "p_a_ratio": p_a_ratio, "resistance": resistance}


# ---------------------------------------------------------------------------
# DHW (domestic hot water) estimation methods
# ---------------------------------------------------------------------------

def dhw_summer_baseload_kwh(monthly_baseload_kwh: float, kitchen_kwh: float = 0.0) -> float:
    """Matches R18 = R10*12 - R15 (summer baseload extrapolated to a year,
    minus kitchen gas usage which is also drawn from the summer baseload)."""
    return monthly_baseload_kwh * 12 - kitchen_kwh


def dhw_tank_size_kwh(tank_volume_litres: float, temp_rise_c: float, cycles_per_day: float, efficiency: float) -> float:
    """Standard tank reheat energy: Q = m * c * dT, c = 4.186 kJ/(kg.K),
    1 litre of water ~= 1 kg. Converts kJ -> kWh (/3600), extrapolates to a
    year, then divides by boiler/immersion efficiency."""
    daily_kwh = (tank_volume_litres * 4.186 * temp_rise_c * cycles_per_day) / 3600
    annual_kwh = daily_kwh * 365
    return annual_kwh / efficiency if efficiency else annual_kwh


def kitchen_gas_usage_kwh(total_annual_kwh: float, kitchen_pct: float) -> float:
    """Matches R15 = R14 * R29."""
    return total_annual_kwh * kitchen_pct


def space_heating_gas_usage_kwh(total_annual_kwh: float, dhw_kwh: float, kitchen_kwh: float = 0.0) -> float:
    """Matches the 'remaining gas usage for space heating' idea (R25), but
    computed directly per plant room since each plant room's meter/usage is
    entered individually in this app rather than split proportionally across
    a shared site meter."""
    return max(total_annual_kwh - dhw_kwh - kitchen_kwh, 0.0)


# ---------------------------------------------------------------------------
# Building fabric improvement savings (Overview of Heat Loss sheet, rows
# 16-29 and 65-69)
# ---------------------------------------------------------------------------

def pct_heat_loss_reduction(existing_ua: float, improved_ua: float, total_existing_hlc: float) -> float:
    """Matches P16 = (H16-N16)/SUM(H16:H22) - the % reduction is expressed
    against the *whole plant room's* existing heat loss coefficient (fabric
    UA for every category + ventilation), not just the one category."""
    return (existing_ua - improved_ua) / total_existing_hlc if total_existing_hlc else 0.0


def thermal_energy_saving_kwh(pct_reduction: float, annual_space_heating_kwh: float) -> float:
    """Matches Q16 = P16 * 'Existing energy usage'!T41."""
    return pct_reduction * annual_space_heating_kwh


def co2_saving_tonnes(thermal_saving_kwh: float, emission_factor_kg_per_kwh: float) -> float:
    """Matches D66 = $B$34 * C66 / 1000."""
    return thermal_saving_kwh * emission_factor_kg_per_kwh / 1000.0


def cost_saving_gbp(thermal_saving_kwh: float, unit_rate_per_kwh: float) -> float:
    """Matches E66 = C66 * 'Existing energy usage'!$L$14."""
    return thermal_saving_kwh * unit_rate_per_kwh


def cost_of_improvement_gbp(area_m2: float, cost_per_m2: float) -> float:
    """Matches G50 = E50*F50."""
    return area_m2 * cost_per_m2


def lifetime_carbon_saving_tonnes(co2_saving_tonnes_per_yr: float, lifetime_years: float) -> float:
    """Matches G66 = D66*D50 (D50 = measure lifetime, used as a 'persistence
    factor' - i.e. total carbon saved over the measure's life)."""
    return co2_saving_tonnes_per_yr * lifetime_years


def payback_period_years(cost_gbp: float, annual_cost_saving_gbp: float):
    """Matches H66 = F66/E66. Returns None (workbook shows #DIV/0!) if there
    is no cost saving."""
    return (cost_gbp / annual_cost_saving_gbp) if annual_cost_saving_gbp else None


def cost_per_tonne_co2e(cost_gbp: float, lifetime_carbon_saving: float):
    """Matches I66 = F66/G66."""
    return (cost_gbp / lifetime_carbon_saving) if lifetime_carbon_saving else None
