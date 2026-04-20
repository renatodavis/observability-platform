"""Simula um sistema legado publicando eventos via API da plataforma.

Cria as integrações se ainda não existirem e publica eventos aleatórios em loop.
"""
from __future__ import annotations

import asyncio
import random
import sys
from dataclasses import dataclass

import httpx
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    api_url: str = Field(default="http://api:8000", alias="API_URL")
    interval_seconds: float = Field(default=1.0, alias="SIMULATOR_INTERVAL_SECONDS")


@dataclass(frozen=True)
class IntegrationSpec:
    name: str
    description: str
    queue: str
    index: str


INTEGRATIONS: list[IntegrationSpec] = [
    IntegrationSpec(
        name="legacy-erp",
        description="ERP legado em Delphi",
        queue="legacy-erp.events",
        index="legacy-erp-logs",
    ),
    IntegrationSpec(
        name="payments",
        description="Sistema de pagamentos",
        queue="payments.events",
        index="payments-logs",
    ),
    IntegrationSpec(
        name="auth-service",
        description="Serviço de autenticação",
        queue="auth-service.events",
        index="auth-service-logs",
    ),
]

MESSAGES: dict[str, list[tuple[str, str]]] = {
    "legacy-erp": [
        ("info", "Pedido criado"),
        ("info", "Nota fiscal emitida"),
        ("warn", "Estoque abaixo do mínimo"),
        ("error", "Falha ao conectar com SAP"),
    ],
    "payments": [
        ("info", "Pagamento autorizado"),
        ("info", "Pagamento capturado"),
        ("warn", "Gateway de pagamento lento"),
        ("error", "Pagamento recusado pela operadora"),
    ],
    "auth-service": [
        ("info", "Usuário autenticado com sucesso"),
        ("warn", "Tentativa de login suspeita"),
        ("error", "Token JWT inválido"),
    ],
}


async def ensure_integrations(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/integrations")
    resp.raise_for_status()
    existing = {i["name"] for i in resp.json()}
    for spec in INTEGRATIONS:
        if spec.name in existing:
            continue
        r = await client.post(
            "/api/integrations",
            json={
                "name": spec.name,
                "description": spec.description,
                "queue": spec.queue,
                "index": spec.index,
                "enabled": True,
            },
        )
        if r.status_code not in (201, 409):
            r.raise_for_status()
        print(f"[simulator] integração garantida: {spec.name}", flush=True)


async def publish_random_event(client: httpx.AsyncClient) -> None:
    integration = random.choice(INTEGRATIONS)
    level, message = random.choice(MESSAGES[integration.name])
    attributes = {
        "request_id": f"req-{random.randint(1000, 9999)}",
        "duration_ms": random.randint(5, 1500),
        "user_id": f"user-{random.randint(1, 500)}",
    }
    resp = await client.post(
        "/api/events/publish",
        json={
            "integration": integration.name,
            "level": level,
            "message": message,
            "source": "simulator",
            "attributes": attributes,
        },
    )
    if resp.status_code != 200:
        print(f"[simulator] publish failed: {resp.status_code} {resp.text}", flush=True)


async def wait_for_api(client: httpx.AsyncClient) -> None:
    for attempt in range(60):
        try:
            resp = await client.get("/api/health", timeout=3)
            if resp.status_code == 200:
                return
        except Exception:
            pass
        await asyncio.sleep(2)
    raise RuntimeError("API not reachable")


async def main() -> None:
    settings = Settings()
    print(f"[simulator] conectando em {settings.api_url}", flush=True)
    async with httpx.AsyncClient(base_url=settings.api_url, timeout=10) as client:
        await wait_for_api(client)
        await ensure_integrations(client)
        print("[simulator] publicando eventos...", flush=True)
        while True:
            try:
                await publish_random_event(client)
            except Exception as exc:
                print(f"[simulator] erro: {exc}", flush=True)
            await asyncio.sleep(settings.interval_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
