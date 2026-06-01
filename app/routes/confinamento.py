"""
BovTurn — Módulo de Confinamento
=================================
Motor próprio de cenários de confinamento (cálculo do zero).

Fórmulas (matemática padrão de confinamento):
  custo_da_@_produzida = diária × 15 ÷ ganho_carcaça_kg_dia   (15 kg carcaça = 1@)
  @ produzidas         = dias × ganho_carcaça ÷ 15
  @ final              = @ entrada + @ produzidas
  custo_total          = custo_animal + dias × diária + custos_fixos
  receita              = @ final × preço_venda
  margem/cab           = receita − custo_total
  preço_equilíbrio     = custo_total ÷ @ final
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

ARROBA_KG = 15.0


class EntradaConfinamento(BaseModel):
    diaria: float = Field(..., gt=0, description="Custo da diária (alim.+operacional) R$/dia")
    ganho_carcaca: float = Field(..., gt=0, description="Ganho de carcaça kg/dia")
    preco_venda: float = Field(..., gt=0, description="Preço de venda R$/@")
    custo_animal: float = Field(..., ge=0, description="Custo do animal R$/cabeça")
    dias: int = Field(100, gt=0, description="Dias de cocho")
    arroba_entrada: float = Field(12.0, ge=0, description="@ de carcaça na entrada")
    custos_fixos_cab: float = Field(0.0, ge=0, description="Sanidade/fixos R$/cab")


def _calcular(e: EntradaConfinamento) -> dict:
    arrobas_prod = e.dias * e.ganho_carcaca / ARROBA_KG
    arroba_final = e.arroba_entrada + arrobas_prod
    custo_alim = e.dias * e.diaria
    custo_total = e.custo_animal + custo_alim + e.custos_fixos_cab
    receita = arroba_final * e.preco_venda
    margem = receita - custo_total
    custo_arroba = e.diaria * ARROBA_KG / e.ganho_carcaca
    preco_eq = custo_total / arroba_final if arroba_final else 0
    # custo máximo do animal que ainda fecha no zero (para o preço informado)
    custo_animal_max = receita - custo_alim - e.custos_fixos_cab
    return {
        "custo_arroba_produzida": round(custo_arroba, 2),
        "arrobas_produzidas": round(arrobas_prod, 2),
        "arroba_final": round(arroba_final, 2),
        "custo_alimentacao": round(custo_alim, 2),
        "custo_total": round(custo_total, 2),
        "receita": round(receita, 2),
        "margem_cab": round(margem, 2),
        "preco_equilibrio": round(preco_eq, 2),
        "custo_animal_max_viavel": round(custo_animal_max, 2),
        "viavel": margem > 0,
        "semaforo": "🟢" if margem > 0 else "🔴",
    }


@router.post("/calcular")
def calcular(entrada: EntradaConfinamento):
    """Calcula um cenário pontual de confinamento."""
    return {"sucesso": True, "entrada": entrada.model_dump(), "resultado": _calcular(entrada)}


class FaixaMatriz(BaseModel):
    ganho_min: float = 0.700
    ganho_max: float = 1.500
    ganho_passo: float = 0.050
    diaria_min: float = 14.00
    diaria_max: float = 17.00
    diaria_passo: float = 0.25


@router.post("/matriz")
def matriz(f: FaixaMatriz):
    """Gera a matriz custo-da-@ produzida (ganho de carcaça × custo da diária)."""
    def faixa(ini, fim, passo):
        vals, v = [], ini
        while v <= fim + 1e-9:
            vals.append(round(v, 4))
            v += passo
        return vals

    ganhos = faixa(f.ganho_min, f.ganho_max, f.ganho_passo)
    diarias = faixa(f.diaria_min, f.diaria_max, f.diaria_passo)
    linhas = []
    for g in ganhos:
        linhas.append({
            "ganho_carcaca": g,
            "custos": [round(d * ARROBA_KG / g, 0) for d in diarias],
        })
    return {"diarias": diarias, "ganhos": ganhos, "linhas": linhas}
