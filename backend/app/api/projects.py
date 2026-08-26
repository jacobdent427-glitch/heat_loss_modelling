from flask import jsonify, request

from ..extensions import db
from ..models import Project
from . import api_bp


@api_bp.get("/projects")
def list_projects():
    projects = Project.query.order_by(Project.updated_at.desc()).all()
    return jsonify([p.to_dict() for p in projects])


@api_bp.post("/projects")
def create_project():
    data = request.get_json(force=True) or {}
    if not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    project = Project(name=data["name"], address=data.get("address"), notes=data.get("notes"))
    db.session.add(project)
    db.session.commit()
    return jsonify(project.to_dict()), 201


@api_bp.get("/projects/<int:project_id>")
def get_project(project_id):
    project = db.get_or_404(Project, project_id)
    return jsonify(project.to_dict(include_plant_rooms=True))


@api_bp.put("/projects/<int:project_id>")
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    data = request.get_json(force=True) or {}
    for field in ("name", "address", "notes"):
        if field in data:
            setattr(project, field, data[field])
    db.session.commit()
    return jsonify(project.to_dict())


@api_bp.delete("/projects/<int:project_id>")
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return "", 204
