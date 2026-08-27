from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    notes = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    plant_rooms = db.relationship(
        "PlantRoom", backref="project", cascade="all, delete-orphan", order_by="PlantRoom.id"
    )

    def to_dict(self, include_plant_rooms=False):
        data = {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "notes": self.notes,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "plant_room_count": len(self.plant_rooms),
        }
        if include_plant_rooms:
            data["plant_rooms"] = [p.to_dict() for p in self.plant_rooms]
        return data


class PlantRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("project.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)

    fuel_type = db.Column(db.String(50), default="Natural gas")
    annual_fuel_usage_kwh = db.Column(db.Float, default=0.0)
    unit_rate_per_kwh = db.Column(db.Float)
    standing_charge_per_day = db.Column(db.Float)
    boiler_efficiency = db.Column(db.Float, default=0.85)

    uses_gas_kitchen = db.Column(db.Boolean, default=False)
    kitchen_gas_pct = db.Column(db.Float, default=0.02)

    dhw_method = db.Column(db.String(30), default="manual")
    dhw_manual_kwh = db.Column(db.Float, default=0.0)
    dhw_summer_baseload_kwh_month = db.Column(db.Float)
    dhw_tank_volume_litres = db.Column(db.Float)
    dhw_tank_temp_rise_c = db.Column(db.Float, default=45.0)
    dhw_tank_cycles_per_day = db.Column(db.Float, default=1.0)
    dhw_efficiency = db.Column(db.Float, default=0.85)

    ach = db.Column(db.Float, default=0.5)
    internal_setpoint_c = db.Column(db.Float, default=20.0)
    external_design_temp_c = db.Column(db.Float, default=-4.0)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    walls = db.relationship("WallElement", backref="plant_room", cascade="all, delete-orphan", order_by="WallElement.id")
    roofs = db.relationship("RoofElement", backref="plant_room", cascade="all, delete-orphan", order_by="RoofElement.id")
    rooflights = db.relationship("RoofLightElement", backref="plant_room", cascade="all, delete-orphan", order_by="RoofLightElement.id")
    floors = db.relationship("FloorElement", backref="plant_room", cascade="all, delete-orphan", order_by="FloorElement.id")
    doors = db.relationship("DoorElement", backref="plant_room", cascade="all, delete-orphan", order_by="DoorElement.id")
    zones = db.relationship("Zone", backref="plant_room", cascade="all, delete-orphan", order_by="Zone.id")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "name": self.name,
            "fuel_type": self.fuel_type,
            "annual_fuel_usage_kwh": self.annual_fuel_usage_kwh,
            "unit_rate_per_kwh": self.unit_rate_per_kwh,
            "standing_charge_per_day": self.standing_charge_per_day,
            "boiler_efficiency": self.boiler_efficiency,
            "uses_gas_kitchen": self.uses_gas_kitchen,
            "kitchen_gas_pct": self.kitchen_gas_pct,
            "dhw_method": self.dhw_method,
            "dhw_manual_kwh": self.dhw_manual_kwh,
            "dhw_summer_baseload_kwh_month": self.dhw_summer_baseload_kwh_month,
            "dhw_tank_volume_litres": self.dhw_tank_volume_litres,
            "dhw_tank_temp_rise_c": self.dhw_tank_temp_rise_c,
            "dhw_tank_cycles_per_day": self.dhw_tank_cycles_per_day,
            "dhw_efficiency": self.dhw_efficiency,
            "ach": self.ach,
            "internal_setpoint_c": self.internal_setpoint_c,
            "external_design_temp_c": self.external_design_temp_c,
            "notes": self.notes,
        }


class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    area_m2 = db.Column(db.Float, default=0.0)
    height_m = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "name": self.name,
            "area_m2": self.area_m2,
            "height_m": self.height_m,
            "volume_m3": (self.area_m2 or 0) * (self.height_m or 0),
        }


class ImprovementMeasure(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    applies_to = db.Column(db.String(100), default="")
    lifetime_years = db.Column(db.Float)
    cost_per_m2 = db.Column(db.Float)
    cost_guidance = db.Column(db.Text)
    typical_u_value = db.Column(db.Float)
    u_value_guidance = db.Column(db.Text)
    is_custom = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "applies_to": [a for a in self.applies_to.split(",") if a] if self.applies_to else [],
            "lifetime_years": self.lifetime_years,
            "cost_per_m2": self.cost_per_m2,
            "cost_guidance": self.cost_guidance,
            "typical_u_value": self.typical_u_value,
            "u_value_guidance": self.u_value_guidance,
            "is_custom": self.is_custom,
        }


class EmissionFactor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fuel_type = db.Column(db.String(50), nullable=False, unique=True)
    unit_rate_per_kwh = db.Column(db.Float)
    standing_charge_per_day = db.Column(db.Float)
    scope_1_2_kg_per_kwh = db.Column(db.Float)
    scope_3_kg_per_kwh = db.Column(db.Float)
    source = db.Column(db.String(300))

    def to_dict(self):
        return {
            "id": self.id,
            "fuel_type": self.fuel_type,
            "unit_rate_per_kwh": self.unit_rate_per_kwh,
            "standing_charge_per_day": self.standing_charge_per_day,
            "scope_1_2_kg_per_kwh": self.scope_1_2_kg_per_kwh,
            "scope_3_kg_per_kwh": self.scope_3_kg_per_kwh,
            "source": self.source,
        }


class FloorUValueReferencePoint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    p_a_ratio = db.Column(db.Float, nullable=False)
    resistance = db.Column(db.Float, nullable=False)
    u_value = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "p_a_ratio": self.p_a_ratio,
            "resistance": self.resistance,
            "u_value": self.u_value,
        }


class AgeBandUValue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    period_label = db.Column(db.String(100), nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    wall_u = db.Column(db.Float)
    floor_u = db.Column(db.Float)
    pitched_roof_u = db.Column(db.Float)
    flat_roof_u = db.Column(db.Float)
    window_metal_u = db.Column(db.Float)
    window_other_u = db.Column(db.Float)
    window_area_pct_note = db.Column(db.String(50))
    pedestrian_door_u = db.Column(db.Float)
    vehicle_door_u = db.Column(db.Float)
    entrance_door_u = db.Column(db.Float)
    air_permeability = db.Column(db.Float)

    def to_dict(self):
        return {
            "id": self.id,
            "period_label": self.period_label,
            "sort_order": self.sort_order,
            "wall_u": self.wall_u,
            "floor_u": self.floor_u,
            "pitched_roof_u": self.pitched_roof_u,
            "flat_roof_u": self.flat_roof_u,
            "window_metal_u": self.window_metal_u,
            "window_other_u": self.window_other_u,
            "window_area_pct_note": self.window_area_pct_note,
            "pedestrian_door_u": self.pedestrian_door_u,
            "vehicle_door_u": self.vehicle_door_u,
            "entrance_door_u": self.entrance_door_u,
            "air_permeability": self.air_permeability,
        }


class WallElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)

    location = db.Column(db.String(200))
    construction = db.Column(db.String(200))  # free-text note, separate from age_band_id
    reference = db.Column(db.String(200))
    height = db.Column(db.Float, default=0.0)
    width = db.Column(db.Float, default=0.0)
    window_pct = db.Column(db.Float, default=0.0)  # 0-1
    window_frame_type = db.Column(db.String(10), default="Other")  # Metal | Other

    age_band_id = db.Column(db.Integer, db.ForeignKey("age_band_u_value.id"))
    wall_u_value = db.Column(db.Float, default=0.0)
    window_u_value = db.Column(db.Float, default=0.0)

    proposed_wall_u_value = db.Column(db.Float)
    proposed_window_u_value = db.Column(db.Float)
    wall_measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))
    window_measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))

    geometry = db.Column(db.JSON)

    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "location": self.location,
            "construction": self.construction,
            "reference": self.reference,
            "height": self.height,
            "width": self.width,
            "window_pct": self.window_pct,
            "window_frame_type": self.window_frame_type,
            "age_band_id": self.age_band_id,
            "wall_u_value": self.wall_u_value,
            "window_u_value": self.window_u_value,
            "proposed_wall_u_value": self.proposed_wall_u_value,
            "proposed_window_u_value": self.proposed_window_u_value,
            "wall_measure_id": self.wall_measure_id,
            "window_measure_id": self.window_measure_id,
            "geometry": self.geometry,
            "notes": self.notes,
        }


class RoofElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)

    location = db.Column(db.String(200))
    construction = db.Column(db.String(200))
    reference = db.Column(db.String(200))
    roof_type = db.Column(db.String(20), default="Pitched")  # Pitched | Flat
    has_loft = db.Column(db.Boolean, default=False)
    area = db.Column(db.Float, default=0.0)
    perimeter = db.Column(db.Float)
    age_band_id = db.Column(db.Integer, db.ForeignKey("age_band_u_value.id"))
    u_value = db.Column(db.Float, default=0.0)

    proposed_u_value = db.Column(db.Float)
    measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))

    geometry = db.Column(db.JSON)

    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "location": self.location,
            "construction": self.construction,
            "reference": self.reference,
            "roof_type": self.roof_type,
            "has_loft": self.has_loft,
            "geometry": self.geometry,
            "area": self.area,
            "perimeter": self.perimeter,
            "age_band_id": self.age_band_id,
            "u_value": self.u_value,
            "proposed_u_value": self.proposed_u_value,
            "measure_id": self.measure_id,
            "notes": self.notes,
        }


class RoofLightElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)

    roof_id = db.Column(db.Integer, db.ForeignKey("roof_element.id"))

    location = db.Column(db.String(200))
    construction = db.Column(db.String(200))
    reference = db.Column(db.String(200))
    height = db.Column(db.Float, default=0.0)
    width = db.Column(db.Float, default=0.0)
    qty = db.Column(db.Float, default=1.0)
    u_value = db.Column(db.Float, default=0.0)

    proposed_u_value = db.Column(db.Float)
    measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))

    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "roof_id": self.roof_id,
            "location": self.location,
            "construction": self.construction,
            "reference": self.reference,
            "height": self.height,
            "width": self.width,
            "qty": self.qty,
            "u_value": self.u_value,
            "proposed_u_value": self.proposed_u_value,
            "measure_id": self.measure_id,
            "notes": self.notes,
        }


class FloorElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)

    location = db.Column(db.String(200))
    construction = db.Column(db.String(200))
    reference = db.Column(db.String(200))
    area = db.Column(db.Float, default=0.0)
    perimeter = db.Column(db.Float)
    thickness_m = db.Column(db.Float, default=0.1)
    k_value = db.Column(db.Float, default=1.63)
    age_band_id = db.Column(db.Integer, db.ForeignKey("age_band_u_value.id"))
    u_value = db.Column(db.Float, default=0.0)

    proposed_u_value = db.Column(db.Float)
    measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))

    geometry = db.Column(db.JSON)

    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "location": self.location,
            "construction": self.construction,
            "reference": self.reference,
            "area": self.area,
            "perimeter": self.perimeter,
            "thickness_m": self.thickness_m,
            "k_value": self.k_value,
            "age_band_id": self.age_band_id,
            "u_value": self.u_value,
            "proposed_u_value": self.proposed_u_value,
            "measure_id": self.measure_id,
            "geometry": self.geometry,
            "notes": self.notes,
        }


class DoorElement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plant_room_id = db.Column(db.Integer, db.ForeignKey("plant_room.id"), nullable=False)

    location = db.Column(db.String(200))
    construction = db.Column(db.String(200))
    reference = db.Column(db.String(200))
    door_type = db.Column(db.String(20), default="Pedestrian")  # Pedestrian | Vehicle | Entrance
    height = db.Column(db.Float, default=0.0)
    width = db.Column(db.Float, default=0.0)
    qty = db.Column(db.Float, default=1.0)
    age_band_id = db.Column(db.Integer, db.ForeignKey("age_band_u_value.id"))
    u_value = db.Column(db.Float, default=0.0)

    proposed_u_value = db.Column(db.Float)
    measure_id = db.Column(db.Integer, db.ForeignKey("improvement_measure.id"))

    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "plant_room_id": self.plant_room_id,
            "location": self.location,
            "construction": self.construction,
            "reference": self.reference,
            "door_type": self.door_type,
            "height": self.height,
            "width": self.width,
            "qty": self.qty,
            "age_band_id": self.age_band_id,
            "u_value": self.u_value,
            "proposed_u_value": self.proposed_u_value,
            "measure_id": self.measure_id,
            "notes": self.notes,
        }
