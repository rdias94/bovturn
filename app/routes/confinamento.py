"""
BovTurn — Módulo de Confinamento (curva de ganho)
=================================================
Motor com CURVA DE GANHO real: o GMD CAI ao longo dos dias de cocho
(curva de Domingues, 2018 → GMD médio ≈ a − b·dias). Por isso o lucro
NÃO cresce indefinidamente — existe um ponto de Lucro Máximo (dias ótimos).

Receita diária = ganho de carcaça do dia × valor da @.
Despesa diária = consumo de MS (kg) × custo do kg de MS + diária operacional.
O consumo (kg/dia) sobe porque o animal fica mais pesado.
Quando a receita gerada/dia < diária → caixa negativo → o lucro acumulado
começa a cair. O motor encontra o dia de Lucro Máximo.

Arrobas em CARCAÇA (15 kg/@). Rendimento de carcaça (RC) converte
peso vivo → carcaça e pode ser informado ou calculado.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

ARROBA_CARCACA_KG = 15.0


class EntradaConfinamento(BaseModel):
    peso_entrada_kg: float = Field(420, gt=0, description="Peso vivo de entrada")
    gmd_inicial: float = Field(1.90, gt=0, description="Ganho de peso vivo no início (kg/dia)")
    decaimento_gmd: float = Field(0.0095, ge=0, description="Queda do GMD por dia de cocho (kg/dia/dia)")
    rendimento_carcaca: float = Field(50.0, gt=0, description="Rendimento de carcaça de entrada (%)")
    rendimento_ganho: float = Field(60.0, gt=0, description="Rendimento de carcaça do GANHO (%) — a engorda rende mais")
    preco_compra_arroba: float = Field(300, gt=0, description="R$/@ carcaça paga na reposição")
    preco_venda_arroba: float = Field(349.7, gt=0, description="R$/@ carcaça na venda (CEPEA boi gordo)")
    # Custo da dieta derivado do MILHO (dieta real ~50% milho na MS)
    preco_saca_milho: float = Field(65.0, gt=0, description="Preço da saca de milho (60 kg)")
    pct_milho_dieta: float = Field(0.50, ge=0, le=1, description="Fração da MS da dieta que é milho")
    custo_ms_outros: float = Field(0.95, ge=0, description="Custo R$/kg MS dos demais ingredientes")
    consumo_pct_pv: float = Field(2.2, gt=0, description="Consumo de MS (% do peso vivo)")
    diaria_operacional: float = Field(1.60, ge=0, description="Diária operacional (R$/cab/dia)")
    dias_max: int = Field(180, gt=0, le=400, description="Horizonte de simulação (dias)")


def _custo_kg_ms(e: "EntradaConfinamento") -> float:
    """Custo do kg de MS da dieta, derivado do preço do milho.
    Milho moído ~87% MS, saca de 60 kg → R$/kg MS = preço_saca / 60 / 0,87."""
    milho_kg_ms = e.preco_saca_milho / 60.0 / 0.87
    return e.pct_milho_dieta * milho_kg_ms + (1 - e.pct_milho_dieta) * e.custo_ms_outros


def _simular(e: EntradaConfinamento) -> dict:
    rc_base = e.rendimento_carcaca / 100.0
    rg = e.rendimento_ganho / 100.0
    custo_kg_ms = _custo_kg_ms(e)
    carcaca_entrada = e.peso_entrada_kg * rc_base
    arroba_entrada = carcaca_entrada / ARROBA_CARCACA_KG
    custo_animal = arroba_entrada * e.preco_compra_arroba
    agio_cab = (e.preco_compra_arroba - e.preco_venda_arroba) * arroba_entrada

    curva = []
    peso_vivo = e.peso_entrada_kg
    custo_acum = custo_animal
    melhor = {"dia": 0, "lucro": -custo_animal}
    breakeven = None

    for dia in range(1, e.dias_max + 1):
        gmd = max(e.gmd_inicial - e.decaimento_gmd * dia, 0.0)
        peso_vivo += gmd
        cms_kg = peso_vivo * (e.consumo_pct_pv / 100.0)
        diaria = cms_kg * custo_kg_ms + e.diaria_operacional
        custo_acum += diaria

        # carcaça = carcaça de entrada + ganho de peso × rendimento do ganho
        ganho_pv = peso_vivo - e.peso_entrada_kg
        carcaca = carcaca_entrada + ganho_pv * rg
        arroba_carc = carcaca / ARROBA_CARCACA_KG
        receita = arroba_carc * e.preco_venda_arroba
        lucro = receita - custo_acum

        if lucro >= 0 and breakeven is None:
            breakeven = dia
        if lucro > melhor["lucro"]:
            melhor = {"dia": dia, "lucro": lucro}

        curva.append({
            "dia": dia,
            "gmd": round(gmd, 3),
            "peso_vivo": round(peso_vivo, 1),
            "rc_atual": round(carcaca / peso_vivo * 100, 1),
            "arroba_carcaca": round(arroba_carc, 2),
            "receita": round(receita, 2),
            "custo_acumulado": round(custo_acum, 2),
            "lucro": round(lucro, 2),
            "diaria": round(diaria, 2),
        })

    return {"curva": curva, "dias_otimos": melhor["dia"],
            "lucro_maximo": round(melhor["lucro"], 2),
            "breakeven_dias": breakeven,
            "custo_animal": round(custo_animal, 2),
            "arroba_entrada": round(arroba_entrada, 2),
            "agio_cab": round(agio_cab, 2)}


@router.post("/calcular")
def calcular(entrada: EntradaConfinamento):
    """Simula a curva de lucro × dias de cocho e acha o ponto ótimo."""
    sim = _simular(entrada)
    otimo = sim["curva"][sim["dias_otimos"] - 1] if sim["dias_otimos"] > 0 else None

    resumo = None
    if otimo:
        dias = sim["dias_otimos"]
        ganho_pv = otimo["peso_vivo"] - entrada.peso_entrada_kg
        gmd_medio = ganho_pv / dias if dias else 0
        arrobas_prod = otimo["arroba_carcaca"] - sim["arroba_entrada"]
        carcaca_prod = arrobas_prod * ARROBA_CARCACA_KG
        ganho_carcaca_medio = carcaca_prod / dias if dias else 0
        custo_op = otimo["custo_acumulado"] - sim["custo_animal"]
        resumo = {
            "dias_otimos": dias,
            "breakeven_dias": sim["breakeven_dias"],
            "lucro_maximo": sim["lucro_maximo"],
            "margem_cab": sim["lucro_maximo"],
            "peso_saida_kg": otimo["peso_vivo"],
            "gmd_medio": round(gmd_medio, 3),
            "ganho_carcaca_medio": round(ganho_carcaca_medio, 3),
            "rendimento_carcaca_entrada": entrada.rendimento_carcaca,
            "rendimento_carcaca_saida": otimo["rc_atual"],
            "arroba_entrada": sim["arroba_entrada"],
            "arroba_saida": otimo["arroba_carcaca"],
            "arrobas_produzidas": round(arrobas_prod, 2),
            "custo_animal": sim["custo_animal"],
            "custo_operacional": round(custo_op, 2),
            "custo_arroba_produzida": round(custo_op / arrobas_prod, 2) if arrobas_prod > 0 else 0,
            "receita": otimo["receita"],
            "agio_cab": sim["agio_cab"],
            "viavel": sim["lucro_maximo"] > 0,
            "semaforo": "🟢" if sim["lucro_maximo"] > 0 else "🔴",
        }

    # amostra a curva (1 ponto a cada 3 dias) para o gráfico
    curva = [p for i, p in enumerate(sim["curva"]) if i % 3 == 0 or p["dia"] == sim["dias_otimos"]]
    return {"sucesso": True, "resumo": resumo, "curva": curva,
            "dias_otimos": sim["dias_otimos"], "breakeven_dias": sim["breakeven_dias"]}


class FaixaMatriz(BaseModel):
    ganho_min: float = 0.700
    ganho_max: float = 1.500
    ganho_passo: float = 0.050
    diaria_min: float = 14.00
    diaria_max: float = 17.00
    diaria_passo: float = 0.25


@router.post("/matriz")
def matriz(f: FaixaMatriz):
    """Matriz de referência: custo da @ produzida = diária × 15 ÷ ganho de carcaça."""
    def faixa(ini, fim, passo):
        vals, v = [], ini
        while v <= fim + 1e-9:
            vals.append(round(v, 4))
            v += passo
        return vals

    ganhos = faixa(f.ganho_min, f.ganho_max, f.ganho_passo)
    diarias = faixa(f.diaria_min, f.diaria_max, f.diaria_passo)
    linhas = [{"ganho_carcaca": g, "custos": [round(d * ARROBA_CARCACA_KG / g, 0) for d in diarias]}
              for g in ganhos]
    return {"diarias": diarias, "ganhos": ganhos, "linhas": linhas}
