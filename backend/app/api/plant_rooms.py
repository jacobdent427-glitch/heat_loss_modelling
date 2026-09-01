from flask import jsonify, request

from ..extensions import db
from ..models import PlantRoom, Project, ImprovementMeasure
from ..results import plant_room_results, auto_propose_plant_room
from ..validation import validate, error_response
from . import api_bp

PLANT_ROOM_FIELDS = [
    "name", "fuel_type", "annual_fuel_usage_kwh", "unit_rate_per_kwh", "standing_charge_per_day",
    "boiler_efficiency",
    "uses_gas_kitchen", "kitchen_gas_method", "kitchen_gas_pct", "kitchen_hobs", "kitchen_hours_per_day",
    "uses_gas_science_lab", "lab_gas_method", "science_lab_gas_pct",
    "lab_count", "lab_burners_per_lab", "lab_uses_per_day", "lab_bunsen_kwh",
    "dhw_method", "dhw_manual_kwh", "dhw_summer_baseload_kwh_month", "dhw_tank_volume_litres",
    "dhw_tank_temp_rise_c", "dhw_tank_cycles_per_day", "dhw_efficiency", "ach", "internal_setpoint_c",
    "external_design_temp_c", "notes",
]

PLANT_ROOM_VALIDATION = dict(
    non_negative_if_set=[
        "annual_fuel_usage_kwh", "unit_rate_per_kwh", "standing_charge_per_day", "dhw_manual_kwh",
        "dhw_summer_baseload_kwh_month", "dhw_tank_volume_litres", "dhw_tank_temp_rise_c",
        "dhw_tank_cycles_per_day", "ach",
        "kitchen_hobs", "kitchen_hours_per_day",
        "lab_count", "lab_burners_per_lab", "lab_uses_per_day", "lab_bunsen_kwh",
    ],
    fraction_if_set=["boiler_efficiency", "kitchen_gas_pct", "science_lab_gas_pct", "dhw_efficiency"],
)


@api_bp.get("/projects/<int:project_id>/plant-rooms")
def list_plant_rooms(project_id):
    db.get_or_404(Project, project_id)
    rooms = PlantRoom.query.filter_by(project_id=project_id).order_by(PlantRoom.id).all()
    return jsonify([r.to_dict() for r in rooms])


@api_bp.post("/projects/<int:project_id>/plant-rooms")
def create_plant_room(project_id):
    db.get_or_404(Project, project_id)
    data = request.get_json(force=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    errors = validate(data, **PLANT_ROOM_VALIDATION)
    if errors:
        return error_response(errors)
    room = PlantRoom(project_id=project_id)
    for field in PLANT_ROOM_FIELDS:
        if field in data:
            setattr(room, field, data[field])
    db.session.add(room)
    db.session.commit()
    return jsonify(room.to_dict()), 201


@api_bp.get("/plant-rooms/<int:room_id>")
def get_plant_room(room_id):
    room = db.get_or_404(PlantRoom, room_id)
    data = room.to_dict()
    data["walls"] = [w.to_dict() for w in room.walls]
    data["roofs"] = [r.to_dict() for r in room.roofs]
    data["rooflights"] = [rl.to_dict() for rl in room.rooflights]
    data["floors"] = [f.to_dict() for f in room.floors]
    data["doors"] = [d.to_dict() for d in room.doors]
    data["zones"] = [z.to_dict() for z in room.zones]
    return jsonify(data)


@api_bp.put("/plant-rooms/<int:room_id>")
def update_plant_room(room_id):
    room = db.get_or_404(PlantRoom, room_id)
    data = request.get_json(force=True) or {}
    errors = validate(data, **PLANT_ROOM_VALIDATION)
    if errors:
        return error_response(errors)
    for field in PLANT_ROOM_FIELDS:
        if field in data:
            setattr(room, field, data[field])
    db.session.commit()
    return jsonify(room.to_dict())


@api_bp.delete("/plant-rooms/<int:room_id>")
def delete_plant_room(room_id):
    room = db.get_or_404(PlantRoom, room_id)
    db.session.delete(room)
    db.session.commit()
    return "", 204


@api_bp.get("/plant-rooms/<int:room_id>/results")
def get_plant_room_results(room_id):
    room = db.get_or_404(PlantRoom, room_id)
    return jsonify(plant_room_results(room))


@api_bp.post("/plant-rooms/<int:room_id>/auto-propose")
def auto_propose(room_id):
    room = db.get_or_404(PlantRoom, room_id)
    measures_by_name = {m.name: m for m in ImprovementMeasure.query.all()}
    changes = auto_propose_plant_room(room, measures_by_name)
    db.session.commit()
    return jsonify({"updated_count": len(changes), "changes": changes})
