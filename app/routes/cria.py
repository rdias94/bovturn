"""
BovTurn — Endpoint de Cria (evolução de rebanho)
POST /api/cria → projeção ano a ano + custo do bezerro + lucro/cabeça.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.cria import CriaEntrada, CustoVacaAno, projetar

router = APIRouter()


class CriaRequest(BaseModel):
    vacas: int = Field(1000, ge=0)
    novilhas: int = Field(250, ge=0)
    bezerras_retidas: int = Field(0, ge=0)
    touros: int = Field(40, ge=0)

    taxa_desmame: float = 0.80
    mortalidade_bezerro: float = 0.03
    taxa_descarte_vacas: float = 0.16

    peso_desmame_kg: float = 200.0
    preco_kg_bezerro: float = 13.0
    preco_kg_bezerra: float = 11.0
    peso_vaca_descarte_kg: float = 450.0
    rendimento_vaca: float = 0.50
    preco_arroba_vaca: float = 280.0

    # Custo da vaca/ano por componentes (R$/vaca/ano)
    custo_pasto_arrendamento: float = 0.0
    custo_sal_mineral: float = 0.0
    custo_sanidade: float = 0.0
    custo_mao_de_obra: float = 0.0
    custo_outros: float = 0.0

    anos: int = Field(5, ge=1, le=15)


@router.post("/")
def cria(req: CriaRequest):
    entrada = CriaEntrada(
        vacas=req.vacas, novilhas=req.novilhas, bezerras_retidas=req.bezerras_retidas,
        touros=req.touros,
        taxa_desmame=req.taxa_desmame, mortalidade_bezerro=req.mortalidade_bezerro,
        taxa_descarte_vacas=req.taxa_descarte_vacas,
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
