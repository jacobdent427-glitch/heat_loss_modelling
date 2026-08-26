from flask import Blueprint

api_bp = Blueprint("api", __name__, url_prefix="/api")

from . import projects  # noqa: E402,F401
from . import plant_rooms  # noqa: E402,F401
from . import elements  # noqa: E402,F401
from . import measures  # noqa: E402,F401
from . import floor_calculator  # noqa: E402,F401
from . import overview  # noqa: E402,F401
from . import geocode  # noqa: E402,F401
