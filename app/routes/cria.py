"""
BovTurn — Endpoint de Cria (rebanho + reprodutivo)
POST /api/cria → índices reprodutivos + projeção ano a ano + custo/lucro do bezerro.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.cria import CriaEntrada, CustoVacaAno, projetar

router = APIRouter()


class CriaRequest(BaseModel):
    matrizes: int = Field(1000, ge=0)
    touros: int = Field(40, ge=0)

    taxa_prenhez: float = 0.85
    perda_gestacional: float = 0.03
    mortalidade_bezerro: float = 0.04
    idade_primeiro_parto_meses: int = 36
    taxa_descarte_vacas: float = 0.16
    taxa_crescimento_rebanho: float = 0.0

    peso_desmame_kg: float = 210.0
    preco_kg_bezerro: float = 13.5
    preco_kg_bezerra: float = 11.5
    peso_vaca_descarte_kg: float = 450.0
    rendimento_vaca: float = 0.50
    preco_arroba_vaca: float = 280.0

    custo_pasto_arrendamento: float = 0.0
    custo_sal_mineral: float = 0.0
    custo_sanidade: float = 0.0
    custo_mao_de_obra: float = 0.0
    custo_outros: float = 0.0

    anos: int = Field(5, ge=1, le=15)


@router.post("/")
def cria(req: CriaRequest):
    entrada = CriaEntrada(
        matrizes=req.matrizes, touros=req.touros,
        taxa_prenhez=req.taxa_prenhez, perda_gestacional=req.perda_gestacional,
        mortalidade_bezerro=req.mortalidade_bezerro,
        idade_primeiro_parto_meses=req.idade_primeiro_parto_meses,
        taxa_descarte_vacas=req.taxa_descarte_vacas,
        taxa_crescimento_rebanho=req.taxa_crescimento_rebanho,
        peso_desmame_kg=req.peso_desmame_kg, preco_kg_bezerro=req.preco_kg_bezerro,
        preco_kg_bezerra=req.preco_kg_bezerra,
        peso_vaca_descarte_kg=req.peso_vaca_descarte_kg, rendimento_vaca=req.rendimento_vaca,
        preco_arroba_vaca=req.preco_arroba_vaca,
        custo=CustoVacaAno(
            pasto_arrendamento=req.custo_pasto_arrendamento,
            sal_mineral=req.custo_sal_mineral,
            sanidade=req.custo_sanidade,
            mao_de_obra=req.custo_mao_de_obra,
            outros=req.custo_outros,
        ),
        anos=req.anos,
    )
    return projetar(entrada)
