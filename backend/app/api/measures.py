from flask import jsonify, request

from ..extensions import db
from ..models import ImprovementMeasure, EmissionFactor, AgeBandUValue
from . import api_bp

MEASURE_FIELDS = [
    "name", "applies_to", "lifetime_years", "cost_per_m2", "cost_guidance",
    "typical_u_value", "u_value_guidance", "is_custom",
]


def _set_applies_to(row, data):
    if "applies_to" in data:
        value = data["applies_to"]
        row.applies_to = ",".join(value) if isinstance(value, list) else (value or "")


@api_bp.get("/measures")
def list_measures():
    rows = ImprovementMeasure.query.order_by(ImprovementMeasure.name).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.post("/measures")
def create_measure():
    data = request.get_json(force=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    row = ImprovementMeasure(name=data["name"], is_custom=True)
    for field in MEASURE_FIELDS:
        if field in data and field not in ("name", "applies_to"):
            setattr(row, field, data[field])
    _set_applies_to(row, data)
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api_bp.put("/measures/<int:measure_id>")
def update_measure(measure_id):
    row = db.get_or_404(ImprovementMeasure, measure_id)
    data = request.get_json(force=True) or {}
    for field in MEASURE_FIELDS:
        if field in data and field != "applies_to":
            setattr(row, field, data[field])
    _set_applies_to(row, data)
    db.session.commit()
    return jsonify(row.to_dict())


@api_bp.delete("/measures/<int:measure_id>")
def delete_measure(measure_id):
    row = db.get_or_404(ImprovementMeasure, measure_id)
    db.session.delete(row)
    db.session.commit()
    return "", 204


@api_bp.get("/emission-factors")
def list_emission_factors():
    rows = EmissionFactor.query.order_by(EmissionFactor.fuel_type).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.put("/emission-factors/<int:factor_id>")
def update_emission_factor(factor_id):
    row = db.get_or_404(EmissionFactor, factor_id)
    data = request.get_json(force=True) or {}
    for field in ("unit_rate_per_kwh", "standing_charge_per_day", "scope_1_2_kg_per_kwh", "scope_3_kg_per_kwh", "source"):
        if field in data:
            setattr(row, field, data[field])
    db.session.commit()
    return jsonify(row.to_dict())


@api_bp.get("/age-band-u-values")
def list_age_band_u_values():
    rows = AgeBandUValue.query.order_by(AgeBandUValue.sort_order).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.post("/age-band-u-values")
def create_age_band_u_value():
    data = request.get_json(force=True) or {}
    if not data.get("period_label"):
        return jsonify({"error": "period_label is required"}), 400
    row = AgeBandUValue(period_label=data["period_label"])
    for field in (
        "sort_order", "wall_u", "floor_u", "pitched_roof_u", "flat_roof_u", "window_metal_u",
        "window_other_u", "window_area_pct_note", "pedestrian_door_u", "vehicle_door_u",
        "entrance_door_u", "air_permeability",
    ):
        if field in data:
            setattr(row, field, data[field])
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api_bp.put("/age-band-u-values/<int:row_id>")
def update_age_band_u_value(row_id):
    row = db.get_or_404(AgeBandUValue, row_id)
    data = request.get_json(force=True) or {}
    for field in (
        "period_label", "sort_order", "wall_u", "floor_u", "pitched_roof_u", "flat_roof_u",
        "window_metal_u", "window_other_u", "window_area_pct_note", "pedestrian_door_u",
        "vehicle_door_u", "entrance_door_u", "air_permeability",
    ):
        if field in data:
            setattr(row, field, data[field])
    db.session.commit()
    return jsonify(row.to_dict())


@api_bp.delete("/age-band-u-values/<int:row_id>")
def delete_age_band_u_value(row_id):
    row = db.get_or_404(AgeBandUValue, row_id)
    db.session.delete(row)
    db.session.commit()
    return "", 204
