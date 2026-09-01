from . import calculations as calc
from .models import EmissionFactor


def _prop(proposed, existing):
    return proposed if proposed is not None else existing


def _kitchen_kwh(plant_room):
    if not plant_room.uses_gas_kitchen:
        return 0.0
    if plant_room.kitchen_gas_method == "calculated":
        return calc.kitchen_gas_usage_calc_kwh(plant_room.kitchen_hobs or 0.0, plant_room.kitchen_hours_per_day or 0.0)
    return calc.kitchen_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, plant_room.kitchen_gas_pct)


def _lab_kwh(plant_room):
    if not plant_room.uses_gas_science_lab:
        return 0.0
    if plant_room.lab_gas_method == "calculated":
        return calc.science_lab_gas_usage_calc_kwh(
            plant_room.lab_bunsen_kwh or 0.0, plant_room.lab_count or 0.0,
            plant_room.lab_burners_per_lab or 0.0, plant_room.lab_uses_per_day or 0.0,
        )
    return calc.science_lab_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, plant_room.science_lab_gas_pct)


def _dhw_kwh(plant_room):
    if plant_room.dhw_method == "summer_baseload" and plant_room.dhw_summer_baseload_kwh_month is not None:
        return calc.dhw_summer_baseload_kwh(
            plant_room.dhw_summer_baseload_kwh_month, _kitchen_kwh(plant_room), _lab_kwh(plant_room)
        )
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

    rooflight_area_by_roof = {}
    for rl in plant_room.rooflights:
        if rl.roof_id:
            rooflight_area_by_roof[rl.roof_id] = rooflight_area_by_roof.get(rl.roof_id, 0.0) + calc.hwq_area(
                rl.height or 0, rl.width or 0, rl.qty or 0
            )

    for r in plant_room.roofs:
        net_area = max((r.area or 0.0) - rooflight_area_by_roof.get(r.id, 0.0), 0.0)
        entries.append({
            "category": "roof",
            "element_id": r.id,
            "location": r.location,
            "area": net_area,
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
    kitchen_kwh = _kitchen_kwh(plant_room)
    lab_kwh = _lab_kwh(plant_room)
    space_heating_kwh = calc.space_heating_gas_usage_kwh(plant_room.annual_fuel_usage_kwh, dhw_kwh, kitchen_kwh, lab_kwh)
    unit_rate, emission_factor = _resolve_rates(plant_room)

    measure_groups = {}
    for e in entries:
        if not e["measure_id"]:
            continue
        existing_ua = e["existing_u"] * e["area"]
        improved_ua = e["improved_u"] * e["area"]
        delta_ua = existing_ua - improved_ua
        if abs(delta_ua) < 1e-9:
            continue
        g = measure_groups.setdefault(
            e["measure_id"], {"area": 0.0, "delta_ua": 0.0, "existing_ua": 0.0, "improved_ua": 0.0, "categories": set(), "elements": []}
        )
        g["area"] += e["area"]
        g["delta_ua"] += delta_ua
        g["existing_ua"] += existing_ua
        g["improved_ua"] += improved_ua
        g["categories"].add(e["category"])
        g["elements"].append({"category": e["category"], "element_id": e["element_id"], "location": e["location"]})

    category_labels = {"wall": "wall", "window": "window", "roof": "roof", "rooflight": "rooflight", "floor": "floor", "door": "door"}

    measure_results = []
    for measure_id, g in measure_groups.items():
        pct_reduction = calc.pct_heat_loss_reduction(g["delta_ua"], 0.0, hlc_existing)
        thermal_saving = calc.thermal_energy_saving_kwh(pct_reduction, space_heating_kwh)
        co2_saving = calc.co2_saving_tonnes(thermal_saving, emission_factor)
        cost_saving = calc.cost_saving_gbp(thermal_saving, unit_rate)
        avg_existing_u = g["existing_ua"] / g["area"] if g["area"] else 0.0
        avg_improved_u = g["improved_ua"] / g["area"] if g["area"] else 0.0
        category_text = " & ".join(category_labels.get(c, c) for c in sorted(g["categories"]))
        assumptions = f"Changed U-value of {category_text} from {avg_existing_u:.2f} to {avg_improved_u:.2f}"
        measure_results.append({
            "measure_id": measure_id,
            "area_of_improvement_m2": g["area"],
            "heat_loss_reduction_w_per_k": g["delta_ua"],
            "pct_heat_loss_reduction": pct_reduction,
            "thermal_energy_saving_kwh": thermal_saving,
            "co2_saving_tonnes_per_yr": co2_saving,
            "cost_saving_gbp_per_yr": cost_saving,
            "avg_existing_u_value": avg_existing_u,
            "avg_improved_u_value": avg_improved_u,
            "assumptions": assumptions,
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
            "lab_kwh": lab_kwh,
            "space_heating_kwh": space_heating_kwh,
            "unit_rate_per_kwh": unit_rate,
            "emission_factor_kg_per_kwh": emission_factor,
        },
        "measure_results": measure_results,
    }


def apply_measure_cost_analysis(measure_results, measures_by_id):
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


WALL_MEASURE_NAME = "Cavity wall insulation"
WINDOW_MEASURE_NAME = "Double glazing with metal or plastic frames"
ROOF_MEASURE_NAME = "Roof insulation"
LOFT_MEASURE_NAME = "Loft insulation"


def auto_propose_plant_room(plant_room, measures_by_name):
    changes = []

    def maybe_apply(element, existing_u, proposed_attr, measure_attr, measure_name, category, label):
        if getattr(element, proposed_attr) is not None:
            return
        measure = measures_by_name.get(measure_name)
        if not measure or measure.typical_u_value is None:
            return
        if existing_u is None or existing_u <= measure.typical_u_value:
            return
        setattr(element, proposed_attr, measure.typical_u_value)
        setattr(element, measure_attr, measure.id)
        changes.append({
            "category": category,
            "element_id": element.id,
            "location": label,
            "measure_name": measure.name,
            "existing_u_value": existing_u,
            "proposed_u_value": measure.typical_u_value,
        })

    for w in plant_room.walls:
        maybe_apply(w, w.wall_u_value, "proposed_wall_u_value", "wall_measure_id", WALL_MEASURE_NAME, "wall", w.location)
        maybe_apply(w, w.window_u_value, "proposed_window_u_value", "window_measure_id", WINDOW_MEASURE_NAME, "window", w.location)

    for r in plant_room.roofs:
        measure_name = LOFT_MEASURE_NAME if r.has_loft else ROOF_MEASURE_NAME
        maybe_apply(r, r.u_value, "proposed_u_value", "measure_id", measure_name, "roof", r.location)

    return changes
