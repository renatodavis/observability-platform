const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `${res.status} ${res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface Integration {
  id: number;
  name: string;
  description: string;
  queue: string;
  index: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface IntegrationInput {
  name: string;
  description?: string;
  queue: string;
  index: string;
  enabled?: boolean;
}

export interface EventHit {
  id: string;
  index: string;
  timestamp: string | null;
  level: string | null;
  message: string | null;
  integration: string | null;
  source: Record<string, unknown>;
}

export interface EventsPage {
  total: number;
  items: EventHit[];
}

export interface Stats {
  total_events: number;
  by_integration: { integration: string; count: number }[];
  by_level: { integration: string; count: number }[];
}

export interface Health {
  status: string;
  elasticsearch: boolean;
  rabbitmq: boolean;
}

export const api = {
  health: () => request<Health>("/api/health"),
  stats: () => request<Stats>("/api/stats"),
  listIntegrations: () => request<Integration[]>("/api/integrations"),
  createIntegration: (data: IntegrationInput) =>
    request<Integration>("/api/integrations", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateIntegration: (id: number, data: Partial<IntegrationInput>) =>
    request<Integration>(`/api/integrations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteIntegration: (id: number) =>
    request<void>(`/api/integrations/${id}`, { method: "DELETE" }),
  searchEvents: (params: {
    integration?: string;
    level?: string;
    q?: string;
    size?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return request<EventsPage>(`/api/events?${qs.toString()}`);
  },
  publishEvent: (data: {
    integration: string;
    level: string;
    message: string;
    source?: string;
    attributes?: Record<string, unknown>;
  }) =>
    request<{ status: string; queue: string }>("/api/events/publish", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
