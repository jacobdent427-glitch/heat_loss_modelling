import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export default function ProjectListPage() {
  const [projects, setProjects] = useState([]);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = () => api.listProjects().then(setProjects).catch((e) => setError(e.message));

  useEffect(() => {
    load();
  }, []);

  const createProject = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      const project = await api.createProject({ name, address });
      setName("");
      setAddress("");
      navigate(`/projects/${project.id}`);
    } catch (e) {
      setError(e.message);
    }
  };

  const deleteProject = async (id) => {
    if (!confirm("Delete this project and everything in it?")) return;
    await api.deleteProject(id);
    load();
  };

  return (
    <div className="page">
      <h1>Projects</h1>
      {error && <p className="error">{error}</p>}

      <form className="inline-form" onSubmit={createProject}>
        <input placeholder="Project name" value={name} onChange={(e) => setName(e.target.value)} />
        <input placeholder="Address" value={address} onChange={(e) => setAddress(e.target.value)} />
        <button type="submit">New project</button>
      </form>

      <table className="list-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Address</th>
            <th>Plant rooms</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.id}>
              <td>
                <Link to={`/projects/${p.id}`}>{p.name}</Link>
              </td>
              <td>{p.address}</td>
              <td>{p.plant_room_count}</td>
              <td>
                <Link to={`/projects/${p.id}/overview`}>Overview</Link> |{" "}
                <button className="danger" onClick={() => deleteProject(p.id)}>
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {projects.length === 0 && (
            <tr>
              <td colSpan={4}>No projects yet - create one above.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
