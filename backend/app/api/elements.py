from flask import jsonify, request

from .. import calculations as calc
from ..extensions import db
from ..models import (
    PlantRoom, WallElement, RoofElement, RoofLightElement, FloorElement, DoorElement, Zone,
    FloorUValueReferencePoint,
)
from ..validation import validate, error_response
from . import api_bp

ELEMENT_TYPES = {
    "walls": (WallElement, [
        "location", "construction", "reference", "height", "width", "window_pct", "window_frame_type",
        "age_band_id", "wall_u_value", "window_u_value", "proposed_wall_u_value", "proposed_window_u_value",
        "wall_measure_id", "window_measure_id", "geometry", "notes",
    ]),
    "roofs": (RoofElement, [
        "location", "construction", "reference", "roof_type", "has_loft", "area", "perimeter", "age_band_id",
        "u_value", "proposed_u_value", "measure_id", "geometry", "notes",
    ]),
    "rooflights": (RoofLightElement, [
        "roof_id", "location", "construction", "reference", "height", "width", "qty", "u_value",
        "proposed_u_value", "measure_id", "notes",
    ]),
    "floors": (FloorElement, [
        "location", "construction", "reference", "area", "perimeter", "thickness_m", "k_value", "age_band_id",
        "u_value", "proposed_u_value", "measure_id", "geometry", "notes",
    ]),
    "doors": (DoorElement, [
        "location", "construction", "reference", "door_type", "height", "width", "qty", "age_band_id", "u_value",
        "proposed_u_value", "measure_id", "notes",
    ]),
    "zones": (Zone, ["name", "area_m2", "height_m"]),
}

# height/width/area/qty/u_value are real measurements - a row can be created without them
# (e.g. "copy from roof" leaves them blank on purpose) but if you send a value it can't be
# zero or negative, and once set it can't be blanked back out to zero either.
VALIDATION_RULES = {
    "walls": dict(
        strict_positive=["height", "width", "wall_u_value", "window_u_value"],
        positive_if_set=["proposed_wall_u_value", "proposed_window_u_value"],
        fraction_if_set=["window_pct"],
    ),
    "roofs": dict(
        strict_positive=["area", "u_value"],
        positive_if_set=["proposed_u_value", "perimeter"],
    ),
    "rooflights": dict(
        strict_positive=["height", "width", "qty", "u_value"],
        positive_if_set=["proposed_u_value"],
    ),
    "floors": dict(
        # u_value is deliberately not strict-positive here - if area/perimeter/thickness_m/k_value
        # are all present it gets calculated automatically below instead of being typed in.
        strict_positive=["area"],
        positive_if_set=["proposed_u_value", "perimeter", "thickness_m", "k_value"],
        non_negative_if_set=["u_value"],
    ),
    "doors": dict(
        strict_positive=["height", "width", "qty", "u_value"],
        positive_if_set=["proposed_u_value"],
    ),
    "zones": dict(
        strict_positive=["area_m2", "height_m"],
    ),
}

FLOOR_U_VALUE_INPUTS = {"area", "perimeter", "thickness_m", "k_value"}
DEFAULT_FLOOR_THICKNESS_M = 0.1
DEFAULT_FLOOR_K_VALUE = 1.63


def _autocalc_floor_u_value(row, touched_fields):
    if not (touched_fields & FLOOR_U_VALUE_INPUTS):
        return
    if not (row.area and row.perimeter and row.thickness_m and row.k_value):
        return
    resistance = calc.floor_thermal_resistance(row.thickness_m, row.k_value)
    p_a_ratio = calc.floor_perimeter_area_ratio(row.perimeter, row.area)
    reference_points = [r.to_dict() for r in FloorUValueReferencePoint.query.all()]
    result = calc.interpolate_floor_u_value(p_a_ratio, resistance, reference_points)
    if result.get("u_value") is not None:
        row.u_value = result["u_value"]


def _model_and_fields(element_type):
    if element_type not in ELEMENT_TYPES:
        return None, None
    return ELEMENT_TYPES[element_type]


@api_bp.get("/plant-rooms/<int:room_id>/<element_type>")
def list_elements(room_id, element_type):
    model, _ = _model_and_fields(element_type)
    if model is None:
        return jsonify({"error": f"Unknown element type '{element_type}'"}), 404
    db.get_or_404(PlantRoom, room_id)
    rows = model.query.filter_by(plant_room_id=room_id).order_by(model.id).all()
    return jsonify([r.to_dict() for r in rows])


@api_bp.post("/plant-rooms/<int:room_id>/<element_type>")
def create_element(room_id, element_type):
    model, fields = _model_and_fields(element_type)
    if model is None:
        return jsonify({"error": f"Unknown element type '{element_type}'"}), 404
    db.get_or_404(PlantRoom, room_id)
    data = request.get_json(force=True) or {}

    errors = validate(data, **VALIDATION_RULES.get(element_type, {}))
    if errors:
        return error_response(errors)

    row = model(plant_room_id=room_id)
    for field in fields:
        if field in data:
            setattr(row, field, data[field])

    if element_type == "floors":
        # column defaults only apply once flushed to the db, so set them here too -
        # otherwise a brand new row with just area+perimeter wouldn't auto-calculate yet
        if row.thickness_m is None:
            row.thickness_m = DEFAULT_FLOOR_THICKNESS_M
        if row.k_value is None:
            row.k_value = DEFAULT_FLOOR_K_VALUE
        _autocalc_floor_u_value(row, (set(data.keys()) & FLOOR_U_VALUE_INPUTS) | {"thickness_m", "k_value"})

    db.session.add(row)
    db.session.commit()
    return jsonify(row.to_dict()), 201


@api_bp.put("/<element_type>/<int:element_id>")
def update_element(element_type, element_id):
    model, fields = _model_and_fields(element_type)
    if model is None:
        return jsonify({"error": f"Unknown element type '{element_type}'"}), 404
    row = db.get_or_404(model, element_id)
    data = request.get_json(force=True) or {}

    errors = validate(data, **VALIDATION_RULES.get(element_type, {}))
    if errors:
        return error_response(errors)

    for field in fields:
        if field in data:
            setattr(row, field, data[field])

    if element_type == "floors":
        _autocalc_floor_u_value(row, set(data.keys()) & FLOOR_U_VALUE_INPUTS)

    db.session.commit()
    return jsonify(row.to_dict())


@api_bp.delete("/<element_type>/<int:element_id>")
def delete_element(element_type, element_id):
    model, _ = _model_and_fields(element_type)
    if model is None:
        return jsonify({"error": f"Unknown element type '{element_type}'"}), 404
    row = db.get_or_404(model, element_id)
    db.session.delete(row)
    db.session.commit()
    return "", 204
