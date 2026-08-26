import { Link, Route, Routes } from "react-router-dom";
import ProjectListPage from "./pages/ProjectListPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import PlantRoomPage from "./pages/PlantRoomPage";
import ReferenceDataPage from "./pages/ReferenceDataPage";
import OverviewPage from "./pages/OverviewPage";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="brand">
          <img src="/btg-eddisons-logo.png" alt="BTG Eddisons" />
          Heat Loss Modelling
        </Link>
        <nav>
          <Link to="/">Projects</Link>
          <Link to="/reference-data">Reference Data</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<ProjectListPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/projects/:projectId/overview" element={<OverviewPage />} />
          <Route path="/plant-rooms/:roomId" element={<PlantRoomPage />} />
          <Route path="/reference-data" element={<ReferenceDataPage />} />
        </Routes>
      </main>
    </div>
  );
}
