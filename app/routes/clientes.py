"""
BovTurn — Cadastro de clientes/produtores
==========================================
Registra um produtor (telefone WhatsApp) + sua fazenda no banco,
para que o agente personalize as respostas com o contexto dele.

Cadastro rápido cria, numa transação:
  cliente → fazenda → (módulo com a forrageira) → usuário (telefone)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app import db

router = APIRouter()


class CadastroCliente(BaseModel):
    nome: str = Field(..., min_length=2)
    telefone: str = Field(..., min_length=8)
    fazenda: str = Field(..., min_length=2)
    estado: Optional[str] = None              # UF, 2 letras
    tem_sequeiro: bool = False                # fazenda pode ter os dois
    tem_irrigado: bool = False
    forrageiras: list[str] = []               # pode ter mais de uma
    area_util_ha: Optional[float] = None


def _normalizar_telefone(t: str) -> str:
    """Mantém só dígitos e prefixa +; aceita já com +."""
    so_digitos = "".join(c for c in t if c.isdigit())
    return "+" + so_digitos if so_digitos else t


@router.post("/")
async def cadastrar(dados: CadastroCliente):
    if not db.tem_banco():
        raise HTTPException(503, "Banco não conectado.")

    telefone = _normalizar_telefone(dados.telefone)
    tem_irr = dados.tem_irrigado
    tem_seq = dados.tem_sequeiro or not tem_irr  # default sequeiro se nada marcado
    nivel = "intensivo_irrigado" if tem_irr else "intensivo_sequeiro"
    estado = (dados.estado or "").strip().upper()[:2] or None
    forrageiras = [f.strip() for f in dados.forrageiras if f and f.strip()]
    if tem_irr and tem_seq:
        sistema_label = "misto"
    elif tem_irr:
        sistema_label = "irrigado"
    else:
        sistema_label = "sequeiro"

    async with db.pool().acquire() as con:
        existente = await con.fetchval(
            "SELECT nome FROM usuarios WHERE telefone = $1", telefone
        )
        if existente:
            raise HTTPException(409, f"Telefone já cadastrado para {existente}.")

        async with con.transaction():
            cliente_id = await con.fetchval(
                "INSERT INTO clientes (nome, telefone) VALUES ($1,$2) RETURNING id",
                dados.nome, telefone,
            )
            fazenda_id = await con.fetchval(
                """
                INSERT INTO fazendas (cliente_id, nome, estado, area_util_ha,
                                      nivel_tecnologico, tem_irrigacao)
                VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
                """,
                cliente_id, dados.fazenda, estado, dados.area_util_ha,
                nivel, tem_irr,
            )
            # Um módulo por forrageira (uso reflete o sistema predominante)
            uso = "pastejo_irrigado" if tem_irr else "intensivo_sequeiro"
            for forr in forrageiras:
                await con.execute(
                    """
                    INSERT INTO modulos (fazenda_id, identificacao, forrageira, uso_atual)
                    VALUES ($1,$2,$3,$4)
                    """,
                    fazenda_id, forr, forr, uso,
                )
            # Marca presença de sequeiro quando a fazenda é mista (p/ rótulo)
            if tem_irr and tem_seq:
                await con.execute(
                    """
                    INSERT INTO modulos (fazenda_id, identificacao, uso_atual)
                    VALUES ($1,'Área sequeiro','intensivo_sequeiro')
                    """,
                    fazenda_id,
                )
            await con.execute(
                """
                INSERT INTO usuarios (fazenda_id, nome, telefone, perfil)
                VALUES ($1,$2,$3,'produtor')
                """,
                fazenda_id, dados.nome, telefone,
            )

    return {
        "sucesso": True,
        "telefone": telefone,
        "fazenda": dados.fazenda,
        "sistema": sistema_label,
        "forrageiras": forrageiras,
        "mensagem": f"{dados.nome} cadastrado. O agente já personaliza para {telefone}.",
    }


@router.get("/")
async def listar():
    if not db.tem_banco():
        raise HTTPException(503, "Banco não conectado.")
    async with db.pool().acquire() as con:
        linhas = await con.fetch(
            """
            SELECT u.telefone, u.nome, f.nome AS fazenda,
                   f.estado, f.tem_irrigacao, f.id AS fazenda_id,
                   EXISTS (
                     SELECT 1 FROM modulos m
                     WHERE m.fazenda_id = f.id AND m.uso_atual ILIKE '%sequeiro%'
                   ) AS tem_sequeiro,
                   (SELECT array_agg(DISTINCT m.forrageira)
                      FROM modulos m
                      WHERE m.fazenda_id = f.id AND m.forrageira IS NOT NULL) AS forrageiras,
                   (SELECT COUNT(*) FROM giro_resultados gr WHERE gr.fazenda_id = f.id) AS giros
            FROM usuarios u
            JOIN fazendas f ON f.id = u.fazenda_id
            WHERE u.ativo
            ORDER BY u.criado_em DESC
            """
        )

    def sistema_label(irr, seq):
        if irr and seq:
            return "misto"
        return "irrigado" if irr else "sequeiro"

    return [
        {
            "telefone": r["telefone"],
            "nome": r["nome"],
            "fazenda": r["fazenda"],
            "estado": r["estado"],
            "sistema": sistema_label(r["tem_irrigacao"], r["tem_sequeiro"]),
            "forrageiras": list(r["forrageiras"]) if r["forrageiras"] else [],
            "giros_historico": r["giros"],
        }
        for r in linhas
    ]
