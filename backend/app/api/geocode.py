import urllib.parse
import urllib.request
import json

from flask import jsonify, request

from . import api_bp

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "BTG-Eddisons-HeatLossModellingApp/1.0 (internal survey tool)"


@api_bp.get("/geocode")
def geocode():
    address = request.args.get("address", "").strip()
    if not address:
        return jsonify({"error": "address query param is required"}), 400

    query = urllib.parse.urlencode({"q": address, "format": "json", "limit": 1})
    req = urllib.request.Request(f"{NOMINATIM_URL}?{query}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": f"Geocoding request failed: {e}"}), 502

    if not results:
        return jsonify({"error": "No location found for that address"}), 404

    result = results[0]
    return jsonify({
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "display_name": result.get("display_name"),
    })
