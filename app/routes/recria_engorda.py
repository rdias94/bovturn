"""
BovTurn — Endpoint do Ciclo Completo (Recria + Engorda juntos)
POST /api/ciclo/calcular  → giro inteiro bezerro → boi gordo (1 cenário)
POST /api/ciclo/comparar  → 3 intensidades (extensivo/intermediário/intensivo)
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.recria_engorda import CicloEntrada, calcular_ciclo, comparar_intensidades

router = APIRouter()


class CicloRequest(BaseModel):
    peso_entrada_kg: float = Field(220, gt=0)
    preco_kg_bezerro: float = Field(13.0, ge=0)
    rc_entrada: float = Field(50.0, gt=0)

    peso_transicao_kg: float = Field(380, gt=0)
    gmd_aguas: float = Field(0.700, gt=0)
    gmd_seca: float = Field(0.350, gt=0)
    pct_periodo_aguas: float = Field(0.50, ge=0, le=1)
    custo_pasto_recria_cab_mes: float = 15.0
    custo_suplemento_recria_cab_mes: float = 25.0
    custo_mdo_cab_mes: float = 10.0
    custo_sanidade_cab_ano: float = 60.0

    modo_engorda: str = Field("pasto", pattern="^(pasto|confinamento)$")
    peso_final_kg: float = Field(540, gt=0)
    rc_final: float = Field(53.0, gt=0)
    arroba_abate_alvo: float = Field(0.0, ge=0)

    gmd_engorda_pasto: float = Field(0.800, gt=0)
    custo_engorda_pasto_cab_mes: float = 55.0

    gmd_confinamento: float = Field(1.500, gt=0)
    consumo_pct_pv_conf: float = Field(2.3, gt=0)
    preco_saca_milho: float = Field(65.0, gt=0)
    pct_milho_dieta: float = Field(0.56, ge=0, le=1)
    custo_ms_outros: float = Field(0.86, ge=0)
    diaria_operacional_conf: float = Field(1.60, ge=0)

    preco_venda_arroba: float = Field(349.7, gt=0)

    def to_entrada(self) -> CicloEntrada:
        return CicloEntrada(**self.model_dump())


@router.post("/calcular")
def calcular(req: CicloRequest):
    return calcular_ciclo(req.to_entrada())


@router.post("/comparar")
def comparar(req: CicloRequest):
    return {"intensidades": comparar_intensidades(req.to_entrada())}
