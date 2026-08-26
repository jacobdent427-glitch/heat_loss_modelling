const BASE = "http://localhost:5000/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const data = await res.json();
      msg = data.error || msg;
    } catch {}
    throw new Error(msg);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listProjects: () => request("/projects"),
  createProject: (data) => request("/projects", { method: "POST", body: JSON.stringify(data) }),
  getProject: (id) => request(`/projects/${id}`),
  updateProject: (id, data) => request(`/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id) => request(`/projects/${id}`, { method: "DELETE" }),
  getProjectOverview: (id) => request(`/projects/${id}/overview`),
  geocode: (address) => request(`/geocode?address=${encodeURIComponent(address)}`),

  listPlantRooms: (projectId) => request(`/projects/${projectId}/plant-rooms`),
  createPlantRoom: (projectId, data) =>
    request(`/projects/${projectId}/plant-rooms`, { method: "POST", body: JSON.stringify(data) }),
  getPlantRoom: (id) => request(`/plant-rooms/${id}`),
  updatePlantRoom: (id, data) => request(`/plant-rooms/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deletePlantRoom: (id) => request(`/plant-rooms/${id}`, { method: "DELETE" }),
  getPlantRoomResults: (id) => request(`/plant-rooms/${id}/results`),
  autoPropose: (id) => request(`/plant-rooms/${id}/auto-propose`, { method: "POST" }),

  listElements: (roomId, type) => request(`/plant-rooms/${roomId}/${type}`),
  createElement: (roomId, type, data) =>
    request(`/plant-rooms/${roomId}/${type}`, { method: "POST", body: JSON.stringify(data) }),
  updateElement: (type, id, data) => request(`/${type}/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteElement: (type, id) => request(`/${type}/${id}`, { method: "DELETE" }),

  listMeasures: () => request("/measures"),
  createMeasure: (data) => request("/measures", { method: "POST", body: JSON.stringify(data) }),
  updateMeasure: (id, data) => request(`/measures/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteMeasure: (id) => request(`/measures/${id}`, { method: "DELETE" }),

  listEmissionFactors: () => request("/emission-factors"),
  updateEmissionFactor: (id, data) => request(`/emission-factors/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  listAgeBands: () => request("/age-band-u-values"),
  createAgeBand: (data) => request("/age-band-u-values", { method: "POST", body: JSON.stringify(data) }),
  updateAgeBand: (id, data) => request(`/age-band-u-values/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteAgeBand: (id) => request(`/age-band-u-values/${id}`, { method: "DELETE" }),

  listFloorReferencePoints: () => request("/floor-u-value/reference-points"),
  createFloorReferencePoint: (data) =>
    request("/floor-u-value/reference-points", { method: "POST", body: JSON.stringify(data) }),
  deleteFloorReferencePoint: (id) => request(`/floor-u-value/reference-points/${id}`, { method: "DELETE" }),
  calculateFloorUValue: (data) => request("/floor-u-value/calculate", { method: "POST", body: JSON.stringify(data) }),
};
