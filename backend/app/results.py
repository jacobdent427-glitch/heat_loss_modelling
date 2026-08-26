"""
Combines the ORM models with the pure calculation functions in
calculations.py to produce the "existing" vs "improved" heat-loss results for
a plant room, plus the per-measure savings/payback table (the app's version
of the "Overview of Heat Loss" sheet).
"""
from . import calculations as calc
from .models import EmissionFactor


def _prop(proposed, existing):
    return proposed if proposed is not None else existing


def _dhw_kwh(plant_room):
    if plant_room.dhw_method == "summer_baseload" and plant_room.dhw_summer_baseload_kwh_month is not None:
        kitchen_kwh = (
            calc.kitchen_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, plant_room.kitchen_gas_pct)
            if plant_room.uses_gas_kitchen
            else 0.0
        )
        return calc.dhw_summer_baseload_kwh(plant_room.dhw_summer_baseload_kwh_month, kitchen_kwh)
    if plant_room.dhw_method == "tank_size" and plant_room.dhw_tank_volume_litres:
        return calc.dhw_tank_size_kwh(
            plant_room.dhw_tank_volume_litres,
            plant_room.dhw_tank_temp_rise_c or 45.0,
            plant_room.dhw_tank_cycles_per_day or 1.0,
            plant_room.dhw_efficiency or 1.0,
        )
    return plant_room.dhw_manual_kwh or 0.0


def _resolve_rates(plant_room):
    ef = EmissionFactor.query.filter_by(fuel_type=plant_room.fuel_type).first()
    unit_rate = plant_room.unit_rate_per_kwh
    if unit_rate is None:
        unit_rate = ef.unit_rate_per_kwh if ef else 0.0
    emission_factor = ef.scope_1_2_kg_per_kwh if ef else 0.0
    return unit_rate, emission_factor


def _element_entries(plant_room):
    """Builds a flat list of per-element dicts: type, id, area, existing_u,
    improved_u, measure_id, location - one entry per fabric element,
    including the window portion of each wall as a separate 'window' entry
    (matching the workbook's independent Wall / Windows-and-doors tables)."""
    entries = []

    for w in plant_room.walls:
        entries.append({
            "category": "wall",
            "element_id": w.id,
            "location": w.location,
            "area": calc.wall_area(w.height or 0, w.width or 0, w.window_pct or 0),
            "existing_u": w.wall_u_value or 0.0,
            "improved_u": _prop(w.proposed_wall_u_value, w.wall_u_value or 0.0),
            "measure_id": w.wall_measure_id,
        })
        if (w.window_pct or 0) > 0:
            entries.append({
                "category": "window",
                "element_id": w.id,
                "location": w.location,
                "area": calc.window_area(w.height or 0, w.width or 0, w.window_pct or 0),
                "existing_u": w.window_u_value or 0.0,
                "improved_u": _prop(w.proposed_window_u_value, w.window_u_value or 0.0),
                "measure_id": w.window_measure_id,
            })

    for r in plant_room.roofs:
        entries.append({
            "category": "roof",
            "element_id": r.id,
            "location": r.location,
            "area": r.area or 0.0,
            "existing_u": r.u_value or 0.0,
            "improved_u": _prop(r.proposed_u_value, r.u_value or 0.0),
            "measure_id": r.measure_id,
        })

    for rl in plant_room.rooflights:
        entries.append({
            "category": "rooflight",
            "element_id": rl.id,
            "location": rl.location,
            "area": calc.hwq_area(rl.height or 0, rl.width or 0, rl.qty or 0),
            "existing_u": rl.u_value or 0.0,
            "improved_u": _prop(rl.proposed_u_value, rl.u_value or 0.0),
            "measure_id": rl.measure_id,
        })

    for f in plant_room.floors:
        entries.append({
            "category": "floor",
            "element_id": f.id,
            "location": f.location,
            "area": f.area or 0.0,
            "existing_u": f.u_value or 0.0,
            "improved_u": _prop(f.proposed_u_value, f.u_value or 0.0),
            "measure_id": f.measure_id,
        })

    for d in plant_room.doors:
        entries.append({
            "category": "door",
            "element_id": d.id,
            "location": d.location,
            "area": calc.hwq_area(d.height or 0, d.width or 0, d.qty or 0),
            "existing_u": d.u_value or 0.0,
            "improved_u": _prop(d.proposed_u_value, d.u_value or 0.0),
            "measure_id": d.measure_id,
        })

    return entries


def _category_summary(entries, u_field):
    results = [calc.ElementResult(e["area"], e[u_field]) for e in entries]
    return calc.category_summary(results)


def plant_room_results(plant_room):
    entries = _element_entries(plant_room)
    categories = ["wall", "window", "roof", "rooflight", "floor", "door"]

    category_existing = {}
    category_improved = {}
    for cat in categories:
        cat_entries = [e for e in entries if e["category"] == cat]
        category_existing[cat] = _category_summary(cat_entries, "existing_u")
        category_improved[cat] = _category_summary(cat_entries, "improved_u")

    category_ua_existing = {
        cat: calc.category_ua_for_heat_loss(category_existing[cat]["avg_u"], category_existing[cat]["area"])
        for cat in categories
    }
    category_ua_improved = {
        cat: calc.category_ua_for_heat_loss(category_improved[cat]["avg_u"], category_improved[cat]["area"])
        for cat in categories
    }

    thermal_capacity_existing = calc.building_thermal_capacity(category_ua_existing)
    thermal_capacity_improved = calc.building_thermal_capacity(category_ua_improved)

    volume_m3 = sum((z.area_m2 or 0) * (z.height_m or 0) for z in plant_room.zones)
    vent_loss = calc.ventilation_loss(volume_m3, plant_room.ach or 0.0)

    hlc_existing = calc.heat_loss_coefficient(thermal_capacity_existing, vent_loss)
    hlc_improved = calc.heat_loss_coefficient(thermal_capacity_improved, vent_loss)

    peak_existing_kw = calc.peak_heat_loss_kw(hlc_existing, plant_room.internal_setpoint_c, plant_room.external_design_temp_c)
    peak_improved_kw = calc.peak_heat_loss_kw(hlc_improved, plant_room.internal_setpoint_c, plant_room.external_design_temp_c)

    dhw_kwh = _dhw_kwh(plant_room)
    kitchen_kwh = (
        calc.kitchen_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, plant_room.kitchen_gas_pct)
        if plant_room.uses_gas_kitchen
        else 0.0
    )
    space_heating_kwh = calc.space_heating_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, dhw_kwh, kitchen_kwh)
    unit_rate, emission_factor = _resolve_rates(plant_room)

    # Per-measure savings: group individual elements (not whole categories)
    # by the measure applied, so mixed measures within one category (e.g.
    # two different wall upgrades) are still attributed correctly.
    measure_groups = {}
    for e in entries:
        if not e["measure_id"]:
            continue
        delta_ua = (e["existing_u"] * e["area"]) - (e["improved_u"] * e["area"])
        if abs(delta_ua) < 1e-9:
            continue
        g = measure_groups.setdefault(e["measure_id"], {"area": 0.0, "delta_ua": 0.0, "elements": []})
        g["area"] += e["area"]
        g["delta_ua"] += delta_ua
        g["elements"].append({"category": e["category"], "element_id": e["element_id"], "location": e["location"]})

    measure_results = []
    for measure_id, g in measure_groups.items():
        pct_reduction = calc.pct_heat_loss_reduction(g["delta_ua"], 0.0, hlc_existing)
        thermal_saving = calc.thermal_energy_saving_kwh(pct_reduction, space_heating_kwh)
        co2_saving = calc.co2_saving_tonnes(thermal_saving, emission_factor)
        cost_saving = calc.cost_saving_gbp(thermal_saving, unit_rate)
        measure_results.append({
            "measure_id": measure_id,
            "area_of_improvement_m2": g["area"],
            "heat_loss_reduction_w_per_k": g["delta_ua"],
            "pct_heat_loss_reduction": pct_reduction,
            "thermal_energy_saving_kwh": thermal_saving,
            "co2_saving_tonnes_per_yr": co2_saving,
            "cost_saving_gbp_per_yr": cost_saving,
            "elements": g["elements"],
        })

    return {
        "categories": {
            cat: {
                "existing": {**category_existing[cat], "ua_for_heat_loss": category_ua_existing[cat]},
                "improved": {**category_improved[cat], "ua_for_heat_loss": category_ua_improved[cat]},
            }
            for cat in categories
        },
        "thermal_capacity_ua_w_per_k": {"existing": thermal_capacity_existing, "improved": thermal_capacity_improved},
        "volume_m3": volume_m3,
        "ventilation_loss_w_per_k": vent_loss,
        "heat_loss_coefficient_w_per_k": {"existing": hlc_existing, "improved": hlc_improved},
        "peak_heat_loss_kw": {"existing": peak_existing_kw, "improved": peak_improved_kw},
        "energy_usage": {
            "annual_fuel_usage_kwh": plant_room.annual_fuel_usage_kwh,
            "dhw_kwh": dhw_kwh,
            "kitchen_kwh": kitchen_kwh,
            "space_heating_kwh": space_heating_kwh,
            "unit_rate_per_kwh": unit_rate,
            "emission_factor_kg_per_kwh": emission_factor,
        },
        "measure_results": measure_results,
    }


def apply_measure_cost_analysis(measure_results, measures_by_id):
    """Adds cost-of-improvement / payback / lifetime-carbon-saving /
    cost-per-tonne-CO2e fields, given an {id: ImprovementMeasure} lookup.
    Kept separate from plant_room_results so routes can override cost/m2 or
    lifetime per-application without re-running the heat-loss maths."""
    enriched = []
    for m in measure_results:
        measure = measures_by_id.get(m["measure_id"])
        cost_per_m2 = measure.cost_per_m2 if measure and measure.cost_per_m2 is not None else 0.0
        lifetime_years = measure.lifetime_years if measure and measure.lifetime_years is not None else 0.0

        cost = calc.cost_of_improvement_gbp(m["area_of_improvement_m2"], cost_per_m2)
        lifetime_carbon = calc.lifetime_carbon_saving_tonnes(m["co2_saving_tonnes_per_yr"], lifetime_years)
        payback = calc.payback_period_years(cost, m["cost_saving_gbp_per_yr"])
        cost_per_tonne = calc.cost_per_tonne_co2e(cost, lifetime_carbon)

        enriched.append({
            **m,
            "measure_name": measure.name if measure else "Unknown measure",
            "lifetime_years": lifetime_years,
            "cost_per_m2": cost_per_m2,
            "cost_of_improvement_gbp": cost,
            "lifetime_carbon_saving_tonnes": lifetime_carbon,
            "payback_period_years": payback,
            "cost_per_tonne_co2e": cost_per_tonne,
        })
    return enriched
