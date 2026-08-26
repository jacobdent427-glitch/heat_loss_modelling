import { useEffect, useState } from "react";
import { api } from "../api";
import EditableTable from "../components/EditableTable";

const APPLIES_TO_OPTIONS = ["wall", "window", "roof", "rooflight", "floor", "door"];

export default function ReferenceDataPage() {
  const [measures, setMeasures] = useState([]);
  const [factors, setFactors] = useState([]);
  const [ageBands, setAgeBands] = useState([]);
  const [error, setError] = useState(null);

  const load = () =>
    Promise.all([api.listMeasures(), api.listEmissionFactors(), api.listAgeBands()])
      .then(([m, f, a]) => {
        setMeasures(m);
        setFactors(f);
        setAgeBands(a);
      })
      .catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page">
      <h1>Reference data</h1>
      {error && <p className="error">{error}</p>}

      <h2>Building fabric improvement measures</h2>
      <p className="muted">
        Floor insulation is deliberately not listed - it is generally not recommended (expensive, disruptive, poor
        cost-effectiveness). Add custom/bespoke measures (e.g. a specific curtain-walling replacement) below as
        needed.
      </p>
      <div className="table-scroll">
        <EditableTable
          columns={[
            { key: "name", label: "Name", type: "text" },
            {
              key: "applies_to",
              label: "Applies to (comma list)",
              type: "text",
            },
            { key: "lifetime_years", label: "Lifetime (yrs)", type: "number", width: "70px" },
            { key: "cost_per_m2", label: "Cost (£/m2)", type: "number", width: "80px" },
            { key: "typical_u_value", label: "Typical U", type: "number", width: "70px" },
            { key: "cost_guidance", label: "Cost guidance", type: "text" },
            { key: "u_value_guidance", label: "U-value guidance", type: "text" },
          ]}
          rows={measures.map((m) => ({ ...m, applies_to: m.applies_to.join(",") }))}
          newRowDefaults={{ name: "", applies_to: APPLIES_TO_OPTIONS[0], lifetime_years: 0, cost_per_m2: 0 }}
          onUpdate={async (id, fields) => {
            if ("applies_to" in fields) fields.applies_to = (fields.applies_to || "").split(",").map((s) => s.trim()).filter(Boolean);
            await api.updateMeasure(id, fields);
            load();
          }}
          onDelete={async (id) => {
            await api.deleteMeasure(id);
            load();
          }}
          onAdd={async (fields) => {
            fields.applies_to = (fields.applies_to || "").split(",").map((s) => s.trim()).filter(Boolean);
            await api.createMeasure(fields);
            load();
          }}
        />
      </div>

      <h2>Fuel emission factors &amp; unit costs</h2>
      <div className="table-scroll">
        <table className="list-table">
          <thead>
            <tr>
              <th>Fuel</th>
              <th>Unit rate (£/kWh)</th>
              <th>Standing charge (£/day)</th>
              <th>Scope 1&amp;2 (kg CO2e/kWh)</th>
              <th>Scope 3 (kg CO2e/kWh)</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((f) => (
              <EmissionFactorRow key={f.id} factor={f} onSave={load} />
            ))}
          </tbody>
        </table>
      </div>

      <h2>Default U-values by building age band</h2>
      <p className="muted">
        Seeded from the project brief's historic fabric table. The header row for most columns was cropped in the
        source image - only the final period ("2013 &amp; 2016") was legible, so the other period labels are a
        best-effort reconstruction of standard UK Building Regs Part L compliance periods.{" "}
        <strong>Verify against your CIBSE/Building Regs source before relying on these for a real HDP.</strong>
      </p>
      <div className="table-scroll">
        <EditableTable
          columns={[
            { key: "period_label", label: "Period", type: "text" },
            { key: "wall_u", label: "Wall U", type: "number", width: "60px" },
            { key: "floor_u", label: "Floor U", type: "number", width: "60px" },
            { key: "pitched_roof_u", label: "Pitched roof U", type: "number", width: "70px" },
            { key: "flat_roof_u", label: "Flat roof U", type: "number", width: "70px" },
            { key: "window_metal_u", label: "Window (metal)", type: "number", width: "70px" },
            { key: "window_other_u", label: "Window (other)", type: "number", width: "70px" },
            { key: "pedestrian_door_u", label: "Pedestrian door U", type: "number", width: "70px" },
            { key: "vehicle_door_u", label: "Vehicle door U", type: "number", width: "70px" },
            { key: "entrance_door_u", label: "Entrance door U", type: "number", width: "70px" },
            { key: "air_permeability", label: "Air permeability", type: "number", width: "70px" },
          ]}
          rows={ageBands}
          newRowDefaults={{ period_label: "", sort_order: ageBands.length + 1 }}
          onUpdate={async (id, fields) => {
            await api.updateAgeBand(id, fields);
            load();
          }}
          onDelete={async (id) => {
            await api.deleteAgeBand(id);
            load();
          }}
          onAdd={async (fields) => {
            await api.createAgeBand(fields);
            load();
          }}
        />
      </div>

      <FloorUValueCalculator />
    </div>
  );
}

function EmissionFactorRow({ factor, onSave }) {
  const [form, setForm] = useState(factor);
  useEffect(() => setForm(factor), [factor]);

  const commit = async () => {
    await api.updateEmissionFactor(factor.id, form);
    onSave();
  };

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  return (
    <tr>
      <td>{factor.fuel_type}</td>
      <td>
        <input type="number" step="any" value={form.unit_rate_per_kwh ?? ""} onChange={set("unit_rate_per_kwh")} onBlur={commit} />
      </td>
      <td>
        <input type="number" step="any" value={form.standing_charge_per_day ?? ""} onChange={set("standing_charge_per_day")} onBlur={commit} />
      </td>
      <td>
        <input type="number" step="any" value={form.scope_1_2_kg_per_kwh ?? ""} onChange={set("scope_1_2_kg_per_kwh")} onBlur={commit} />
      </td>
      <td>
        <input type="number" step="any" value={form.scope_3_kg_per_kwh ?? ""} onChange={set("scope_3_kg_per_kwh")} onBlur={commit} />
      </td>
      <td>
        <input type="text" value={form.source ?? ""} onChange={set("source")} onBlur={commit} style={{ width: "280px" }} />
      </td>
    </tr>
  );
}

function FloorUValueCalculator() {
  const [points, setPoints] = useState([]);
  const [form, setForm] = useState({ perimeter_m: "", area_m2: "", k_value: 1.63, thickness_m: 0.1 });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const loadPoints = () => api.listFloorReferencePoints().then(setPoints);

  useEffect(() => {
    loadPoints();
  }, []);

  const calculate = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await api.calculateFloorUValue({
        perimeter_m: parseFloat(form.perimeter_m),
        area_m2: parseFloat(form.area_m2),
        k_value: parseFloat(form.k_value),
        thickness_m: parseFloat(form.thickness_m),
      });
      if (res.error) setError(res.error);
      setResult(res);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <>
      <h2>U-Value Floor Calculator</h2>
      <p className="muted">
        Perimeter/area ratio method (BS EN ISO 13370 / BRE "Table C1"). The reference grid below only has the points
        actually used in the source workbook - add more perimeter/area-ratio rows and thermal-resistance columns from
        your BRE/CIBSE source table as needed; the interpolation works with however many points you give it.
      </p>
      <form className="inline-form" onSubmit={calculate}>
        <label>
          Perimeter (m)
          <input type="number" step="any" value={form.perimeter_m} onChange={(e) => setForm({ ...form, perimeter_m: e.target.value })} required />
        </label>
        <label>
          Area (m2)
          <input type="number" step="any" value={form.area_m2} onChange={(e) => setForm({ ...form, area_m2: e.target.value })} required />
        </label>
        <label>
          Floor k-value (W/mK)
          <input type="number" step="any" value={form.k_value} onChange={(e) => setForm({ ...form, k_value: e.target.value })} required />
        </label>
        <label>
          Thickness (m)
          <input type="number" step="any" value={form.thickness_m} onChange={(e) => setForm({ ...form, thickness_m: e.target.value })} required />
        </label>
        <button type="submit">Calculate</button>
      </form>

      {error && <p className="error">{error}</p>}
      {result && !result.error && (
        <p>
          p/a ratio = {result.p_a_ratio?.toFixed(4)}, thermal resistance = {result.thermal_resistance?.toFixed(4)} m2K/W &rarr;{" "}
          <strong>U-value = {result.u_value} W/m2K</strong>
        </p>
      )}

      <h3>Reference grid points</h3>
      <div className="table-scroll">
        <EditableTable
          columns={[
            { key: "p_a_ratio", label: "P/A ratio", type: "number" },
            { key: "resistance", label: "Resistance (m2K/W)", type: "number" },
            { key: "u_value", label: "U value (W/m2K)", type: "number" },
          ]}
          rows={points}
          newRowDefaults={{ p_a_ratio: 0, resistance: 0, u_value: 0 }}
          onUpdate={() => {}}
          onDelete={async (id) => {
            await api.deleteFloorReferencePoint(id);
            loadPoints();
          }}
          onAdd={async (fields) => {
            await api.createFloorReferencePoint(fields);
            loadPoints();
          }}
        />
      </div>
      <p className="muted">Reference points are add/delete only here - delete and re-add a point to change its value.</p>
    </>
  );
}
