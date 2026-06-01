"""
BovTurn — Endpoint de Análise Estatística
=========================================
POST /api/analise → relatório completo com varredura GMD×compra×venda,
métricas financeiras, benchmarks e curvas de sensibilidade.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.services.motor_cenarios import (
    EntradaGiro, SistemaHidrico, SistemaProducao, Sexo,
)
from app.services.analise import analisar

router = APIRouter()


class AnaliseRequest(BaseModel):
    peso_entrada_kg: float = Field(..., gt=0)
    # preço de compra — informe um
    preco_compra_kg: Optional[float] = None
    preco_compra_arroba: Optional[float] = None
    valor_animal_mercado: Optional[float] = None
    preco_venda_arroba: float = Field(..., gt=0)

    dias_giro: int = 120
    gmd_esperado: float = 0.0
    peso_saida_kg: Optional[float] = None

    area_ha: float = 100.0
    lotacao_ua_ha: float = 1.2

    sistema_hidrico: str = "sequeiro"
    sistema_producao: str = "engorda"
    sexo: str = "macho"
    raca: str = "nelore"

    custo_mdo_cab_mes: float = 20.0
    custo_gastos_prod_cab_mes: float = 20.0
    custo_arrendamento_ua_mes: float = 0.0
    custo_sanidade_cab_giro: float = 16.27
    custo_kg_suplemento: float = 3.50
    consumo_suplemento_pct_pv: float = 0.003

    frete_cab: float = 0.0
    comissao_pct: float = 0.0

    # parâmetros de mercado / varredura
    preco_saca_milho: float = 65.0
    amplitude_gmd: float = 0.20
    amplitude_compra: float = 0.15
    amplitude_venda: float = 0.15


@router.post("/")
def analise(req: AnaliseRequest):
    if not any([req.preco_compra_kg, req.preco_compra_arroba, req.valor_animal_mercado]):
        raise HTTPException(422, "Informe um preço de compra (kg, @ ou cab).")
    try:
        entrada = EntradaGiro(
            peso_entrada_kg=req.peso_entrada_kg,
            preco_compra_kg=req.preco_compra_kg,
            preco_compra_arroba=req.preco_compra_arroba,
            valor_animal_mercado=req.valor_animal_mercado,
            preco_venda_arroba=req.preco_venda_arroba,
            dias_giro=req.dias_giro,
            gmd_esperado=req.gmd_esperado,
            peso_saida_kg=req.peso_saida_kg,
            area_ha=req.area_ha,
            lotacao_ua_ha=req.lotacao_ua_ha,
            sistema_hidrico=SistemaHidrico(req.sistema_hidrico),
            sistema_producao=SistemaProducao(req.sistema_producao),
            sexo=Sexo(req.sexo),
            raca=req.raca,
            custo_mdo_cab_mes=req.custo_mdo_cab_mes,
            custo_gastos_prod_cab_mes=req.custo_gastos_prod_cab_mes,
            custo_arrendamento_ua_mes=req.custo_arrendamento_ua_mes,
            custo_sanidade_cab_giro=req.custo_sanidade_cab_giro,
            custo_kg_suplemento=req.custo_kg_suplemento,
            consumo_suplemento_pct_pv=req.consumo_suplemento_pct_pv,
            frete_cab=req.frete_cab,
            comissao_pct=req.comissao_pct,
        )
        return analisar(
            entrada,
            preco_saca_milho=req.preco_saca_milho,
            amplitude_gmd=req.amplitude_gmd,
            amplitude_compra=req.amplitude_compra,
            amplitude_venda=req.amplitude_venda,
        )
    except ValueError as e:
        raise HTTPException(422, f"Dado inválido: {e}")
