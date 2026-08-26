from flask import jsonify, request

from .. import calculations as calc
from ..extensions import db
from ..models import FloorUValueReferencePoint
from . import api_bp


@api_bp.get("/floor-u-value/reference-points")
def list_reference_points():
    rows = FloorUValueReferencePoint.query.order_by(
        FloorUValueReferencePoint.resistance, FloorUValueReferencePoint.p_a_ratio
    ).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.post("/floor-u-value/reference-points")
def create_reference_point():
    data = request.get_json(force=True) or {}
    for field in ("p_a_ratio", "resistance", "u_value"):
        if field not in data:
            return jsonify({"error": f"{field} is required"}), 400
    row = FloorUValueReferencePoint(
        p_a_ratio=data["p_a_ratio"], resistance=data["resistance"], u_value=data["u_value"]
    )
    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api_bp.delete("/floor-u-value/reference-points/<int:point_id>")
def delete_reference_point(point_id):
    row = db.get_or_404(FloorUValueReferencePoint, point_id)
    db.session.delete(row)
    db.session.commit()
    return "", 204


@api_bp.post("/floor-u-value/calculate")
def calculate_floor_u_value():
    data = request.get_json(force=True) or {}
    required = ["perimeter_m", "area_m2", "k_value", "thickness_m"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    resistance = calc.floor_thermal_resistance(data["thickness_m"], data["k_value"])
    p_a_ratio = calc.floor_perimeter_area_ratio(data["perimeter_m"], data["area_m2"])

    reference_points = [r.to_dict() for r in FloorUValueReferencePoint.query.all()]
    result = calc.interpolate_floor_u_value(p_a_ratio, resistance, reference_points)
    result["thermal_resistance"] = resistance
    return jsonify(result)
