import os

from flask import Flask
from flask_cors import CORS

from .extensions import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    db_path = os.path.join(app.instance_path, "heat_loss.sqlite3")
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", f"sqlite:///{db_path}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    from .api import api_bp
    app.register_blueprint(api_bp)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()
        from .seed import seed_all
        seed_all()

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app
