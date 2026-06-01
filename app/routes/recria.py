"""
BovTurn — Endpoint de Recria (bezerro → boi magro)
POST /api/recria/calcular
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.recria import RecriaEntrada, calcular

router = APIRouter()


class RecriaRequest(BaseModel):
    peso_entrada_kg: float = Field(200, gt=0)
    peso_saida_kg: float = Field(400, gt=0)
    gmd: float = Field(0.600, gt=0)
    preco_kg_compra: float = 13.0
    preco_kg_venda: float = 11.5
    consumo_suplemento_pct_pv: float = 0.003
    custo_kg_suplemento: float = 2.50
    custo_mdo_cab_mes: float = 12.0
    custo_gastos_prod_cab_mes: float = 18.0
    custo_sanidade_cab: float = 25.0


@router.post("/calcular")
def calcular_recria(req: RecriaRequest):
    return {"sucesso": True, "resultado": calcular(RecriaEntrada(**req.model_dump()))}
