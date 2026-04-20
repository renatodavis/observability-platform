import { FormEvent, useEffect, useState } from "react";
import { api, Integration, IntegrationInput } from "../lib/api";

const EMPTY: IntegrationInput = {
  name: "",
  description: "",
  queue: "",
  index: "",
  enabled: true,
};

export default function IntegrationsPage() {
  const [items, setItems] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState<IntegrationInput>(EMPTY);
  const [saving, setSaving] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      setItems(await api.listIntegrations());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  function autoFill(name: string) {
    const normalized = name
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9-]+/g, "-")
      .replace(/^-+|-+$/g, "");
    setForm((f) => ({
      ...f,
      name,
      queue: normalized ? `${normalized}.events` : "",
      index: normalized ? `${normalized}-logs` : "",
    }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.createIntegration(form);
      setShowModal(false);
      setForm(EMPTY);
      await reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  }

  async function toggleEnabled(it: Integration) {
    try {
      await api.updateIntegration(it.id, { enabled: !it.enabled });
      await reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  async function remove(it: Integration) {
    if (!confirm(`Remover integração "${it.name}"?`)) return;
    try {
      await api.deleteIntegration(it.id);
      await reload();
    } catch (err) {
      alert(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <>
      <div className="flex-between mb-4">
        <div>
          <h1 className="page-title">Integrações</h1>
          <p className="page-subtitle">
            Cada integração mapeia uma fila RabbitMQ para um índice do Elasticsearch.
          </p>
        </div>
        <button onClick={() => setShowModal(true)}>+ Nova integração</button>
      </div>

      {error && (
        <div className="card mb-4" style={{ borderColor: "var(--error)" }}>
          {error}
        </div>
      )}

      <div className="card">
        {loading ? (
          <div className="empty">Carregando…</div>
        ) : items.length === 0 ? (
          <div className="empty">
            Nenhuma integração cadastrada. Clique em <strong>+ Nova integração</strong> para começar.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Fila (RabbitMQ)</th>
                <th>Índice (Elasticsearch)</th>
                <th>Status</th>
                <th style={{ width: 200 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.id}>
                  <td>
                    <strong>{it.name}</strong>
                    {it.description && (
                      <div style={{ fontSize: 12, color: "var(--muted)" }}>
                        {it.description}
                      </div>
                    )}
                  </td>
                  <td><code>{it.queue}</code></td>
                  <td><code>{it.index}</code></td>
                  <td>
                    <span className={`badge ${it.enabled ? "success" : "muted"}`}>
                      {it.enabled ? "Ativa" : "Desativada"}
                    </span>
                  </td>
                  <td>
                    <div className="flex gap-2">
                      <button className="secondary" onClick={() => toggleEnabled(it)}>
                        {it.enabled ? "Desativar" : "Ativar"}
                      </button>
                      <button className="danger" onClick={() => remove(it)}>
                        Remover
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Nova integração</h3>
            <form onSubmit={onSubmit} className="grid" style={{ gap: 12 }}>
              <div>
                <label>Nome</label>
                <input
                  value={form.name}
                  onChange={(e) => autoFill(e.target.value)}
                  placeholder="ex: legacy-erp"
                  required
                />
              </div>
              <div>
                <label>Descrição</label>
                <input
                  value={form.description ?? ""}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Sistema ERP legado em Delphi"
                />
              </div>
              <div>
                <label>Fila RabbitMQ</label>
                <input
                  value={form.queue}
                  onChange={(e) => setForm({ ...form, queue: e.target.value })}
                  required
                />
              </div>
              <div>
                <label>Índice Elasticsearch</label>
                <input
                  value={form.index}
                  onChange={(e) => setForm({ ...form, index: e.target.value })}
                  required
                />
              </div>
              <div className="flex gap-3 mt-3" style={{ justifyContent: "flex-end" }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setShowModal(false)}
                >
                  Cancelar
                </button>
                <button type="submit" disabled={saving}>
                  {saving ? "Salvando…" : "Criar"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
