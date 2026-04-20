import { useEffect, useState } from "react";
import { api, Health, Stats } from "../lib/api";

function levelBadge(level: string) {
  const l = level.toLowerCase();
  if (l === "error" || l === "critical") return "error";
  if (l === "warn" || l === "warning") return "warn";
  if (l === "info") return "info";
  return "muted";
}

export default function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    try {
      const [h, s] = await Promise.all([api.health(), api.stats()]);
      setHealth(h);
      setStats(s);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    reload();
    const t = setInterval(reload, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">Visão geral da saúde da plataforma e dos eventos indexados.</p>

      {error && (
        <div className="card mb-4" style={{ borderColor: "var(--error)" }}>
          Falha ao conectar na API: <code>{error}</code>
        </div>
      )}

      <div className="grid grid-3 mb-4">
        <div className="card">
          <div className="stat-label">Eventos indexados</div>
          <div className="stat-value">{stats?.total_events ?? "—"}</div>
        </div>
        <div className="card">
          <div className="stat-label">Elasticsearch</div>
          <div className="stat-value">
            <span className={`status-dot ${health?.elasticsearch ? "ok" : "down"}`} />
            {health?.elasticsearch ? "Online" : "Offline"}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">RabbitMQ</div>
          <div className="stat-value">
            <span className={`status-dot ${health?.rabbitmq ? "ok" : "down"}`} />
            {health?.rabbitmq ? "Online" : "Offline"}
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Eventos por integração</h3>
          {stats?.by_integration?.length ? (
            <table>
              <thead>
                <tr>
                  <th>Integração</th>
                  <th style={{ textAlign: "right" }}>Eventos</th>
                </tr>
              </thead>
              <tbody>
                {stats.by_integration.map((b) => (
                  <tr key={b.integration}>
                    <td>{b.integration}</td>
                    <td style={{ textAlign: "right" }}>{b.count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">Nenhum evento indexado ainda.</div>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Eventos por severidade</h3>
          {stats?.by_level?.length ? (
            <table>
              <thead>
                <tr>
                  <th>Nível</th>
                  <th style={{ textAlign: "right" }}>Eventos</th>
                </tr>
              </thead>
              <tbody>
                {stats.by_level.map((b) => (
                  <tr key={b.integration}>
                    <td>
                      <span className={`badge ${levelBadge(b.integration)}`}>
                        {b.integration}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>{b.count.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="empty">Nenhum evento indexado ainda.</div>
          )}
        </div>
      </div>
    </>
  );
}
