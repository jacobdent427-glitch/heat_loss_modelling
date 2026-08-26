import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";

function fmt(n, dp = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "-";
  return Number(n).toFixed(dp);
}

export default function OverviewPage() {
  const { projectId } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getProjectOverview(projectId).then(setData).catch((e) => setError(e.message));
  }, [projectId]);

  if (!data) return <div className="page">{error || "Loading..."}</div>;

  return (
    <div className="page">
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to project</Link>
      </p>
      <h1>{data.project.name} - Overview of Heat Loss</h1>

      <h2>Peak heat loss by plant room</h2>
      <div className="table-scroll">
        <table className="list-table">
          <thead>
            <tr>
              <th>Plant room</th>
              <th>Volume (m3)</th>
              <th>HLC existing (W/K)</th>
              <th>HLC improved (W/K)</th>
              <th>Peak heat loss existing (kW)</th>
              <th>Peak heat loss improved (kW)</th>
            </tr>
          </thead>
          <tbody>
            {data.plant_rooms.map((r) => (
              <tr key={r.plant_room_id}>
                <td>
                  <Link to={`/plant-rooms/${r.plant_room_id}`}>{r.plant_room_name}</Link>
                </td>
                <td>{fmt(r.volume_m3)}</td>
                <td>{fmt(r.heat_loss_coefficient_w_per_k.existing)}</td>
                <td>{fmt(r.heat_loss_coefficient_w_per_k.improved)}</td>
                <td>{fmt(r.peak_heat_loss_kw.existing)}</td>
                <td>{fmt(r.peak_heat_loss_kw.improved)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td>
                <strong>Total</strong>
              </td>
              <td></td>
              <td></td>
              <td></td>
              <td>
                <strong>{fmt(data.peak_heat_loss_kw_total.existing)}</strong>
              </td>
              <td>
                <strong>{fmt(data.peak_heat_loss_kw_total.improved)}</strong>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <h2>Building fabric improvement measures</h2>
      <p className="muted">Cost input table - relative cost of improvement (£/m2) and persistence factor come from each measure's reference data.</p>
      <div className="table-scroll">
        <table className="list-table spreadsheet-table">
          <thead>
            <tr>
              <th>Plant room</th>
              <th>Measure</th>
              <th>Description of Improvement</th>
              <th>Assumptions made</th>
              <th>Persistance Factor</th>
              <th>Area of improvement</th>
              <th>Relative cost of improvement (£/m2)</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {data.measures.map((m, i) => (
              <tr key={i}>
                <td>{m.plant_room_name}</td>
                <td>{m.measure_name}</td>
                <td>{m.measure_name}</td>
                <td>{m.assumptions}</td>
                <td>{fmt(m.lifetime_years, 0)}</td>
                <td>{fmt(m.area_of_improvement_m2)}</td>
                <td>&pound;{fmt(m.cost_per_m2, 0)}</td>
                <td>&pound;{fmt(m.cost_of_improvement_gbp, 2)}</td>
              </tr>
            ))}
            {data.measures.length === 0 && (
              <tr>
                <td colSpan={8}>No improvement measures assigned yet - set a proposed U-value and measure on an element in a plant room, or use "Auto-generate proposed building".</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2>Performance of proposed thermal improvements</h2>
      <div className="table-scroll">
        <table className="list-table spreadsheet-table">
          <thead>
            <tr>
              <th>Description of Improvement</th>
              <th>Assumptions made</th>
              <th>Energy savings (kWh/year)</th>
              <th>CO2 savings (Tonnes)</th>
              <th>Cost savings (£/year)</th>
              <th>Cost of Improvements</th>
              <th>Lifetime carbon savings</th>
              <th>Payback</th>
            </tr>
          </thead>
          <tbody>
            {data.measures.map((m, i) => (
              <tr key={i}>
                <td>{m.measure_name}</td>
                <td>{m.assumptions}</td>
                <td>{fmt(m.thermal_energy_saving_kwh, 2)}</td>
                <td>{fmt(m.co2_saving_tonnes_per_yr, 2)}</td>
                <td>&pound;{fmt(m.cost_saving_gbp_per_yr, 0)}</td>
                <td>&pound;{fmt(m.cost_of_improvement_gbp, 0)}</td>
                <td>{fmt(m.lifetime_carbon_saving_tonnes, 2)}</td>
                <td>{m.payback_period_years === null ? "-" : fmt(m.payback_period_years, 2)}</td>
              </tr>
            ))}
            {data.measures.length === 0 && (
              <tr>
                <td colSpan={8}>No improvement measures assigned yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <h2>Totals</h2>
      <table className="list-table">
        <tbody>
          <tr>
            <td>Total cost of improvements</td>
            <td>&pound;{fmt(data.totals.total_cost_of_improvement_gbp, 0)}</td>
          </tr>
          <tr>
            <td>Total annual cost saving</td>
            <td>&pound;{fmt(data.totals.total_cost_saving_gbp_per_yr, 0)}</td>
          </tr>
          <tr>
            <td>Total annual thermal energy saving</td>
            <td>{fmt(data.totals.total_thermal_energy_saving_kwh, 0)} kWh</td>
          </tr>
          <tr>
            <td>Total annual CO2 saving</td>
            <td>{fmt(data.totals.total_co2_saving_tonnes_per_yr, 3)} tonnes</td>
          </tr>
          <tr>
            <td>Total lifetime carbon saving</td>
            <td>{fmt(data.totals.total_lifetime_carbon_saving_tonnes, 2)} tonnes</td>
          </tr>
          <tr>
            <td>
              <strong>Blended payback period</strong>
            </td>
            <td>
              <strong>{data.totals.blended_payback_period_years === null ? "-" : fmt(data.totals.blended_payback_period_years, 1)} years</strong>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
