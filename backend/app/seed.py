from .extensions import db
from .models import EmissionFactor, ImprovementMeasure, FloorUValueReferencePoint, AgeBandUValue


def seed_emission_factors():
    if EmissionFactor.query.count() > 0:
        return
    rows = [
        dict(fuel_type="Natural gas", unit_rate_per_kwh=0.068, standing_charge_per_day=1.753,
             scope_1_2_kg_per_kwh=0.1829, scope_3_kg_per_kwh=0.03021,
             source="March 2025 market averages / Greenhouse gas reporting: conversion factors 2024"),
        dict(fuel_type="Electricity", unit_rate_per_kwh=0.258, standing_charge_per_day=1.197,
             scope_1_2_kg_per_kwh=0.20705, scope_3_kg_per_kwh=0.0183,
             source="March 2025 market averages / Greenhouse gas reporting: conversion factors 2024"),
        dict(fuel_type="Gas oil", unit_rate_per_kwh=0.092, standing_charge_per_day=None,
             scope_1_2_kg_per_kwh=0.25649, scope_3_kg_per_kwh=0.05913,
             source="Quarterly Energy Prices: December 2024"),
    ]
    for r in rows:
        db.session.add(EmissionFactor(**r))
    db.session.commit()


def seed_improvement_measures():
    if ImprovementMeasure.query.count() > 0:
        return
    rows = [
        dict(name="Cavity wall insulation", applies_to="wall", lifetime_years=60, cost_per_m2=40,
             cost_guidance="£25/m2 to £55/m2. If insulation is already present in the wall it will need to be removed at cost.",
             typical_u_value=0.55,
             u_value_guidance="Typically, minimum U-value achievable on a pre-1975 wall is 0.5. To go lower you must also add internal or external wall insulation. Building regs guidance is to retrofit to U-value 0.55."),
        dict(name="Double glazing with metal or plastic frames", applies_to="window", lifetime_years=28, cost_per_m2=400,
             cost_guidance="~£400/m2 (typical supply+install rate; the source workbook priced it as ~£1000 per window instead - adjust to match your own quotes).",
             typical_u_value=1.6, u_value_guidance="Building regs guidance is to retrofit to U-value 1.6."),
        dict(name="Dry lining", applies_to="wall", lifetime_years=35, cost_per_m2=70,
             cost_guidance="£40/m2 to £100/m2, varies quite a lot.",
             typical_u_value=0.3, u_value_guidance="Building regs guidance is to retrofit to U-value 0.3."),
        dict(name="External wall insulation", applies_to="wall", lifetime_years=60, cost_per_m2=None,
             cost_guidance=None, typical_u_value=0.3,
             u_value_guidance="Building regs guidance is to retrofit to U-value 0.3."),
        dict(name="Loft insulation", applies_to="roof", lifetime_years=27, cost_per_m2=30,
             cost_guidance="~£30/m2.",
             typical_u_value=0.18,
             u_value_guidance="Pitched roof, insulation at ceiling level: retrofit to U-value 0.16. At rafter level: retrofit to U-value 0.18."),
        dict(name="Roof insulation", applies_to="roof", lifetime_years=30, cost_per_m2=30,
             cost_guidance="~£30/m2.",
             typical_u_value=0.18,
             u_value_guidance="Pitched roof (ceiling level): 0.16. Pitched roof (rafter level): 0.18. Flat roof / integral insulation: 0.18."),
        dict(name="Secondary glazing", applies_to="window", lifetime_years=7.92, cost_per_m2=None,
             cost_guidance=None, typical_u_value=None, u_value_guidance=None),
    ]
    for r in rows:
        db.session.add(ImprovementMeasure(**r))
    db.session.commit()


# Solid ground floor U-values by ground type, digitized from the standard published tables
# (U-value in W/m2K for stated perimeter/area ratio and added thermal resistance Rf).
FLOOR_GROUND_TABLES = {
    "clay_soil": {
        "resistances": [0.0, 0.5, 1.0, 1.5, 2.0],
        "rows": {
            0.05: [0.13, 0.11, 0.10, 0.09, 0.08],
            0.10: [0.22, 0.18, 0.16, 0.14, 0.13],
            0.15: [0.30, 0.24, 0.21, 0.18, 0.17],
            0.20: [0.37, 0.29, 0.25, 0.22, 0.19],
            0.25: [0.44, 0.34, 0.28, 0.24, 0.22],
            0.30: [0.49, 0.38, 0.31, 0.27, 0.23],
            0.35: [0.55, 0.41, 0.34, 0.29, 0.25],
            0.40: [0.60, 0.44, 0.36, 0.30, 0.26],
            0.45: [0.65, 0.47, 0.38, 0.32, 0.27],
            0.50: [0.70, 0.50, 0.40, 0.33, 0.28],
            0.55: [0.74, 0.52, 0.41, 0.34, 0.28],
            0.60: [0.78, 0.55, 0.43, 0.35, 0.29],
            0.65: [0.82, 0.57, 0.44, 0.35, 0.30],
            0.70: [0.86, 0.59, 0.45, 0.36, 0.30],
            0.75: [0.89, 0.61, 0.46, 0.37, 0.31],
            0.80: [0.93, 0.62, 0.47, 0.37, 0.32],
            0.85: [0.96, 0.64, 0.47, 0.38, 0.32],
            0.90: [0.99, 0.65, 0.48, 0.39, 0.32],
            0.95: [1.02, 0.66, 0.49, 0.39, 0.33],
            1.00: [1.05, 0.68, 0.50, 0.40, 0.33],
        },
    },
    "sand_or_gravel": {
        "resistances": [0.0, 0.5, 1.0, 2.0],
        "rows": {
            0.05: [0.16, 0.14, 0.12, 0.10],
            0.10: [0.28, 0.22, 0.19, 0.16],
            0.15: [0.38, 0.30, 0.25, 0.20],
            0.20: [0.47, 0.36, 0.30, 0.23],
            0.25: [0.55, 0.41, 0.33, 0.25],
            0.30: [0.63, 0.46, 0.37, 0.26],
            0.35: [0.70, 0.50, 0.39, 0.28],
            0.40: [0.76, 0.53, 0.42, 0.29],
            0.45: [0.82, 0.56, 0.43, 0.30],
            0.50: [0.88, 0.59, 0.45, 0.31],
            0.55: [0.93, 0.62, 0.47, 0.31],
            0.60: [0.98, 0.64, 0.48, 0.32],
            0.65: [1.03, 0.66, 0.49, 0.33],
            0.70: [1.07, 0.68, 0.50, 0.33],
            0.75: [1.12, 0.70, 0.51, 0.34],
            0.80: [1.16, 0.72, 0.52, 0.34],
            0.85: [1.19, 0.73, 0.53, 0.35],
            0.90: [1.23, 0.75, 0.54, 0.35],
            0.95: [1.27, 0.76, 0.54, 0.35],
            1.00: [1.30, 0.77, 0.55, 0.35],
        },
    },
    "homogeneous_rock": {
        "resistances": [0.0, 0.5, 1.0, 2.0],
        "rows": {
            0.05: [0.27, 0.21, 0.18, 0.15],
            0.10: [0.45, 0.34, 0.28, 0.22],
            0.15: [0.61, 0.43, 0.35, 0.26],
            0.20: [0.74, 0.51, 0.40, 0.28],
            0.25: [0.86, 0.58, 0.44, 0.30],
            0.30: [0.97, 0.63, 0.47, 0.32],
            0.35: [1.07, 0.66, 0.50, 0.33],
            0.40: [1.16, 0.72, 0.52, 0.34],
            0.45: [1.25, 0.75, 0.53, 0.35],
            0.50: [1.33, 0.78, 0.55, 0.35],
            0.55: [1.40, 0.80, 0.56, 0.36],
            0.60: [1.47, 0.82, 0.58, 0.37],
            0.65: [1.53, 0.84, 0.59, 0.37],
            0.70: [1.59, 0.86, 0.60, 0.37],
            0.75: [1.64, 0.87, 0.61, 0.38],
            0.80: [1.69, 0.89, 0.62, 0.38],
            0.85: [1.74, 0.91, 0.62, 0.38],
            0.90: [1.79, 0.92, 0.63, 0.39],
            0.95: [1.83, 0.93, 0.64, 0.39],
            1.00: [1.87, 0.95, 0.64, 0.39],
        },
    },
}


def seed_floor_u_value_reference_points():
    if FloorUValueReferencePoint.query.count() > 0:
        return
    for ground_type, table in FLOOR_GROUND_TABLES.items():
        for p_a_ratio, u_values in table["rows"].items():
            for resistance, u_value in zip(table["resistances"], u_values):
                db.session.add(FloorUValueReferencePoint(
                    ground_type=ground_type, p_a_ratio=p_a_ratio, resistance=resistance, u_value=u_value,
                ))
    db.session.commit()


def seed_age_band_u_values():
    if AgeBandUValue.query.count() > 0:
        return
    rows = [
        dict(period_label="Pre-1976", sort_order=1, wall_u=1.7, floor_u=None, pitched_roof_u=1.4, flat_roof_u=None,
             window_metal_u=None, window_other_u=None, window_area_pct_note=None,
             pedestrian_door_u=None, vehicle_door_u=None, entrance_door_u=None, air_permeability=None),
        dict(period_label="1976-1982", sort_order=2, wall_u=1.0, floor_u=1.0, pitched_roof_u=0.6, flat_roof_u=0.6,
             window_metal_u=None, window_other_u=None, window_area_pct_note=None,
             pedestrian_door_u=None, vehicle_door_u=None, entrance_door_u=None, air_permeability=None),
        dict(period_label="1983-1990", sort_order=3, wall_u=0.6, floor_u=0.6, pitched_roof_u=0.6, flat_roof_u=0.6,
             window_metal_u=5.7, window_other_u=5.7, window_area_pct_note="35/15%",
             pedestrian_door_u=None, vehicle_door_u=None, entrance_door_u=None, air_permeability=None),
        dict(period_label="1991-2001", sort_order=4, wall_u=0.45, floor_u=0.45, pitched_roof_u=0.45, flat_roof_u=0.45,
             window_metal_u=None, window_other_u=None, window_area_pct_note="35/15%",
             pedestrian_door_u=None, vehicle_door_u=None, entrance_door_u=None, air_permeability=None),
        dict(period_label="2002-2005", sort_order=5, wall_u=0.45, floor_u=0.45, pitched_roof_u=0.25, flat_roof_u=0.25,
             window_metal_u=None, window_other_u=3.3, window_area_pct_note="40/15%",
             pedestrian_door_u=3.3, vehicle_door_u=0.7, entrance_door_u=None, air_permeability=None),
        dict(period_label="2006-2009", sort_order=6, wall_u=0.35, floor_u=0.25, pitched_roof_u=0.25, flat_roof_u=0.16,
             window_metal_u=2.2, window_other_u=2.0, window_area_pct_note="25%",
             pedestrian_door_u=2.2, vehicle_door_u=0.7, entrance_door_u=6.0, air_permeability=None),
        dict(period_label="2010-2012", sort_order=7, wall_u=0.35, floor_u=0.25, pitched_roof_u=0.25, flat_roof_u=0.25,
             window_metal_u=2.2, window_other_u=2.2, window_area_pct_note=None,
             pedestrian_door_u=2.2, vehicle_door_u=1.5, entrance_door_u=3.5, air_permeability=10.0),
        dict(period_label="2013 & 2016", sort_order=8, wall_u=0.35, floor_u=0.25, pitched_roof_u=0.25, flat_roof_u=0.25,
             window_metal_u=2.2, window_other_u=2.2, window_area_pct_note=None,
             pedestrian_door_u=2.2, vehicle_door_u=1.5, entrance_door_u=None, air_permeability=10.0),
    ]
    for r in rows:
        db.session.add(AgeBandUValue(**r))
    db.session.commit()


def seed_all():
    seed_emission_factors()
    seed_improvement_measures()
    seed_floor_u_value_reference_points()
    seed_age_band_u_values()
