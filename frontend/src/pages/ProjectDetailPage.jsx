import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [name, setName] = useState("");
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = () => api.getProject(projectId).then(setProject).catch((e) => setError(e.message));

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  const addPlantRoom = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    const room = await api.createPlantRoom(projectId, { name });
    setName("");
    navigate(`/plant-rooms/${room.id}`);
  };

  const deleteRoom = async (id) => {
    if (!confirm("Delete this plant room and all its elements?")) return;
    await api.deletePlantRoom(id);
    load();
  };

  if (!project) return <div className="page">{error || "Loading..."}</div>;

  return (
    <div className="page">
      <p>
        <Link to="/">&larr; All projects</Link>
      </p>
      <h1>{project.name}</h1>
      <p className="muted">{project.address}</p>
      <p>
        <Link to={`/projects/${project.id}/overview`}>View project overview (Overview of Heat Loss)</Link>
      </p>

      <h2>Plant rooms / loads</h2>
      <form className="inline-form" onSubmit={addPlantRoom}>
        <input placeholder="Plant room name" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit">Add plant room</button>
      </form>

      <table className="list-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Fuel</th>
            <th>Annual usage (kWh)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {project.plant_rooms.map((r) => (
            <tr key={r.id}>
              <td>
                <Link to={`/plant-rooms/${r.id}`}>{r.name}</Link>
              </td>
              <td>{r.fuel_type}</td>
              <td>{r.annual_fuel_usage_kwh}</td>
              <td>
                <button className="danger" onClick={() => deleteRoom(r.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {project.plant_rooms.length === 0 && (
            <tr>
              <td colSpan={4}>No plant rooms yet - add one above.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
