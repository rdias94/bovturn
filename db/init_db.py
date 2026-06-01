"""
BovTurn — Inicializador de banco
=================================
Cria todo o schema e carrega os dados-semente em QUALQUER PostgreSQL
apontado por DATABASE_URL (Railway, Timescale Cloud, local...).

Uso:
    export DATABASE_URL="postgresql://user:senha@host:porta/banco"
    python -m db.init_db

Tolera Postgres sem TimescaleDB: se a extensão não existir, as tabelas
são criadas como tabelas comuns (as hypertables viram tabelas normais).
O agente WhatsApp não depende de hypertables — funciona em ambos.
"""

import os
import re
import sys
import asyncio
import asyncpg

AQUI = os.path.dirname(os.path.abspath(__file__))
ARQUIVOS = ["01_schema_core.sql", "02_dados_vpagro.sql", "03_seed_agente.sql"]


def _ler(arquivo: str) -> str:
    with open(os.path.join(AQUI, arquivo), "r", encoding="utf-8") as f:
        return f.read()


def _remover_timescale(sql: str) -> str:
    """Remove dependências de TimescaleDB para rodar em Postgres puro."""
    linhas = []
    for linha in sql.splitlines():
        if "CREATE EXTENSION IF NOT EXISTS timescaledb" in linha:
            continue
        if "create_hypertable" in linha:
            continue
        linhas.append(linha)
    return "\n".join(linhas)


async def main() -> int:
    url = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
    if not url:
        print("ERRO: defina DATABASE_URL antes de rodar.")
        return 1

    con = await asyncpg.connect(dsn=url)
    try:
        # Detecta TimescaleDB
        tem_timescale = False
        try:
            await con.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
            tem_timescale = True
            print("[init] TimescaleDB disponível — hypertables ativas.")
        except Exception:
            print("[init] TimescaleDB ausente — usando tabelas comuns (ok para o agente).")

        schema = _ler(ARQUIVOS[0])
        if not tem_timescale:
            schema = _remover_timescale(schema)

        print("[init] Criando schema...")
        await con.execute(schema)

        for arq in ARQUIVOS[1:]:
            print(f"[init] Carregando {arq}...")
            await con.execute(_ler(arq))

        # Conferência
        n_usuarios = await con.fetchval("SELECT COUNT(*) FROM usuarios")
        n_giros = await con.fetchval("SELECT COUNT(*) FROM giro_resultados")
        print(f"[init] OK — {n_usuarios} usuário(s), {n_giros} giro(s) finalizado(s) carregados.")
        return 0
    finally:
        await con.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
