from flask import jsonify

from ..extensions import db
from ..models import PlantRoom, Project, ImprovementMeasure
from ..results import plant_room_results, apply_measure_cost_analysis
from . import api_bp


@api_bp.get("/projects/<int:project_id>/overview")
def project_overview(project_id):
    project = db.get_or_404(Project, project_id)
    rooms = PlantRoom.query.filter_by(project_id=project_id).order_by(PlantRoom.id).all()
    measures_by_id = {m.id: m for m in ImprovementMeasure.query.all()}

    plant_room_summaries = []
    all_measures = []
    total_existing_kw = 0.0
    total_improved_kw = 0.0

    for room in rooms:
        res = plant_room_results(room)
        total_existing_kw += res["peak_heat_loss_kw"]["existing"]
        total_improved_kw += res["peak_heat_loss_kw"]["improved"]

        enriched_measures = apply_measure_cost_analysis(res["measure_results"], measures_by_id)
        for m in enriched_measures:
            all_measures.append({"plant_room_id": room.id, "plant_room_name": room.name, **m})

        plant_room_summaries.append({
            "plant_room_id": room.id,
            "plant_room_name": room.name,
            "peak_heat_loss_kw": res["peak_heat_loss_kw"],
            "heat_loss_coefficient_w_per_k": res["heat_loss_coefficient_w_per_k"],
            "volume_m3": res["volume_m3"],
            "categories": res["categories"],
        })

    totals = {
        "total_cost_of_improvement_gbp": sum(m["cost_of_improvement_gbp"] for m in all_measures),
        "total_cost_saving_gbp_per_yr": sum(m["cost_saving_gbp_per_yr"] for m in all_measures),
        "total_thermal_energy_saving_kwh": sum(m["thermal_energy_saving_kwh"] for m in all_measures),
        "total_co2_saving_tonnes_per_yr": sum(m["co2_saving_tonnes_per_yr"] for m in all_measures),
        "total_lifetime_carbon_saving_tonnes": sum(m["lifetime_carbon_saving_tonnes"] for m in all_measures),
    }
    if totals["total_cost_saving_gbp_per_yr"]:
        totals["blended_payback_period_years"] = (
            totals["total_cost_of_improvement_gbp"] / totals["total_cost_saving_gbp_per_yr"]
        )
    else:
        totals["blended_payback_period_years"] = None

    return jsonify({
        "project": project.to_dict(),
        "plant_rooms": plant_room_summaries,
        "measures": all_measures,
        "totals": totals,
        "peak_heat_loss_kw_total": {"existing": total_existing_kw, "improved": total_improved_kw},
    })
