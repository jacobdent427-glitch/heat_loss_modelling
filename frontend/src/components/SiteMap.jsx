import { useEffect, useState } from "react";
import { useJsApiLoader, GoogleMap, Polygon, Polyline } from "@react-google-maps/api";
import { api } from "../api";

const GOOGLE_LIBRARIES = ["geometry"];
const DEFAULT_CENTER = { lat: 51.5074, lng: -0.1278 }; // London - used only until the project's address geocodes
const MAP_CONTAINER_STYLE = { width: "100%", height: "600px" };
const LAYER_COLORS = { wall: "#e8a543", roof: "#3388ff", floor: "#2ecc71" };

function toLatLngLiterals(pairs) {
  return pairs.map(([lat, lng]) => ({ lat, lng }));
}

function polylineLengthMetres(points) {
  const g = window.google.maps.geometry.spherical;
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    total += g.computeDistanceBetween(new window.google.maps.LatLng(points[i - 1]), new window.google.maps.LatLng(points[i]));
  }
  return total;
}

function polygonAreaSqMetres(points) {
  if (points.length < 3) return 0;
  return window.google.maps.geometry.spherical.computeArea(points.map((p) => new window.google.maps.LatLng(p)));
}

export default function SiteMap({ project, room, ageBands, elementApi, refreshAll }) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: "google-map-script",
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
    libraries: GOOGLE_LIBRARIES,
  });

  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [geoError, setGeoError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [visible, setVisible] = useState({ wall: true, roof: true, floor: true });
  const [drawMode, setDrawMode] = useState(null); // null | 'wall' | 'roof' | 'floor'
  const [drawPoints, setDrawPoints] = useState([]);
  const [finishedShape, setFinishedShape] = useState(null); // { type, points, measurement }
  const [showFloorPicker, setShowFloorPicker] = useState(false);
  const [floorSourceRoofId, setFloorSourceRoofId] = useState("");

  const geocodeAndCenter = (address, { persist } = {}) => {
    setGeoError(null);
    return api
      .geocode(address)
      .then((res) => {
        setCenter({ lat: res.latitude, lng: res.longitude });
        if (persist) api.updateProject(project.id, { latitude: res.latitude, longitude: res.longitude });
      })
      .catch((e) => setGeoError(e.message));
  };

  useEffect(() => {
    if (project.latitude != null && project.longitude != null) {
      setCenter({ lat: project.latitude, lng: project.longitude });
      return;
    }
    if (!project.address) return;
    geocodeAndCenter(project.address, { persist: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project.id]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    geocodeAndCenter(searchQuery, { persist: true });
  };

  const startDrawing = (type) => {
    setDrawMode(type);
    setDrawPoints([]);
    setFinishedShape(null);
    setShowFloorPicker(false);
  };

  const cancelDrawing = () => {
    setDrawMode(null);
    setDrawPoints([]);
  };

  const handleMapClick = (e) => {
    if (!drawMode) return;
    setDrawPoints((prev) => [...prev, { lat: e.latLng.lat(), lng: e.latLng.lng() }]);
  };

  const finishDrawing = () => {
    const measurement = drawMode === "wall" ? polylineLengthMetres(drawPoints) : polygonAreaSqMetres(drawPoints);
    setFinishedShape({ type: drawMode, points: drawPoints, measurement });
    setDrawMode(null);
  };

  const copyFloorFromRoof = () => {
    const roof = room.roofs.find((r) => String(r.id) === String(floorSourceRoofId));
    if (!roof) return;
    setFinishedShape({
      type: "floor",
      points: roof.geometry ? toLatLngLiterals(roof.geometry) : [],
      measurement: roof.area || 0,
      copiedLocation: roof.location,
    });
    setShowFloorPicker(false);
  };

  const handleAccept = async (fields) => {
    const geometry = finishedShape.points.length ? finishedShape.points.map((p) => [p.lat, p.lng]) : null;
    const type = finishedShape.type === "wall" ? "walls" : finishedShape.type === "roof" ? "roofs" : "floors";
    await elementApi(type).onAdd({ ...fields, geometry });
    setFinishedShape(null);
    setDrawPoints([]);
    refreshAll();
  };

  const handleDiscard = () => {
    setFinishedShape(null);
    setDrawPoints([]);
    setFloorSourceRoofId("");
  };

  if (loadError) {
    return <p className="error">Failed to load Google Maps: {loadError.message}</p>;
  }
  if (!isLoaded) {
    return <p>Loading map...</p>;
  }

  return (
    <div className="site-map">
      <form className="inline-form" onSubmit={handleSearch}>
        <label>
          Search for a location
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="e.g. a postcode, if the full address isn't found"
          />
        </label>
        <button type="submit">Go</button>
      </form>

      {geoError && (
        <p className="error">
          Couldn't locate that address ({geoError}). Try a more specific or simpler search above (e.g. just the
          postcode).
        </p>
      )}

      <div className="map-overlay-toggles">
        <span className="muted">Show on map:</span>
        {["wall", "roof", "floor"].map((cat) => (
          <label key={cat} className="overlay-toggle" style={{ borderColor: LAYER_COLORS[cat] }}>
            <input
              type="checkbox"
              checked={visible[cat]}
              onChange={(e) => setVisible((prev) => ({ ...prev, [cat]: e.target.checked }))}
            />
            {cat === "wall" ? "Walls" : cat === "roof" ? "Roofs" : "Floors"}
          </label>
        ))}
      </div>

      <div className="map-with-panel">
        <div className="map-wrap">
          <GoogleMap
            mapContainerStyle={MAP_CONTAINER_STYLE}
            center={center}
            zoom={20}
            mapTypeId="satellite"
            onClick={handleMapClick}
            options={{ streetViewControl: false, mapTypeControl: false, fullscreenControl: false }}
          >
            {visible.wall &&
              room.walls
                .filter((w) => w.geometry)
                .map((w) => (
                  <Polyline
                    key={`wall-${w.id}`}
                    path={toLatLngLiterals(w.geometry)}
                    options={{ strokeColor: LAYER_COLORS.wall, strokeWeight: 4 }}
                  />
                ))}

            {visible.roof &&
              room.roofs
                .filter((r) => r.geometry)
                .map((r) => (
                  <Polygon
                    key={`roof-${r.id}`}
                    path={toLatLngLiterals(r.geometry)}
                    options={{ fillColor: LAYER_COLORS.roof, strokeColor: LAYER_COLORS.roof, fillOpacity: 0.35 }}
                  />
                ))}

            {visible.floor &&
              room.floors
                .filter((f) => f.geometry)
                .map((f) => (
                  <Polygon
                    key={`floor-${f.id}`}
                    path={toLatLngLiterals(f.geometry)}
                    options={{ fillColor: LAYER_COLORS.floor, strokeColor: LAYER_COLORS.floor, fillOpacity: 0.35 }}
                  />
                ))}

            {drawMode === "wall" && drawPoints.length > 0 && (
              <Polyline path={drawPoints} options={{ strokeColor: "#ff2d55", strokeWeight: 5 }} />
            )}
            {(drawMode === "roof" || drawMode === "floor") && drawPoints.length > 0 && (
              <Polygon path={drawPoints} options={{ fillColor: "#ff2d55", strokeColor: "#ff2d55", fillOpacity: 0.3 }} />
            )}
            {finishedShape &&
              (finishedShape.type === "wall" ? (
                <Polyline path={finishedShape.points} options={{ strokeColor: "#ff2d55", strokeWeight: 5 }} />
              ) : finishedShape.points.length > 0 ? (
                <Polygon path={finishedShape.points} options={{ fillColor: "#ff2d55", strokeColor: "#ff2d55", fillOpacity: 0.3 }} />
              ) : null)}
          </GoogleMap>
        </div>

        <div className="map-side-panel">
          {!drawMode && !finishedShape && !showFloorPicker && (
            <>
              <h3>Add to map</h3>
              <button onClick={() => startDrawing("wall")}>+ Wall</button>
              <button onClick={() => startDrawing("roof")}>+ Roof</button>
              <button onClick={() => setShowFloorPicker(true)}>+ Floor</button>
            </>
          )}

          {showFloorPicker && !drawMode && !finishedShape && (
            <>
              <h3>Add a floor</h3>
              <p className="muted">A floor is normally the same footprint as the roof above it.</p>
              <label>
                Copy area &amp; outline from roof
                <select value={floorSourceRoofId} onChange={(e) => setFloorSourceRoofId(e.target.value)}>
                  <option value="">-</option>
                  {room.roofs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.location || `Roof ${r.id}`} ({r.area?.toFixed(1)} m2)
                    </option>
                  ))}
                </select>
              </label>
              <button onClick={copyFloorFromRoof} disabled={!floorSourceRoofId}>
                Copy from roof
              </button>
              <button onClick={() => startDrawing("floor")}>Or draw floor manually</button>
              <button className="danger" onClick={() => setShowFloorPicker(false)}>
                Cancel
              </button>
            </>
          )}

          {drawMode && (
            <>
              <h3>Drawing {drawMode === "wall" ? "a wall" : drawMode === "roof" ? "a roof" : "a floor"}</h3>
              <p className="muted">
                Click points along the {drawMode === "wall" ? "wall" : "outline"} on the map.
                {drawMode !== "wall" && " Need at least 3 points."}
              </p>
              <p>{drawPoints.length} point(s) placed.</p>
              <div className="map-attribute-actions">
                <button onClick={finishDrawing} disabled={drawMode === "wall" ? drawPoints.length < 2 : drawPoints.length < 3}>
                  Finish
                </button>
                <button className="danger" onClick={cancelDrawing}>
                  Cancel
                </button>
              </div>
            </>
          )}

          {finishedShape && (
            <AttributeForm shape={finishedShape} ageBands={ageBands} onAccept={handleAccept} onCancel={handleDiscard} />
          )}
        </div>
      </div>
    </div>
  );
}

function AttributeForm({ shape, ageBands, onAccept, onCancel }) {
  const isWall = shape.type === "wall";
  const isRoof = shape.type === "roof";
  const isFloor = shape.type === "floor";
  const [fields, setFields] = useState({
    location: shape.copiedLocation || "",
    reference: "",
    age_band_id: "",
    height: 0,
    window_pct: 0,
    window_frame_type: "Other",
    wall_u_value: 0,
    window_u_value: 0,
    roof_type: "Pitched",
    has_loft: false,
    u_value: 0,
  });

  const ageBandOptions = ageBands.map((a) => ({ value: a.id, label: a.period_label }));
  const findAgeBand = (id) => ageBands.find((a) => String(a.id) === String(id));

  const set = (key) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setFields((prev) => ({ ...prev, [key]: val }));
  };

  const onAgeBandChange = (e) => {
    const id = e.target.value;
    const band = findAgeBand(id);
    setFields((prev) => {
      const next = { ...prev, age_band_id: id || null };
      if (!band) return next;
      if (isWall) {
        if (band.wall_u != null) next.wall_u_value = band.wall_u;
        const windowU = prev.window_frame_type === "Metal" ? band.window_metal_u : band.window_other_u;
        if (windowU != null) next.window_u_value = windowU;
      } else if (isRoof) {
        const u = band[prev.roof_type === "Flat" ? "flat_roof_u" : "pitched_roof_u"];
        if (u != null) next.u_value = u;
      } else if (isFloor && band.floor_u != null) {
        next.u_value = band.floor_u;
      }
      return next;
    });
  };

  const measurementLabel = isWall ? `${shape.measurement.toFixed(2)} m (length)` : `${shape.measurement.toFixed(2)} m² (area)`;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (isWall) {
      onAccept({
        location: fields.location,
        reference: fields.reference,
        age_band_id: fields.age_band_id || null,
        height: parseFloat(fields.height) || 0,
        width: shape.measurement,
        window_pct: parseFloat(fields.window_pct) || 0,
        window_frame_type: fields.window_frame_type,
        wall_u_value: parseFloat(fields.wall_u_value) || 0,
        window_u_value: parseFloat(fields.window_u_value) || 0,
      });
    } else if (isRoof) {
      onAccept({
        location: fields.location,
        reference: fields.reference,
        age_band_id: fields.age_band_id || null,
        roof_type: fields.roof_type,
        has_loft: fields.has_loft,
        area: shape.measurement,
        u_value: parseFloat(fields.u_value) || 0,
      });
    } else {
      onAccept({
        location: fields.location,
        reference: fields.reference,
        age_band_id: fields.age_band_id || null,
        area: shape.measurement,
        u_value: parseFloat(fields.u_value) || 0,
      });
    }
  };

  return (
    <form className="map-attribute-panel" onSubmit={handleSubmit}>
      <h3>Measured: {measurementLabel}</h3>

      <div className="map-attribute-grid-vertical">
        <label>
          Location
          <input type="text" value={fields.location} onChange={set("location")} placeholder="e.g. West wing" />
        </label>
        <label>
          Reference
          <input type="text" value={fields.reference} onChange={set("reference")} />
        </label>
        <label>
          Age band
          <select value={fields.age_band_id || ""} onChange={onAgeBandChange}>
            <option value="">-</option>
            {ageBandOptions.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        {isWall ? (
          <>
            <label>
              Height (m)
              <input type="number" step="any" value={fields.height} onChange={set("height")} />
            </label>
            <label>
              % windows (0-1)
              <input type="number" step="any" value={fields.window_pct} onChange={set("window_pct")} />
            </label>
            <label>
              Window frame
              <select value={fields.window_frame_type} onChange={set("window_frame_type")}>
                <option value="Other">Other</option>
                <option value="Metal">Metal</option>
              </select>
            </label>
            <label>
              Wall U
              <input type="number" step="any" value={fields.wall_u_value} onChange={set("wall_u_value")} />
            </label>
            <label>
              Window U
              <input type="number" step="any" value={fields.window_u_value} onChange={set("window_u_value")} />
            </label>
          </>
        ) : isRoof ? (
          <>
            <label>
              Roof type
              <select value={fields.roof_type} onChange={set("roof_type")}>
                <option value="Pitched">Pitched</option>
                <option value="Flat">Flat</option>
              </select>
            </label>
            <label className="checkbox-label">
              <input type="checkbox" checked={fields.has_loft} onChange={set("has_loft")} />
              Has loft?
            </label>
            <label>
              U value
              <input type="number" step="any" value={fields.u_value} onChange={set("u_value")} />
            </label>
          </>
        ) : (
          <label>
            U value
            <input type="number" step="any" value={fields.u_value} onChange={set("u_value")} />
          </label>
        )}
      </div>

      <div className="map-attribute-actions">
        <button type="submit">Accept &amp; save</button>
        <button type="button" className="danger" onClick={onCancel}>
          Discard
        </button>
      </div>
    </form>
  );
}
