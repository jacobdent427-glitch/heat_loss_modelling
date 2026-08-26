"""Seed reference data: fuel emission factors, fabric improvement measures,
floor U-value interpolation points, and default age-band U-values.

All of this is editable later through the /api/reference-data endpoints -
these are starting defaults, not fixed truths, and should be checked against
your current CIBSE/BEIS/Building Regs source documents before relying on
them for a real HDP.
"""
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
        # Floor insulation intentionally omitted - "never recommended" per
        # project brief (expensive, disruptive, poor cost-effectiveness).
    ]
    for r in rows:
        db.session.add(ImprovementMeasure(**r))
    db.session.commit()


def seed_floor_u_value_reference_points():
    if FloorUValueReferencePoint.query.count() > 0:
        return
    # Exactly the grid points present in the source workbook's "U Value
    # Floor Calculator" tab (Table C1 extract). Add more p/a-ratio rows and
    # resistance columns from your BRE/ISO 13370 source as needed - the
    # interpolation endpoint works with however many points exist.
    rows = [
        dict(p_a_ratio=0.05, resistance=0.0, u_value=0.16),
        dict(p_a_ratio=0.05, resistance=0.5, u_value=0.14),
        dict(p_a_ratio=0.10, resistance=0.0, u_value=0.28),
        dict(p_a_ratio=0.10, resistance=0.5, u_value=0.22),
    ]
    for r in rows:
        db.session.add(FloorUValueReferencePoint(**r))
    db.session.commit()


def seed_age_band_u_values():
    if AgeBandUValue.query.count() > 0:
        return
    # Extracted from the project brief's historic fabric U-value table. The
    # header row above these columns was cropped in the source image, so
    # only the final column's label ("2013 & 2016") was legible; the other
    # period labels below are our best reconstruction of the standard UK
    # non-domestic Building Regulations Part L compliance periods and
    # SHOULD BE VERIFIED against your CIBSE/Approved Document L source
    # before relying on them for a real HDP.
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
