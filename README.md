# Observability Platform

Plataforma de observabilidade que integra sistemas legados ao **Elasticsearch** usando **RabbitMQ** como barramento de eventos. Inclui API de configuração, worker com retry/DLQ, dashboard web e simulador de sistema legado — tudo pronto para rodar com Docker Compose e evoluir para produção.

> Protótipo funcional — pronto para colocar em produção após revisar variáveis de ambiente, segredos, políticas de retenção do ES e escalar réplicas.

## Arquitetura

```
┌──────────────────┐   publish    ┌────────────┐  consume   ┌─────────────┐   index   ┌─────────────────┐
│  Sistema legado  │ ───────────▶ │  RabbitMQ  │ ─────────▶ │   Worker    │ ────────▶ │  Elasticsearch  │
│  (simulador)     │              │  (broker)  │            │  (Python)   │           │                 │
└──────────────────┘              └────────────┘            └─────────────┘           └────────┬────────┘
                                                                                               │
                                                                                               │ query
                                                                                               ▼
                                          ┌─────────────┐   HTTP    ┌───────────┐    HTTP    ┌──────────┐
                                          │  Frontend   │ ────────▶ │   API     │ ─────────▶ │   ES     │
                                          │  (React)    │           │ (FastAPI) │            │          │
                                          └─────────────┘           └───────────┘            └──────────┘
                                                                          │
                                                                          └──▶ Kibana (UI oficial do ES)
```

### Componentes

| Serviço         | Descrição                                                                                  | Porta |
| --------------- | ------------------------------------------------------------------------------------------ | ----- |
| `api`           | FastAPI. CRUD de integrações, health, busca em logs, estatísticas agregadas.               | 8000  |
| `worker`        | Consumidor do RabbitMQ que normaliza eventos e indexa no Elasticsearch. Retry + DLQ.       | —     |
| `simulator`     | Publica eventos simulando um sistema legado (logs de aplicação, auditoria, métricas).      | —     |
| `frontend`      | Dashboard em React/Vite para gerenciar integrações e visualizar eventos em tempo real.     | 5173  |
| `rabbitmq`      | Broker de mensageria (management UI habilitada).                                           | 5672, 15672 |
| `elasticsearch` | Armazenamento e indexação dos eventos.                                                     | 9200  |
| `kibana`        | UI oficial do Elastic Stack para exploração avançada.                                      | 5601  |

## Quick start

Requer Docker e Docker Compose v2.

```bash
cp .env.example .env
docker compose up -d --build
```

Serviços:

- Frontend:      http://localhost:5173
- API:           http://localhost:8000/docs
- RabbitMQ:      http://localhost:15672  (user: `observ` / pass: `observ`)
- Kibana:        http://localhost:5601
- Elasticsearch: http://localhost:9200

### Publicar um evento de teste manualmente

```bash
curl -X POST http://localhost:8000/api/events/publish \
  -H "Content-Type: application/json" \
  -d '{
    "integration": "legacy-erp",
    "level": "info",
    "message": "Pedido #1234 criado",
    "attributes": {"order_id": 1234, "customer": "ACME"}
  }'
```

O evento será publicado no RabbitMQ, consumido pelo worker e indexado no Elasticsearch. Atualize o dashboard para visualizá-lo.

### Simulador de sistema legado

O container `simulator` começa desligado (`profiles: [demo]`). Para ligar:

```bash
docker compose --profile demo up -d simulator
```

Ele publicará eventos fake a cada ~1s. Para parar: `docker compose stop simulator`.

## Configurando uma integração

O modelo de integração representa uma origem de dados legada. Cada integração define uma **fila** no RabbitMQ (criada automaticamente pelo worker) e um **índice** no Elasticsearch.

Via dashboard: acesse **Integrações** → **Nova integração**.

Via API:

```bash
curl -X POST http://localhost:8000/api/integrations \
  -H "Content-Type: application/json" \
  -d '{
    "name": "legacy-erp",
    "description": "ERP legado em Delphi",
    "queue": "legacy-erp.events",
    "index": "legacy-erp-logs",
    "enabled": true
  }'
```

O worker detecta novas integrações (poll a cada 10s) e começa a consumir imediatamente.

## Produção

Este repositório está pronto para ser adaptado para ambiente produtivo:

1. **Segredos**: mova `RABBITMQ_PASS`, `ELASTIC_PASSWORD` e `API_SECRET` para o seu gerenciador de segredos (Vault, AWS Secrets Manager, Kubernetes Secrets).
2. **Elasticsearch**: habilite TLS/xpack-security, defina políticas ILM para rotação, configure um cluster com múltiplas réplicas (`discovery.seed_hosts`).
3. **RabbitMQ**: use cluster HA (`mirrored queues` ou `quorum queues`), TLS e usuários dedicados por integração.
4. **API/Worker**: rode atrás de um gateway (Traefik/Nginx), habilite autenticação JWT no endpoint, suba réplicas horizontais.
5. **Frontend**: faça build estático (`npm run build`) e sirva via CDN/Nginx.
6. **Observabilidade da plataforma**: habilite Prometheus scraping nas rotas `/metrics` (expostas via `prometheus-fastapi-instrumentator`).

Os Dockerfiles já seguem boas práticas (multi-stage, usuário não-root, healthcheck, logs estruturados em JSON).

## Desenvolvimento local (sem Docker)

```bash
# API
cd api && pip install -e . && uvicorn app.main:app --reload

# Worker
cd worker && pip install -e . && python worker.py

# Frontend
cd frontend && npm install && npm run dev
```

Cada serviço lê configuração do `.env` na raiz do repo (via `pydantic-settings` no backend).

## Licença

MIT
