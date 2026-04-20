import { Fragment, useEffect, useState } from "react";
import { api, EventHit, Integration } from "../lib/api";

function levelBadge(level: string | null) {
  const l = (level ?? "").toLowerCase();
  if (l === "error" || l === "critical") return "error";
  if (l === "warn" || l === "warning") return "warn";
  if (l === "info") return "info";
  return "muted";
}

function formatTimestamp(ts: string | null) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString();
  } catch {
    return ts;
  }
}

export default function EventsPage() {
  const [items, setItems] = useState<EventHit[]>([]);
  const [total, setTotal] = useState(0);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [integration, setIntegration] = useState<string>("");
  const [level, setLevel] = useState<string>("");
  const [q, setQ] = useState<string>("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  async function loadIntegrations() {
    try {
      setIntegrations(await api.listIntegrations());
    } catch {
      /* ignore */
    }
  }

  async function search() {
    setLoading(true);
    try {
      const res = await api.searchEvents({ integration, level, q, size: 100 });
      setItems(res.items);
      setTotal(res.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadIntegrations();
  }, []);

  useEffect(() => {
    search();
    if (!autoRefresh) return;
    const t = setInterval(search, 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [integration, level, q, autoRefresh]);

  return (
    <>
      <h1 className="page-title">Eventos</h1>
      <p className="page-subtitle">
        Logs e eventos indexados no Elasticsearch — atualização a cada 5s.
      </p>

      <div className="toolbar">
        <select value={integration} onChange={(e) => setIntegration(e.target.value)} style={{ width: 180 }}>
          <option value="">Todas integrações</option>
          {integrations.map((i) => (
            <option key={i.id} value={i.name}>
              {i.name}
            </option>
          ))}
        </select>
        <select value={level} onChange={(e) => setLevel(e.target.value)} style={{ width: 140 }}>
          <option value="">Todos níveis</option>
          <option value="info">info</option>
          <option value="warn">warn</option>
          <option value="error">error</option>
        </select>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Buscar no campo 'message'…"
          style={{ flex: 1, minWidth: 220 }}
        />
        <label className="flex gap-2" style={{ alignItems: "center", margin: 0 }}>
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            style={{ width: "auto" }}
          />
          <span style={{ textTransform: "none", letterSpacing: 0, color: "var(--text)" }}>
            Auto-refresh
          </span>
        </label>
        <button className="secondary" onClick={search}>
          {loading ? "…" : "Atualizar"}
        </button>
      </div>

      {error && (
        <div className="card mb-4" style={{ borderColor: "var(--error)" }}>
          {error}
        </div>
      )}

      <div className="card">
        <div className="flex-between mb-3">
          <span className="stat-label">{total.toLocaleString()} eventos</span>
        </div>
        {items.length === 0 ? (
          <div className="empty">Nenhum evento encontrado.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th style={{ width: 170 }}>Data/hora</th>
                <th style={{ width: 80 }}>Nível</th>
                <th style={{ width: 140 }}>Integração</th>
                <th>Mensagem</th>
              </tr>
            </thead>
            <tbody>
              {items.map((ev) => (
                <Fragment key={ev.id}>
                  <tr
                    onClick={() => setExpanded(expanded === ev.id ? null : ev.id)}
                    style={{ cursor: "pointer" }}
                  >
                    <td>{formatTimestamp(ev.timestamp)}</td>
                    <td>
                      <span className={`badge ${levelBadge(ev.level)}`}>{ev.level ?? "—"}</span>
                    </td>
                    <td>{ev.integration ?? "—"}</td>
                    <td>{ev.message ?? "—"}</td>
                  </tr>
                  {expanded === ev.id && (
                    <tr>
                      <td colSpan={4}>
                        <pre>{JSON.stringify(ev.source, null, 2)}</pre>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
