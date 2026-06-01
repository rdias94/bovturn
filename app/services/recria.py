"""
BovTurn — Motor de Recria (bezerro → boi magro)
================================================
Compra o bezerro ao desmame (por KG) e leva até boi magro (390-420 kg),
para vender à engorda/confinamento. Arrobas de PESO VIVO (30 kg), pois o
animal é vendido vivo (não abatido).

  custo do animal = peso_entrada × preço_kg_compra
  receita         = peso_saída  × preço_kg_venda
  @ produzidas    = (peso_saída − peso_entrada) / 30
  margem/cab      = receita − custo do animal − custo operacional
"""

from dataclasses import dataclass

ARROBA_VIVO_KG = 30.0


@dataclass
class RecriaEntrada:
    peso_entrada_kg: float = 200.0      # desmame
    peso_saida_kg: float = 400.0        # boi magro
    gmd: float = 0.600                  # kg/dia (recria a pasto)
    preco_kg_compra: float = 13.0       # R$/kg do bezerro (desmame)
    preco_kg_venda: float = 11.5        # R$/kg do boi magro
    # custos operacionais
    consumo_suplemento_pct_pv: float = 0.003   # % do PV em suplemento/dia
    custo_kg_suplemento: float = 2.50
    custo_mdo_cab_mes: float = 12.0
    custo_gastos_prod_cab_mes: float = 18.0
    custo_sanidade_cab: float = 25.0


def calcular(e: RecriaEntrada) -> dict:
    ganho = max(e.peso_saida_kg - e.peso_entrada_kg, 0.0)
    dias = ganho / e.gmd if e.gmd > 0 else 0
    meses = dias / 30.0
    peso_medio = (e.peso_entrada_kg + e.peso_saida_kg) / 2.0

    custo_animal = e.peso_entrada_kg * e.preco_kg_compra
    custo_nutricao = peso_medio * e.consumo_suplemento_pct_pv * e.custo_kg_suplemento * dias
    custo_mdo = e.custo_mdo_cab_mes * meses
    custo_gastos = e.custo_gastos_prod_cab_mes * meses
    custo_op = custo_nutricao + custo_mdo + custo_gastos + e.custo_sanidade_cab
    custo_total = custo_animal + custo_op

    receita = e.peso_saida_kg * e.preco_kg_venda
    margem = receita - custo_total

    arrobas_prod = ganho / ARROBA_VIVO_KG
    custo_arroba_prod = custo_op / arrobas_prod if arrobas_prod > 0 else 0
    custo_kg_produzido = custo_op / ganho if ganho > 0 else 0
    tir_am = ((receita / custo_total) ** (30.0 / dias) - 1) if dias > 0 and custo_total > 0 else 0
    # relação de troca: kg de bezerro comprado por kg de magro vendido
    relacao_compra_venda = e.preco_kg_compra / e.preco_kg_venda if e.preco_kg_venda > 0 else 0

    return {
        "dias": round(dias),
        "meses": round(meses, 1),
        "ganho_kg": round(ganho, 1),
        "gmd": e.gmd,
        "arrobas_produzidas": round(arrobas_prod, 2),
        "arroba_entrada": round(e.peso_entrada_kg / ARROBA_VIVO_KG, 2),
        "arroba_saida": round(e.peso_saida_kg / ARROBA_VIVO_KG, 2),
        "custo_animal": round(custo_animal, 2),
        "custo_operacional": round(custo_op, 2),
        "custo_total": round(custo_total, 2),
        "receita": round(receita, 2),
        "margem_cab": round(margem, 2),
        "custo_arroba_produzida": round(custo_arroba_prod, 2),
        "custo_kg_produzido": round(custo_kg_produzido, 2),
        "relacao_compra_venda": round(relacao_compra_venda, 2),
        "tir_am_pct": round(tir_am * 100, 2),
        "viavel": margem > 0,
        "semaforo": "🟢" if margem > 0 else "🔴",
    }
