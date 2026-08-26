import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import EditableTable from "../components/EditableTable";

const TABS = ["Settings", "Walls", "Roofs", "Roof Lights", "Floors", "Doors", "Zones", "Results"];

function fmt(n, dp = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return Number(n).toFixed(dp);
}

export default function PlantRoomPage() {
  const { roomId } = useParams();
  const [room, setRoom] = useState(null);
  const [measures, setMeasures] = useState([]);
  const [ageBands, setAgeBands] = useState([]);
  const [results, setResults] = useState(null);
  const [tab, setTab] = useState("Settings");
  const [error, setError] = useState(null);
  const [autoProposeMsg, setAutoProposeMsg] = useState(null);

  const load = async () => {
    try {
      const [r, m, a] = await Promise.all([api.getPlantRoom(roomId), api.listMeasures(), api.listAgeBands()]);
      setRoom(r);
      setMeasures(m);
      setAgeBands(a);
    } catch (e) {
      setError(e.message);
    }
  };

  const loadResults = async () => {
    try {
      setResults(await api.getPlantRoomResults(roomId));
    } catch (e) {
      setError(e.message);
    }
  };

  useEffect(() => {
    load();
    loadResults();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId]);

  const refreshAll = async () => {
    await load();
    await loadResults();
  };

  const runAutoPropose = async () => {
    const res = await api.autoPropose(roomId);
    setAutoProposeMsg(
      res.updated_count === 0
        ? "No changes - every element's U-value already meets the standard measures, or already has a proposed value set."
        : `Applied ${res.updated_count} proposed upgrade(s). Review them in each tab (proposed U-value / measure columns) - clear a field to discard a suggestion, or edit the value to override it.`
    );
    refreshAll();
  };

  const measureOptions = (applies_to) =>
    measures
      .filter((m) => m.applies_to.length === 0 || m.applies_to.includes(applies_to))
      .map((m) => ({ value: m.id, label: m.name }));

  const ageBandOptions = ageBands.map((a) => ({ value: a.id, label: a.period_label }));
  const findAgeBand = (id) => ageBands.find((a) => String(a.id) === String(id));
  const findMeasure = (id) => measures.find((m) => String(m.id) === String(id));

  // Derives U-value(s) from the selected age band + the row's current type fields
  // (roof_type / door_type / window_frame_type), pre-filling the "existing" U-value
  // while leaving it fully editable afterwards.
  const ageBandDerivers = {
    wall: (row) => {
      const band = findAgeBand(row.age_band_id);
      if (!band) return {};
      const windowU = row.window_frame_type === "Metal" ? band.window_metal_u : band.window_other_u;
      return {
        ...(band.wall_u != null ? { wall_u_value: band.wall_u } : {}),
        ...(windowU != null ? { window_u_value: windowU } : {}),
      };
    },
    roof: (row) => {
      const band = findAgeBand(row.age_band_id);
      if (!band) return {};
      const u = row.roof_type === "Flat" ? band.flat_roof_u : band.pitched_roof_u;
      return u != null ? { u_value: u } : {};
    },
    floor: (row) => {
      const band = findAgeBand(row.age_band_id);
      if (!band || band.floor_u == null) return {};
      return { u_value: band.floor_u };
    },
    door: (row) => {
      const band = findAgeBand(row.age_band_id);
      if (!band) return {};
      const u = { Pedestrian: band.pedestrian_door_u, Vehicle: band.vehicle_door_u, Entrance: band.entrance_door_u }[row.door_type];
      return u != null ? { u_value: u } : {};
    },
  };

  // Auto-fills the proposed U-value from a chosen measure's typical U-value.
  const measureDeriver = (proposedField) => (measureId) => {
    const measure = findMeasure(measureId);
    if (!measure || measure.typical_u_value == null) return {};
    return { [proposedField]: measure.typical_u_value };
  };

  const elementApi = (type) => ({
    onUpdate: async (id, fields) => {
      await api.updateElement(type, id, fields);
      refreshAll();
    },
    onDelete: async (id) => {
      await api.deleteElement(type, id);
      refreshAll();
    },
    onAdd: async (fields) => {
      await api.createElement(roomId, type, fields);
      refreshAll();
    },
  });

  if (!room) return <div className="page">{error || "Loading..."}</div>;

  return (
    <div className="page">
      <p>
        <Link to={`/projects/${room.project_id}`}>&larr; Back to project</Link>
      </p>
      <h1>{room.name}</h1>
      {error && <p className="error">{error}</p>}

      <div className="auto-propose-bar">
        <button onClick={runAutoPropose}>Auto-generate proposed building</button>
        <span className="muted">
          Fills in proposed U-values/measures for elements that don't meet the standard measures yet (walls: cavity
          insulation, windows: double glazing, roofs: loft/roof insulation). Never overwrites a value you've already
          set - accept it as-is, edit it, or clear it to discard.
        </span>
      </div>
      {autoProposeMsg && <p className="notice">{autoProposeMsg}</p>}

      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={t === tab ? "tab active" : "tab"} onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {tab === "Settings" && <SettingsTab room={room} onSave={refreshAll} />}

      {tab === "Walls" && (
        <div className="tab-panel">
          <p className="muted">
            Window % of a wall row is treated as a separate glazed element sharing that wall's height/width.
            Pick an age band to auto-fill the existing U-values; pick a measure under "Proposed" to auto-fill the
            proposed U-value - both stay editable afterwards.
          </p>
          <div className="table-scroll">
            <EditableTable
              columnGroups={[
                { label: "Element", count: 3, className: "group-element" },
                { label: "Geometry", count: 4, className: "group-geometry" },
                { label: "Existing building", count: 2, className: "group-existing" },
                { label: "Proposed / improvement", count: 4, className: "group-proposed" },
                { label: "", count: 1 },
              ]}
              columns={[
                { key: "location", label: "Location", type: "text", group: "group-element" },
                { key: "age_band_id", label: "Age band", type: "select", options: ageBandOptions, group: "group-element", onSelect: (v, row) => ageBandDerivers.wall(row) },
                { key: "reference", label: "Reference", type: "text", group: "group-element" },
                { key: "height", label: "Height (m)", type: "number", width: "70px", group: "group-geometry" },
                { key: "width", label: "Width (m)", type: "number", width: "70px", group: "group-geometry" },
                { key: "window_pct", label: "% windows (0-1)", type: "number", width: "80px", group: "group-geometry" },
                { key: "window_frame_type", label: "Window frame", type: "select", options: [{ value: "Other", label: "Other" }, { value: "Metal", label: "Metal" }], group: "group-geometry", onSelect: (v, row) => ageBandDerivers.wall(row) },
                { key: "wall_u_value", label: "Wall U", type: "number", width: "70px", group: "group-existing" },
                { key: "window_u_value", label: "Window U", type: "number", width: "70px", group: "group-existing" },
                { key: "wall_measure_id", label: "Wall measure", type: "select", options: measureOptions("wall"), group: "group-proposed", onSelect: measureDeriver("proposed_wall_u_value") },
                { key: "proposed_wall_u_value", label: "Proposed wall U", type: "number", width: "80px", group: "group-proposed" },
                { key: "window_measure_id", label: "Window measure", type: "select", options: measureOptions("window"), group: "group-proposed", onSelect: measureDeriver("proposed_window_u_value") },
                { key: "proposed_window_u_value", label: "Proposed window U", type: "number", width: "80px", group: "group-proposed" },
                { key: "notes", label: "Notes", type: "text" },
              ]}
              rows={room.walls}
              newRowDefaults={{ location: "", reference: "", height: 0, width: 0, window_pct: 0, window_frame_type: "Other", wall_u_value: 0, window_u_value: 0 }}
              {...elementApi("walls")}
            />
          </div>
        </div>
      )}

      {tab === "Roofs" && (
        <div className="tab-panel">
          <p className="muted">Tip: tick "Has loft?" so auto-generate proposes loft insulation instead of roof insulation.</p>
          <div className="table-scroll">
            <EditableTable
              columnGroups={[
                { label: "Element", count: 3, className: "group-element" },
                { label: "Geometry", count: 3, className: "group-geometry" },
                { label: "Existing building", count: 1, className: "group-existing" },
                { label: "Proposed / improvement", count: 2, className: "group-proposed" },
                { label: "", count: 1 },
              ]}
              columns={[
                { key: "location", label: "Location", type: "text", group: "group-element" },
                { key: "age_band_id", label: "Age band", type: "select", options: ageBandOptions, group: "group-element", onSelect: (v, row) => ageBandDerivers.roof(row) },
                { key: "reference", label: "Reference", type: "text", group: "group-element" },
                {
                  key: "roof_type",
                  label: "Type",
                  type: "select",
                  options: [{ value: "Pitched", label: "Pitched" }, { value: "Flat", label: "Flat" }],
                  group: "group-geometry",
                  onSelect: (v, row) => ageBandDerivers.roof(row),
                },
                { key: "has_loft", label: "Has loft?", type: "checkbox", group: "group-geometry" },
                { key: "area", label: "Area (m2)", type: "number", width: "80px", group: "group-geometry" },
                { key: "u_value", label: "U value", type: "number", width: "70px", group: "group-existing" },
                { key: "measure_id", label: "Measure", type: "select", options: measureOptions("roof"), group: "group-proposed", onSelect: measureDeriver("proposed_u_value") },
                { key: "proposed_u_value", label: "Proposed U", type: "number", width: "80px", group: "group-proposed" },
                { key: "notes", label: "Notes", type: "text" },
              ]}
              rows={room.roofs}
              newRowDefaults={{ location: "", reference: "", roof_type: "Pitched", has_loft: false, area: 0, u_value: 0 }}
              {...elementApi("roofs")}
            />
          </div>
        </div>
      )}

      {tab === "Roof Lights" && (
        <div className="tab-panel">
          <div className="table-scroll">
            <EditableTable
              columns={[
                { key: "location", label: "Location", type: "text" },
                { key: "construction", label: "Construction", type: "text" },
                { key: "reference", label: "Reference", type: "text" },
                { key: "height", label: "Height (m)", type: "number", width: "70px" },
                { key: "width", label: "Width (m)", type: "number", width: "70px" },
                { key: "qty", label: "Qty", type: "number", width: "50px" },
                { key: "u_value", label: "U value", type: "number", width: "70px" },
                { key: "proposed_u_value", label: "Proposed U", type: "number", width: "80px" },
                { key: "measure_id", label: "Measure", type: "select", options: measureOptions("rooflight") },
                { key: "notes", label: "Notes", type: "text" },
              ]}
              rows={room.rooflights}
              newRowDefaults={{ location: "", construction: "", reference: "", height: 0, width: 0, qty: 1, u_value: 0 }}
              {...elementApi("rooflights")}
            />
          </div>
        </div>
      )}

      {tab === "Floors" && (
        <div className="tab-panel">
          <p className="muted">
            Floor insulation is generally not recommended (expensive, disruptive, poor cost-effectiveness) and is
            excluded from auto-generate - use the U-Value Floor Calculator on the Reference Data page for the
            existing U-value, or pick an age band for a rough default.
          </p>
          <div className="table-scroll">
            <EditableTable
              columnGroups={[
                { label: "Element", count: 3, className: "group-element" },
                { label: "Geometry", count: 1, className: "group-geometry" },
                { label: "Existing building", count: 1, className: "group-existing" },
                { label: "Proposed", count: 1, className: "group-proposed" },
                { label: "", count: 1 },
              ]}
              columns={[
                { key: "location", label: "Location", type: "text", group: "group-element" },
                { key: "age_band_id", label: "Age band", type: "select", options: ageBandOptions, group: "group-element", onSelect: (v, row) => ageBandDerivers.floor(row) },
                { key: "reference", label: "Reference", type: "text", group: "group-element" },
                { key: "area", label: "Area (m2)", type: "number", width: "80px", group: "group-geometry" },
                { key: "u_value", label: "U value", type: "number", width: "70px", group: "group-existing" },
                { key: "proposed_u_value", label: "Proposed U", type: "number", width: "80px", group: "group-proposed" },
                { key: "notes", label: "Notes", type: "text" },
              ]}
              rows={room.floors}
              newRowDefaults={{ location: "", reference: "", area: 0, u_value: 0 }}
              {...elementApi("floors")}
            />
          </div>
        </div>
      )}

      {tab === "Doors" && (
        <div className="tab-panel">
          <div className="table-scroll">
            <EditableTable
              columnGroups={[
                { label: "Element", count: 3, className: "group-element" },
                { label: "Geometry", count: 4, className: "group-geometry" },
                { label: "Existing building", count: 1, className: "group-existing" },
                { label: "Proposed / improvement", count: 2, className: "group-proposed" },
                { label: "", count: 1 },
              ]}
              columns={[
                { key: "location", label: "Location", type: "text", group: "group-element" },
                { key: "age_band_id", label: "Age band", type: "select", options: ageBandOptions, group: "group-element", onSelect: (v, row) => ageBandDerivers.door(row) },
                { key: "reference", label: "Reference", type: "text", group: "group-element" },
                {
                  key: "door_type",
                  label: "Type",
                  type: "select",
                  options: [
                    { value: "Pedestrian", label: "Pedestrian" },
                    { value: "Vehicle", label: "Vehicle" },
                    { value: "Entrance", label: "Entrance" },
                  ],
                  group: "group-geometry",
                  onSelect: (v, row) => ageBandDerivers.door(row),
                },
                { key: "height", label: "Height (m)", type: "number", width: "70px", group: "group-geometry" },
                { key: "width", label: "Width (m)", type: "number", width: "70px", group: "group-geometry" },
                { key: "qty", label: "Qty", type: "number", width: "50px", group: "group-geometry" },
                { key: "u_value", label: "U value", type: "number", width: "70px", group: "group-existing" },
                { key: "measure_id", label: "Measure", type: "select", options: measureOptions("door"), group: "group-proposed", onSelect: measureDeriver("proposed_u_value") },
                { key: "proposed_u_value", label: "Proposed U", type: "number", width: "80px", group: "group-proposed" },
                { key: "notes", label: "Notes", type: "text" },
              ]}
              rows={room.doors}
              newRowDefaults={{ location: "", reference: "", door_type: "Pedestrian", height: 0, width: 0, qty: 1, u_value: 0 }}
              {...elementApi("doors")}
            />
          </div>
        </div>
      )}

      {tab === "Zones" && (
        <div className="tab-panel">
          <p className="muted">
            Zones drive the volume calculation (Volume = &Sigma; area &times; height per zone). Air changes per hour
            (ACH) is set on the Settings tab.
          </p>
          <div className="table-scroll">
            <EditableTable
              columns={[
                { key: "name", label: "Zone name", type: "text" },
                { key: "area_m2", label: "Area (m2)", type: "number", width: "90px" },
                { key: "height_m", label: "Height (m)", type: "number", width: "90px" },
                { key: "volume_m3", label: "Volume (m3)", type: "readonly", format: (v) => fmt(v) },
              ]}
              rows={room.zones}
              newRowDefaults={{ name: "", area_m2: 0, height_m: 0 }}
              {...elementApi("zones")}
            />
          </div>
          <p>
            <strong>Total volume:</strong> {fmt(room.zones.reduce((s, z) => s + (z.area_m2 || 0) * (z.height_m || 0), 0))} m3
          </p>
        </div>
      )}

      {tab === "Results" && <ResultsTab results={results} onRefresh={loadResults} />}
    </div>
  );
}

function SettingsTab({ room, onSave }) {
  const [form, setForm] = useState(room);
  useEffect(() => setForm(room), [room]);

  const set = (key) => (e) => {
    const val = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((prev) => ({ ...prev, [key]: val }));
  };

  const commit = async (overrides) => {
    const next = overrides ? { ...form, ...overrides } : form;
    await api.updatePlantRoom(room.id, next);
    onSave();
  };

  const setAndCommitCheckbox = (key) => (e) => {
    const val = e.target.checked;
    setForm((prev) => ({ ...prev, [key]: val }));
    commit({ [key]: val });
  };

  return (
    <div className="tab-panel settings-grid">
      <fieldset>
        <legend>Energy usage</legend>
        <label>
          Fuel type
          <select
            value={form.fuel_type || ""}
            onChange={(e) => {
              setForm((prev) => ({ ...prev, fuel_type: e.target.value }));
              commit({ fuel_type: e.target.value });
            }}
          >
            <option>Natural gas</option>
            <option>Electricity</option>
            <option>Gas oil</option>
          </select>
        </label>
        <label>
          Annual fuel usage (kWh/yr)
          <input type="number" step="any" value={form.annual_fuel_usage_kwh ?? ""} onChange={set("annual_fuel_usage_kwh")} onBlur={() => commit()} />
        </label>
        <label>
          Unit rate override (£/kWh, optional)
          <input type="number" step="any" value={form.unit_rate_per_kwh ?? ""} onChange={set("unit_rate_per_kwh")} onBlur={() => commit()} />
        </label>
        <label>
          Boiler efficiency (0-1)
          <input type="number" step="any" value={form.boiler_efficiency ?? ""} onChange={set("boiler_efficiency")} onBlur={() => commit()} />
        </label>
        <label className="checkbox-label">
          <input type="checkbox" checked={!!form.uses_gas_kitchen} onChange={setAndCommitCheckbox("uses_gas_kitchen")} />
          Kitchen uses gas
        </label>
        <label>
          Assumed kitchen gas usage (% of annual, 0-1)
          <input type="number" step="any" value={form.kitchen_gas_pct ?? ""} onChange={set("kitchen_gas_pct")} onBlur={() => commit()} />
        </label>
      </fieldset>

      <fieldset>
        <legend>Domestic hot water (DHW)</legend>
        <label>
          Method
          <select
            value={form.dhw_method || "manual"}
            onChange={(e) => {
              setForm((prev) => ({ ...prev, dhw_method: e.target.value }));
              commit({ dhw_method: e.target.value });
            }}
          >
            <option value="manual">Manual entry</option>
            <option value="summer_baseload">Summer baseload method</option>
            <option value="tank_size">Tank size method</option>
          </select>
        </label>
        {form.dhw_method === "manual" && (
          <label>
            DHW annual usage (kWh/yr)
            <input type="number" step="any" value={form.dhw_manual_kwh ?? ""} onChange={set("dhw_manual_kwh")} onBlur={() => commit()} />
          </label>
        )}
        {form.dhw_method === "summer_baseload" && (
          <label>
            Summer baseload (kWh/month)
            <input type="number" step="any" value={form.dhw_summer_baseload_kwh_month ?? ""} onChange={set("dhw_summer_baseload_kwh_month")} onBlur={() => commit()} />
          </label>
        )}
        {form.dhw_method === "tank_size" && (
          <>
            <label>
              Tank volume (litres)
              <input type="number" step="any" value={form.dhw_tank_volume_litres ?? ""} onChange={set("dhw_tank_volume_litres")} onBlur={() => commit()} />
            </label>
            <label>
              Temperature rise (&deg;C)
              <input type="number" step="any" value={form.dhw_tank_temp_rise_c ?? ""} onChange={set("dhw_tank_temp_rise_c")} onBlur={() => commit()} />
            </label>
            <label>
              Reheat cycles per day
              <input type="number" step="any" value={form.dhw_tank_cycles_per_day ?? ""} onChange={set("dhw_tank_cycles_per_day")} onBlur={() => commit()} />
            </label>
            <label>
              DHW efficiency (0-1)
              <input type="number" step="any" value={form.dhw_efficiency ?? ""} onChange={set("dhw_efficiency")} onBlur={() => commit()} />
            </label>
          </>
        )}
      </fieldset>

      <fieldset>
        <legend>Ventilation &amp; design conditions</legend>
        <label>
          Air changes per hour (ACH)
          <input type="number" step="any" value={form.ach ?? ""} onChange={set("ach")} onBlur={() => commit()} />
        </label>
        <label>
          Internal setpoint (&deg;C)
          <input type="number" step="any" value={form.internal_setpoint_c ?? ""} onChange={set("internal_setpoint_c")} onBlur={() => commit()} />
        </label>
        <label>
          External design temperature (&deg;C)
          <input type="number" step="any" value={form.external_design_temp_c ?? ""} onChange={set("external_design_temp_c")} onBlur={() => commit()} />
        </label>
      </fieldset>

      <fieldset>
        <legend>Notes</legend>
        <textarea rows={4} value={form.notes || ""} onChange={set("notes")} onBlur={() => commit()} />
      </fieldset>
    </div>
  );
}

function ResultsTab({ results, onRefresh }) {
  if (!results) return <div className="tab-panel">Loading results...</div>;

  const catLabels = { wall: "Wall", window: "Windows", roof: "Roof", rooflight: "Roof Lights", floor: "Floor", door: "Doors" };

  return (
    <div className="tab-panel">
      <button onClick={onRefresh}>Refresh results</button>

      <h3>Category summary</h3>
      <div className="table-scroll">
        <table className="list-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Existing area (m2)</th>
              <th>Existing avg U</th>
              <th>Existing UA (W/K)</th>
              <th>Improved avg U</th>
              <th>Improved UA (W/K)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(results.categories).map(([key, c]) => (
              <tr key={key}>
                <td>{catLabels[key] || key}</td>
                <td>{fmt(c.existing.area)}</td>
                <td>{fmt(c.existing.avg_u, 3)}</td>
                <td>{fmt(c.existing.ua_for_heat_loss)}</td>
                <td>{fmt(c.improved.avg_u, 3)}</td>
                <td>{fmt(c.improved.ua_for_heat_loss)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3>Heat loss summary</h3>
      <table className="list-table">
        <tbody>
          <tr>
            <td>Volume</td>
            <td>{fmt(results.volume_m3)} m3</td>
          </tr>
          <tr>
            <td>Ventilation loss</td>
            <td>{fmt(results.ventilation_loss_w_per_k)} W/K</td>
          </tr>
          <tr>
            <td>Thermal capacity &Sigma;UA (existing / improved)</td>
            <td>
              {fmt(results.thermal_capacity_ua_w_per_k.existing)} / {fmt(results.thermal_capacity_ua_w_per_k.improved)} W/K
            </td>
          </tr>
          <tr>
            <td>Heat loss coefficient (existing / improved)</td>
            <td>
              {fmt(results.heat_loss_coefficient_w_per_k.existing)} / {fmt(results.heat_loss_coefficient_w_per_k.improved)} W/K
            </td>
          </tr>
          <tr>
            <td>
              <strong>Peak heat loss (existing / improved)</strong>
            </td>
            <td>
              <strong>
                {fmt(results.peak_heat_loss_kw.existing)} / {fmt(results.peak_heat_loss_kw.improved)} kW
              </strong>
            </td>
          </tr>
        </tbody>
      </table>

      <h3>Energy usage</h3>
      <table className="list-table">
        <tbody>
          <tr>
            <td>Annual fuel usage</td>
            <td>{fmt(results.energy_usage.annual_fuel_usage_kwh, 0)} kWh</td>
          </tr>
          <tr>
            <td>DHW usage</td>
            <td>{fmt(results.energy_usage.dhw_kwh, 0)} kWh</td>
          </tr>
          <tr>
            <td>Kitchen usage</td>
            <td>{fmt(results.energy_usage.kitchen_kwh, 0)} kWh</td>
          </tr>
          <tr>
            <td>Space heating usage</td>
            <td>{fmt(results.energy_usage.space_heating_kwh, 0)} kWh</td>
          </tr>
        </tbody>
      </table>

      <h3>Fabric improvement measures applied here</h3>
      {results.measure_results.length === 0 && <p className="muted">No proposed U-values with a measure assigned yet.</p>}
      {results.measure_results.length > 0 && (
        <table className="list-table">
          <thead>
            <tr>
              <th>Area of improvement (m2)</th>
              <th>Heat loss reduction (W/K)</th>
              <th>% of total heat loss</th>
              <th>Thermal energy saving (kWh/yr)</th>
              <th>CO2 saving (t/yr)</th>
              <th>Cost saving (£/yr)</th>
            </tr>
          </thead>
          <tbody>
            {results.measure_results.map((m, i) => (
              <tr key={i}>
                <td>{fmt(m.area_of_improvement_m2)}</td>
                <td>{fmt(m.heat_loss_reduction_w_per_k)}</td>
                <td>{fmt(m.pct_heat_loss_reduction * 100, 1)}%</td>
                <td>{fmt(m.thermal_energy_saving_kwh, 0)}</td>
                <td>{fmt(m.co2_saving_tonnes_per_yr, 3)}</td>
                <td>&pound;{fmt(m.cost_saving_gbp_per_yr, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="muted">Full cost / payback figures (which need the measure's £/m2 and lifetime) are on the project Overview page.</p>
    </div>
  );
}
