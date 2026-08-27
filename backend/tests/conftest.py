import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    flask_app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    yield flask_app
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def project(client):
    res = client.post("/api/projects", json={"name": "Test Project", "address": "1 Test Street"})
    return res.get_json()


@pytest.fixture
def plant_room(client, project):
    res = client.post(f"/api/projects/{project['id']}/plant-rooms", json={"name": "Test Plant Room"})
    return res.get_json()


@pytest.fixture
def wall(client, plant_room):
    res = client.post(
        f"/api/plant-rooms/{plant_room['id']}/walls",
        json={"location": "North", "height": 3, "width": 10, "window_pct": 0.2, "wall_u_value": 1.0, "window_u_value": 2.0},
    )
    return res.get_json()
