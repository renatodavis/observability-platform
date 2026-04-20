import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Integrations from "./pages/Integrations";
import Events from "./pages/Events";

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-dot" />
          Observability
        </div>
        <nav>
          <NavLink to="/dashboard" className="nav-link">Dashboard</NavLink>
          <NavLink to="/integrations" className="nav-link">Integrações</NavLink>
          <NavLink to="/events" className="nav-link">Eventos</NavLink>
        </nav>
        <div className="sidebar-footer">
          <a href="http://localhost:15672" target="_blank" rel="noreferrer">RabbitMQ UI ↗</a>
          <a href="http://localhost:5601" target="_blank" rel="noreferrer">Kibana ↗</a>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/events" element={<Events />} />
        </Routes>
      </main>
    </div>
  );
}
