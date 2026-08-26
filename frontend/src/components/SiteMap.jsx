import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Polygon, Polyline, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet-draw";
import { api } from "../api";

const DEFAULT_CENTER = [51.5074, -0.1278]; // London - used only until the project's address geocodes
const ESRI_SATELLITE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const ESRI_ATTRIBUTION =
  "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community";

const LAYER_COLORS = { wall: "#e8a543", roof: "#3388ff", floor: "#2ecc71" };

function polylineLengthMetres(latlngs) {
  let total = 0;
  for (let i = 1; i < latlngs.length; i++) total += latlngs[i - 1].distanceTo(latlngs[i]);
  return total;
}

// Equirectangular-projection shoelace formula. Flattening error is
// negligible at building scale (tens to low hundreds of metres across).
function polygonAreaSqMetres(latlngs) {
  if (latlngs.length < 3) return 0;
  const R = 6378137;
  const toRad = (d) => (d * Math.PI) / 180;
  const lat0 = toRad(latlngs[0].lat);
  const pts = latlngs.map((p) => [R * toRad(p.lng) * Math.cos(lat0), R * toRad(p.lat)]);
  let area = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % pts.length];
    area += x1 * y2 - x2 * y1;
  }
  return Math.abs(area / 2);
}

function DrawTools({ onShapeDrawn }) {
  const map = useMap();

  useEffect(() => {
    const drawControl = new L.Control.Draw({
      position: "topleft",
      draw: {
        polygon: { allowIntersection: false, showArea: false, shapeOptions: { color: LAYER_COLORS.roof } },
        polyline: { shapeOptions: { color: LAYER_COLORS.wall, weight: 4 } },
        rectangle: false,
        circle: false,
        circlemarker: false,
        marker: false,
      },
      edit: false,
    });
    map.addControl(drawControl);

    const handleCreated = (e) => {
      const latlngs = e.layerType === "polygon" ? e.layer.getLatLngs()[0] : e.layer.getLatLngs();
      onShapeDrawn({ layerType: e.layerType, latlngs });
    };
    map.on(L.Draw.Event.CREATED, handleCreated);

    return () => {
      map.off(L.Draw.Event.CREATED, handleCreated);
      map.removeControl(drawControl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map]);

  return null;
}

function Recenter({ center }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center[0], center[1]]);
  return null;
}

export default function SiteMap({ project, room, ageBands, elementApi, refreshAll }) {
  const [center, setCenter] = useState(DEFAULT_CENTER);
  const [geoError, setGeoError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [pendingShape, setPendingShape] = useState(null);
  const [visible, setVisible] = useState({ wall: true, roof: true, floor: true });

  const geocodeAndCenter = (address, { persist } = {}) => {
    setGeoError(null);
    return api
      .geocode(address)
      .then((res) => {
        setCenter([res.latitude, res.longitude]);
        if (persist) api.updateProject(project.id, { latitude: res.latitude, longitude: res.longitude });
      })
      .catch((e) => setGeoError(e.message));
  };

  useEffect(() => {
    if (project.latitude != null && project.longitude != null) {
      setCenter([project.latitude, project.longitude]);
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

  const handleShapeDrawn = (shape) => {
    const measurement =
      shape.layerType === "polyline" ? polylineLengthMetres(shape.latlngs) : polygonAreaSqMetres(shape.latlngs);
    setPendingShape({ ...shape, measurement });
  };

  const handleAccept = async (elementType, fields) => {
    const geometry = pendingShape.latlngs.map((p) => [p.lat, p.lng]);
    const type = elementType === "wall" ? "walls" : elementType === "roof" ? "roofs" : "floors";
    await elementApi(type).onAdd({ ...fields, geometry });
    setPendingShape(null);
    refreshAll();
  };

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

      <div className="map-wrap">
        <MapContainer center={center} zoom={19} maxZoom={21} style={{ height: "600px", width: "100%" }}>
          <TileLayer url={ESRI_SATELLITE_URL} attribution={ESRI_ATTRIBUTION} maxZoom={21} maxNativeZoom={19} />
          <Recenter center={center} />
          <DrawTools onShapeDrawn={handleShapeDrawn} />

          {visible.wall &&
            room.walls
              .filter((w) => w.geometry)
              .map((w) => (
                <Polyline key={`wall-${w.id}`} positions={w.geometry} color={LAYER_COLORS.wall} weight={4}>
                  <Popup>
                    <strong>{w.location || "Wall"}</strong>
                    <br />
                    Width: {w.width?.toFixed(2)} m
                    <br />
                    Wall U: {w.wall_u_value}
                  </Popup>
                </Polyline>
              ))}

          {visible.roof &&
            room.roofs
              .filter((r) => r.geometry)
              .map((r) => (
                <Polygon key={`roof-${r.id}`} positions={r.geometry} color={LAYER_COLORS.roof}>
                  <Popup>
                    <strong>{r.location || "Roof"}</strong>
                    <br />
                    Area: {r.area?.toFixed(2)} m2
                    <br />
                    U value: {r.u_value}
                  </Popup>
                </Polygon>
              ))}

          {visible.floor &&
            room.floors
              .filter((f) => f.geometry)
              .map((f) => (
                <Polygon key={`floor-${f.id}`} positions={f.geometry} color={LAYER_COLORS.floor}>
                  <Popup>
                    <strong>{f.location || "Floor"}</strong>
                    <br />
                    Area: {f.area?.toFixed(2)} m2
                    <br />
                    U value: {f.u_value}
                  </Popup>
                </Polygon>
              ))}

          {pendingShape &&
            (pendingShape.layerType === "polyline" ? (
              <Polyline positions={pendingShape.latlngs} color="#ff2d55" weight={5} dashArray="6 6" />
            ) : (
              <Polygon positions={pendingShape.latlngs} color="#ff2d55" dashArray="6 6" />
            ))}
        </MapContainer>
      </div>

      <p className="muted">
        Use the draw tools (top-left of the map) to trace a wall (line) or a roof/floor outline (polygon). Once
        you finish a shape, a form appears below to confirm what it is and fill in the rest of its attributes.
      </p>

      {pendingShape && (
        <AttributeForm shape={pendingShape} ageBands={ageBands} onAccept={handleAccept} onCancel={() => setPendingShape(null)} />
      )}
    </div>
  );
}

function AttributeForm({ shape, ageBands, onAccept, onCancel }) {
  const isLine = shape.layerType === "polyline";
  const [elementType, setElementType] = useState(isLine ? "wall" : "roof");
  const [fields, setFields] = useState({
    location: "",
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
      if (elementType === "wall") {
        if (band.wall_u != null) next.wall_u_value = band.wall_u;
        const windowU = prev.window_frame_type === "Metal" ? band.window_metal_u : band.window_other_u;
        if (windowU != null) next.window_u_value = windowU;
      } else if (elementType === "roof" && band[prev.roof_type === "Flat" ? "flat_roof_u" : "pitched_roof_u"] != null) {
        next.u_value = band[prev.roof_type === "Flat" ? "flat_roof_u" : "pitched_roof_u"];
      } else if (elementType === "floor" && band.floor_u != null) {
        next.u_value = band.floor_u;
      }
      return next;
    });
  };

  const measurementLabel = isLine ? `${shape.measurement.toFixed(2)} m (length)` : `${shape.measurement.toFixed(2)} m² (area)`;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (elementType === "wall") {
      onAccept("wall", {
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
    } else if (elementType === "roof") {
      onAccept("roof", {
        location: fields.location,
        reference: fields.reference,
        age_band_id: fields.age_band_id || null,
        roof_type: fields.roof_type,
        has_loft: fields.has_loft,
        area: shape.measurement,
        u_value: parseFloat(fields.u_value) || 0,
      });
    } else {
      onAccept("floor", {
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

      {!isLine && (
        <label>
          This is a
          <select value={elementType} onChange={(e) => setElementType(e.target.value)}>
            <option value="roof">Roof</option>
            <option value="floor">Floor</option>
          </select>
        </label>
      )}

      <div className="map-attribute-grid">
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

        {elementType === "wall" && (
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
        )}

        {elementType === "roof" && (
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
        )}

        {elementType === "floor" && (
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
