"""
BovTurn Intelligence — Camada de banco (PostgreSQL + TimescaleDB)
=================================================================
Pool de conexões asyncpg, gerenciado pelo ciclo de vida do FastAPI.

Filosofia: o banco é OPCIONAL para desenvolvimento.
- Se DATABASE_URL existe  → conecta, e o agente puxa contexto real.
- Se DATABASE_URL ausente → pool fica None, e o agente cai no mock.

Assim o app nunca quebra por falta de banco, e a migração para o
Railway é só setar a variável de ambiente.
"""

import os
from typing import Optional

import asyncpg

# Pool global — criado no startup, fechado no shutdown.
_pool: Optional[asyncpg.Pool] = None


def database_url() -> Optional[str]:
    """URL de conexão. Railway expõe DATABASE_URL automaticamente."""
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")


async def conectar() -> None:
    """Abre o pool de conexões. Idempotente e tolerante a falha."""
    global _pool
    if _pool is not None:
        return
    url = database_url()
    if not url:
        print("[db] DATABASE_URL não definida — rodando sem banco (modo mock).")
        return
    try:
        _pool = await asyncpg.create_pool(
            dsn=url,
            min_size=1,
            max_size=10,
            command_timeout=30,
            # Railway/Neon usam SSL; asyncpg detecta via sslmode na URL.
        )
        print("[db] Pool PostgreSQL conectado.")
    except Exception as e:
        # Não derruba o app — só registra e segue em modo mock.
        _pool = None
        print(f"[db] Falha ao conectar ({e}). Rodando em modo mock.")


async def desconectar() -> None:
    """Fecha o pool no shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        print("[db] Pool PostgreSQL fechado.")


def pool() -> Optional[asyncpg.Pool]:
    """Retorna o pool atual (ou None se o banco não está conectado)."""
    return _pool


def tem_banco() -> bool:
    """True se há banco conectado e pronto para consultas."""
    return _pool is not None
