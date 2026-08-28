import { useEffect, useRef, useState } from "react";
import { useJsApiLoader, GoogleMap, Polygon, Polyline, Marker } from "@react-google-maps/api";
import { api } from "../api";

const GOOGLE_LIBRARIES = ["geometry"];
const DEFAULT_CENTER = { lat: 51.5074, lng: -0.1278 };
const MAP_CONTAINER_STYLE = { width: "100%", height: "600px" };
const LAYER_COLORS = { wall: "#e8a543", roof: "#3388ff", floor: "#2ecc71" };
const MAP_OPTIONS = {
  mapTypeId: "satellite",
  streetViewControl: false,
  mapTypeControl: true,
  fullscreenControl: false,
};

function toLatLngLiterals(pairs) {
  return pairs.map(([lat, lng]) => ({ lat, lng }));
}

function vertexIcon() {
  return {
    path: window.google.maps.SymbolPath.CIRCLE,
    scale: 6,
    fillColor: "#ff2d55",
    fillOpacity: 1,
    strokeColor: "#ffffff",
    strokeWeight: 2,
  };
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

function polygonPerimeterMetres(points) {
  if (points.length < 3) return 0;
  return polylineLengthMetres([...points, points[0]]);
}

function pointToSegmentDistSq(p, a, b) {
  const dx = b.lng - a.lng;
  const dy = b.lat - a.lat;
  if (dx === 0 && dy === 0) {
    const ddx = p.lng - a.lng;
    const ddy = p.lat - a.lat;
    return ddx * ddx + ddy * ddy;
  }
  let t = ((p.lng - a.lng) * dx + (p.lat - a.lat) * dy) / (dx * dx + dy * dy);
  t = Math.max(0, Math.min(1, t));
  const ddx = p.lng - (a.lng + t * dx);
  const ddy = p.lat - (a.lat + t * dy);
  return ddx * ddx + ddy * ddy;
}

function nearestEdgeIndex(points, click, closed) {
  const segCount = closed ? points.length : points.length - 1;
  let best = 0;
  let bestDist = Infinity;
  for (let i = 0; i < segCount; i++) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    const d = pointToSegmentDistSq(click, a, b);
    if (d < bestDist) {
      bestDist = d;
      best = i;
    }
  }
  return best;
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

  const [shapeKind, setShapeKind] = useState(null);
  const [phase, setPhase] = useState("idle");
  const [points, setPoints] = useState([]);
  const [copiedLocation, setCopiedLocation] = useState("");
  const [showFloorPicker, setShowFloorPicker] = useState(false);
  const [floorSourceRoofId, setFloorSourceRoofId] = useState("");
  const [acceptError, setAcceptError] = useState(null);

  const isWall = shapeKind === "wall";
  const minPoints = isWall ? 2 : 3;
  const measurement = isWall ? polylineLengthMetres(points) : polygonAreaSqMetres(points);
  const perimeter = isWall ? null : polygonPerimeterMetres(points);

  const phaseRef = useRef(phase);
  phaseRef.current = phase;
  const isWallRef = useRef(isWall);
  isWallRef.current = isWall;

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

  const startDrawing = (kind) => {
    setShapeKind(kind);
    setPhase("drawing");
    setPoints([]);
    setCopiedLocation("");
    setShowFloorPicker(false);
  };

  const cancelShape = () => {
    setShapeKind(null);
    setPhase("idle");
    setPoints([]);
    setCopiedLocation("");
    setFloorSourceRoofId("");
    setAcceptError(null);
  };

  const handleMapBackgroundClick = (e) => {
    if (phaseRef.current !== "drawing") return;
    setPoints((prev) => [...prev, { lat: e.latLng.lat(), lng: e.latLng.lng() }]);
  };

  const handleShapeClick = (e) => {
    if (phaseRef.current !== "drawing" && phaseRef.current !== "reviewing") return;
    e.stop();
    const newPoint = { lat: e.latLng.lat(), lng: e.latLng.lng() };
    setPoints((prev) => {
      const edge = e.edge != null ? e.edge : nearestEdgeIndex(prev, newPoint, !isWallRef.current);
      const next = [...prev];
      next.splice(edge + 1, 0, newPoint);
      return next;
    });
  };

  const movePoint = (index, latLng) => {
    setPoints((prev) => prev.map((p, i) => (i === index ? { lat: latLng.lat(), lng: latLng.lng() } : p)));
  };

  const deletePoint = (index) => {
    setPoints((prev) => prev.filter((_, i) => i !== index));
  };

  const finishDrawing = () => {
    if (points.length < minPoints) return;
    setPhase("reviewing");
  };

  const copyFloorFromRoof = () => {
    const roof = room.roofs.find((r) => String(r.id) === String(floorSourceRoofId));
    if (!roof) return;
    setShapeKind("floor");
    setPoints(roof.geometry ? toLatLngLiterals(roof.geometry) : []);
    setCopiedLocation(roof.location || "");
    setPhase("reviewing");
    setShowFloorPicker(false);
  };

  const handleAccept = async (fields) => {
    const geometry = points.length ? points.map((p) => [p.lat, p.lng]) : null;
    const type = shapeKind === "wall" ? "walls" : shapeKind === "roof" ? "roofs" : "floors";
    try {
      await elementApi(type).onAdd({ ...fields, geometry });
      setAcceptError(null);
      cancelShape();
    } catch (e) {
      // keep the drawing and the entered fields in place so nothing is lost - just show what's wrong
      setAcceptError(e);
    }
  };

  const handleDiscard = () => {
    cancelShape();
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
            onClick={handleMapBackgroundClick}
            options={MAP_OPTIONS}
          >
            {visible.wall &&
              room.walls
                .filter((w) => w.geometry)
                .map((w) => (
                  <Polyline
                    key={`wall-${w.id}`}
                    path={toLatLngLiterals(w.geometry)}
                    options={{ strokeColor: LAYER_COLORS.wall, strokeWeight: 6, strokeOpacity: 1, zIndex: 10 }}
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

            {phase !== "idle" &&
              points.length > 0 &&
              (isWall ? (
                <Polyline
                  path={points}
                  options={{ strokeColor: "#ff2d55", strokeWeight: 4 }}
                  onClick={handleShapeClick}
                />
              ) : (
                <Polygon
                  path={points}
                  options={{ fillOpacity: 0, strokeColor: "#ff2d55", strokeWeight: 3 }}
                  onClick={handleShapeClick}
                />
              ))}
            {phase !== "idle" &&
              points.map((p, i) => (
                <Marker
                  key={`pt-${i}`}
                  position={p}
                  icon={vertexIcon()}
                  title={`Point ${i + 1} - drag to move, click to delete`}
                  draggable
                  onDragEnd={(e) => movePoint(i, e.latLng)}
                  onClick={() => deletePoint(i)}
                />
              ))}
          </GoogleMap>
        </div>

        <div className="map-side-panel">
          {phase === "idle" && !showFloorPicker && (
            <>
              <h3>Add to map</h3>
              <button onClick={() => startDrawing("wall")}>+ Wall</button>
              <button onClick={() => startDrawing("roof")}>+ Roof</button>
              <button onClick={() => setShowFloorPicker(true)}>+ Floor</button>
            </>
          )}

          {showFloorPicker && phase === "idle" && (
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

          {phase === "drawing" && (
            <>
              <h3>Drawing {isWall ? "a wall" : `a ${shapeKind}`}</h3>
              <p className="muted">
                Click the map to add points. Click the line to insert a point along it, drag a point to move it, or
                click a point to delete it.
                {!isWall && " Need at least 3 points."}
              </p>
              <p>{points.length} point(s) placed.</p>
              <div className="map-attribute-actions">
                <button onClick={finishDrawing} disabled={points.length < minPoints}>
                  Finish
                </button>
                <button className="danger" onClick={cancelShape}>
                  Cancel
                </button>
              </div>
            </>
          )}

          {phase === "reviewing" && (
            <p className="muted">
              Still adjustable on the map - drag a point, click the line to add one, or click a point to remove it.
              The measurement below updates live.
            </p>
          )}
          {phase === "reviewing" && (
            <AttributeForm
              shape={{ type: shapeKind, measurement, perimeter, copiedLocation }}
              ageBands={ageBands}
              onAccept={handleAccept}
              onCancel={handleDiscard}
              error={acceptError}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function AttributeForm({ shape, ageBands, onAccept, onCancel, error }) {
  const isWall = shape.type === "wall";
  const isRoof = shape.type === "roof";
  const isFloor = shape.type === "floor";
  const fieldErrors = error?.fieldErrors || {};
  const errorStyle = (key) =>
    fieldErrors[key] ? { borderColor: "var(--danger)", borderWidth: "2px", background: "#fdf0ee" } : undefined;
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
    ground_type: "sand_or_gravel",
    thickness_m: 0.1,
    k_value: 1.63,
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
      }
      // floor U-value is calculated from area, perimeter, thickness and k-value instead of an age band
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
        perimeter: shape.perimeter,
        u_value: parseFloat(fields.u_value) || 0,
      });
    } else {
      onAccept({
        location: fields.location,
        reference: fields.reference,
        age_band_id: fields.age_band_id || null,
        area: shape.measurement,
        perimeter: shape.perimeter,
        ground_type: fields.ground_type,
        thickness_m: parseFloat(fields.thickness_m) || 0.1,
        k_value: parseFloat(fields.k_value) || 1.63,
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
              <input type="number" step="any" value={fields.height} onChange={set("height")} style={errorStyle("height")} title={fieldErrors.height} />
            </label>
            <label>
              % windows (0-1)
              <input type="number" step="any" value={fields.window_pct} onChange={set("window_pct")} style={errorStyle("window_pct")} title={fieldErrors.window_pct} />
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
              <input type="number" step="any" value={fields.wall_u_value} onChange={set("wall_u_value")} style={errorStyle("wall_u_value")} title={fieldErrors.wall_u_value} />
            </label>
            <label>
              Window U
              <input type="number" step="any" value={fields.window_u_value} onChange={set("window_u_value")} style={errorStyle("window_u_value")} title={fieldErrors.window_u_value} />
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
              <input type="number" step="any" value={fields.u_value} onChange={set("u_value")} style={errorStyle("u_value")} title={fieldErrors.u_value} />
            </label>
            <p className="muted">Perimeter measured from the map: {shape.perimeter.toFixed(2)} m</p>
          </>
        ) : (
          <>
            <label>
              Ground type
              <select value={fields.ground_type} onChange={set("ground_type")}>
                <option value="clay_soil">Clay soil</option>
                <option value="sand_or_gravel">Sand or gravel</option>
                <option value="homogeneous_rock">Homogeneous rock</option>
              </select>
            </label>
            <label>
              Floor thickness (m)
              <input type="number" step="any" value={fields.thickness_m} onChange={set("thickness_m")} style={errorStyle("thickness_m")} title={fieldErrors.thickness_m} />
            </label>
            <label>
              Floor k-value (W/mK)
              <input type="number" step="any" value={fields.k_value} onChange={set("k_value")} style={errorStyle("k_value")} title={fieldErrors.k_value} />
            </label>
            <p className="muted">
              Perimeter measured from the map: {shape.perimeter.toFixed(2)} m. U-value will be calculated
              automatically from the area, perimeter, ground type, thickness and k-value.
            </p>
          </>
        )}
      </div>

      {error && <p className="error">{error.message}</p>}

      <div className="map-attribute-actions">
        <button type="submit">Accept &amp; save</button>
        <button type="button" className="danger" onClick={onCancel}>
          Discard
        </button>
      </div>
    </form>
  );
}
