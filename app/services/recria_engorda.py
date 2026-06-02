"""
BovTurn — Motor de Ciclo Completo (Recria + Engorda juntos)
===========================================================
O giro inteiro num cálculo só: compra o BEZERRO ao desmame (por kg),
recria a PASTO (com GMD SAZONAL águas/seca) até o boi magro e termina
a engorda a PASTO ou em CONFINAMENTO, vendendo o boi gordo por @ de carcaça.

Calibrado na planilha real do Riésley ("REBANHO (2)" — comparativo de
planos nutricionais), que compara três intensidades:
    Extensivo  (~36 meses): só pasto, GMD global ~0,41 → custo @ ~R$133
    Intermediário (~24 m) : pasto + acabamento leve, GMD ~0,60 → ~R$112  ← melhor
    Intensivo  (~18 meses): pasto + confinamento, GMD ~0,73 → ~R$155

Estrutura de fases:
  RECRIA  (pasto): peso_entrada → peso_transição.
      GMD efetivo = %águas·GMD_águas + (1−%águas)·GMD_seca  (sazonalidade real)
  ENGORDA: peso_transição → peso_final.
      modo "pasto"        → GMD moderado, custo R$/cab/mês
      modo "confinamento" → GMD alto, custo da dieta derivado do MILHO

Custo da @ produzida = custo OPERACIONAL ÷ @ de carcaça produzidas no ciclo
(exclui a compra do bezerro, como na planilha). Também reporta o custo total,
lucro/@, lucro/cab, GMD global, TIR a.m. e o desembolso estratificado.
"""

from dataclasses import dataclass

ARROBA_CARCACA_KG = 15.0


@dataclass
class CicloEntrada:
    # --- Compra do bezerro (desmame) ---
    peso_entrada_kg: float = 220.0
    preco_kg_bezerro: float = 13.0          # R$/kg vivo na compra
    rc_entrada: float = 50.0                # rendimento de carcaça do bezerro (%)

    # --- Recria a pasto: entrada → transição ---
    peso_transicao_kg: float = 380.0
    gmd_aguas: float = 0.700                # GMD período das águas (out–abr)
    gmd_seca: float = 0.350                 # GMD período da seca (mai–set)
    pct_periodo_aguas: float = 0.50         # fração do ciclo de recria em águas
    custo_pasto_recria_cab_mes: float = 15.0
    custo_suplemento_recria_cab_mes: float = 25.0
    custo_mdo_cab_mes: float = 10.0
    custo_sanidade_cab_ano: float = 60.0

    # --- Engorda/terminação: transição → final ---
    modo_engorda: str = "pasto"             # "pasto" | "confinamento"
    peso_final_kg: float = 540.0
    rc_final: float = 53.0                  # rendimento de carcaça no abate (%)
    arroba_abate_alvo: float = 0.0          # se >0, define peso_final = @·15/rc

    # engorda a PASTO
    gmd_engorda_pasto: float = 0.800
    custo_engorda_pasto_cab_mes: float = 55.0   # pasto melhorado + suplemento de terminação

    # engorda em CONFINAMENTO (dieta derivada do milho)
    gmd_confinamento: float = 1.500
    consumo_pct_pv_conf: float = 2.3
    preco_saca_milho: float = 65.0
    pct_milho_dieta: float = 0.56
    custo_ms_outros: float = 0.86
    diaria_operacional_conf: float = 1.60

    # --- Venda ---
    preco_venda_arroba: float = 349.7       # R$/@ carcaça (CEPEA boi gordo)


def _custo_kg_ms(e: CicloEntrada) -> float:
    milho_kg_ms = e.preco_saca_milho / 60.0 / 0.87
    return e.pct_milho_dieta * milho_kg_ms + (1 - e.pct_milho_dieta) * e.custo_ms_outros


def calcular_ciclo(e: CicloEntrada) -> dict:
    rc_ent = e.rc_entrada / 100.0
    rc_fim = e.rc_final / 100.0

    # peso final pode vir de uma @ de abate alvo
    peso_final = e.peso_final_kg
    if e.arroba_abate_alvo and e.arroba_abate_alvo > 0:
        peso_final = e.arroba_abate_alvo * ARROBA_CARCACA_KG / rc_fim

    # ---------- FASE RECRIA (pasto, GMD sazonal) ----------
    ganho_recria = max(e.peso_transicao_kg - e.peso_entrada_kg, 0.0)
    gmd_recria = (e.pct_periodo_aguas * e.gmd_aguas
                  + (1 - e.pct_periodo_aguas) * e.gmd_seca)
    dias_recria = ganho_recria / gmd_recria if gmd_recria > 0 else 0
    meses_recria = dias_recria / 30.0
    custo_recria = (
        (e.custo_pasto_recria_cab_mes + e.custo_suplemento_recria_cab_mes
         + e.custo_mdo_cab_mes) * meses_recria
        + e.custo_sanidade_cab_ano * (meses_recria / 12.0)
    )

    # ---------- FASE ENGORDA (pasto OU confinamento) ----------
    ganho_engorda = max(peso_final - e.peso_transicao_kg, 0.0)
    if e.modo_engorda == "confinamento":
        gmd_engorda = e.gmd_confinamento
        dias_engorda = ganho_engorda / gmd_engorda if gmd_engorda > 0 else 0
        peso_medio_eng = (e.peso_transicao_kg + peso_final) / 2.0
        cms_dia = peso_medio_eng * (e.consumo_pct_pv_conf / 100.0)
        custo_kg_ms = _custo_kg_ms(e)
        custo_alimentar = cms_dia * custo_kg_ms * dias_engorda
        custo_engorda = custo_alimentar + e.diaria_operacional_conf * dias_engorda
        detalhe_engorda = {
            "cms_dia": round(cms_dia, 2),
            "custo_kg_ms": round(custo_kg_ms, 4),
            "custo_alimentar": round(custo_alimentar, 2),
        }
    else:
        gmd_engorda = e.gmd_engorda_pasto
        dias_engorda = ganho_engorda / gmd_engorda if gmd_engorda > 0 else 0
        meses_engorda = dias_engorda / 30.0
        custo_engorda = (e.custo_engorda_pasto_cab_mes + e.custo_mdo_cab_mes) * meses_engorda
        detalhe_engorda = {}
    meses_engorda = dias_engorda / 30.0

    # ---------- TOTAIS DO CICLO ----------
    dias_total = dias_recria + dias_engorda
    meses_total = dias_total / 30.0
    ganho_total = max(peso_final - e.peso_entrada_kg, 0.0)
    gmd_global = ganho_total / dias_total if dias_total > 0 else 0

    custo_animal = e.peso_entrada_kg * e.preco_kg_bezerro
    custo_op = custo_recria + custo_engorda
    custo_total = custo_animal + custo_op

    carcaca_entrada = e.peso_entrada_kg * rc_ent
    carcaca_final = peso_final * rc_fim
    arroba_entrada = carcaca_entrada / ARROBA_CARCACA_KG
    arroba_final = carcaca_final / ARROBA_CARCACA_KG
    arrobas_produzidas = max(arroba_final - arroba_entrada, 0.01)

    receita = arroba_final * e.preco_venda_arroba
    lucro_cab = receita - custo_total

    custo_arroba_produzida = custo_op / arrobas_produzidas      # operacional (como na planilha)
    custo_total_arroba = custo_total / arroba_final if arroba_final > 0 else 0
    lucro_arroba = lucro_cab / arrobas_produzidas
    tir_am = ((receita / custo_total) ** (30.0 / dias_total) - 1) if dias_total > 0 and custo_total > 0 else 0

    # desembolso estratificado (R$/cab no ciclo)
    desembolso = {
        "bezerro": round(custo_animal, 2),
        "recria": round(custo_recria, 2),
        "engorda": round(custo_engorda, 2),
    }
    total_desemb = custo_total or 1
    desembolso_pct = {k: round(v / total_desemb * 100, 1) for k, v in desembolso.items()}

    return {
        "modo_engorda": e.modo_engorda,
        "peso_entrada_kg": round(e.peso_entrada_kg, 1),
        "peso_transicao_kg": round(e.peso_transicao_kg, 1),
        "peso_final_kg": round(peso_final, 1),
        "ganho_total_kg": round(ganho_total, 1),
        # tempos
        "dias_recria": round(dias_recria),
        "dias_engorda": round(dias_engorda),
        "dias_total": round(dias_total),
        "meses_recria": round(meses_recria, 1),
        "meses_engorda": round(meses_engorda, 1),
        "meses_total": round(meses_total, 1),
        # ganhos
        "gmd_recria": round(gmd_recria, 3),
        "gmd_engorda": round(gmd_engorda, 3),
        "gmd_global": round(gmd_global, 3),
        # arrobas
        "arroba_entrada": round(arroba_entrada, 2),
        "arroba_final": round(arroba_final, 2),
        "arrobas_produzidas": round(arrobas_produzidas, 2),
        "rc_entrada": e.rc_entrada,
        "rc_final": e.rc_final,
        # financeiro
        "custo_animal": round(custo_animal, 2),
        "custo_recria": round(custo_recria, 2),
        "custo_engorda": round(custo_engorda, 2),
        "custo_operacional": round(custo_op, 2),
        "custo_total": round(custo_total, 2),
        "receita": round(receita, 2),
        "lucro_cab": round(lucro_cab, 2),
        "lucro_arroba": round(lucro_arroba, 2),
        "custo_arroba_produzida": round(custo_arroba_produzida, 2),
        "custo_total_arroba": round(custo_total_arroba, 2),
        "tir_am_pct": round(tir_am * 100, 2),
        "desembolso": desembolso,
        "desembolso_pct": desembolso_pct,
        "detalhe_engorda": detalhe_engorda,
        "viavel": lucro_cab > 0,
        "semaforo": "🟢" if lucro_cab > 0 else "🔴",
    }


# Três intensidades de referência (espelham a planilha do Riésley).
# Mantêm a mesma compra/venda e só variam a estratégia da recria+engorda.
INTENSIDADES = [
    {
        "nome": "Extensivo (só pasto)", "modo_engorda": "pasto",
        "gmd_aguas": 0.550, "gmd_seca": 0.250,
        "gmd_engorda_pasto": 0.500, "custo_engorda_pasto_cab_mes": 35.0,
    },
    {
        "nome": "Intermediário (pasto + acabamento)", "modo_engorda": "pasto",
        "gmd_aguas": 0.700, "gmd_seca": 0.400,
        "gmd_engorda_pasto": 0.800, "custo_engorda_pasto_cab_mes": 55.0,
    },
    {
        "nome": "Intensivo (confinamento)", "modo_engorda": "confinamento",
        "gmd_aguas": 0.800, "gmd_seca": 0.500,
        "gmd_confinamento": 1.500,
    },
]


def comparar_intensidades(base: CicloEntrada) -> list[dict]:
    """Roda os três níveis de intensidade com a mesma compra/venda/pesos,
    para comparar custo da @ produzida × GMD global × tempo × lucro."""
    saida = []
    for cfg in INTENSIDADES:
        e = CicloEntrada(**{**base.__dict__})
        e.modo_engorda = cfg["modo_engorda"]
        e.gmd_aguas = cfg["gmd_aguas"]
        e.gmd_seca = cfg["gmd_seca"]
        if "gmd_engorda_pasto" in cfg:
            e.gmd_engorda_pasto = cfg["gmd_engorda_pasto"]
        if "custo_engorda_pasto_cab_mes" in cfg:
            e.custo_engorda_pasto_cab_mes = cfg["custo_engorda_pasto_cab_mes"]
        if "gmd_confinamento" in cfg:
            e.gmd_confinamento = cfg["gmd_confinamento"]
        r = calcular_ciclo(e)
        saida.append({
            "nome": cfg["nome"],
            "modo_engorda": r["modo_engorda"],
            "meses_total": r["meses_total"],
            "gmd_global": r["gmd_global"],
            "custo_arroba_produzida": r["custo_arroba_produzida"],
            "lucro_cab": r["lucro_cab"],
            "lucro_arroba": r["lucro_arroba"],
            "tir_am_pct": r["tir_am_pct"],
            "arrobas_produzidas": r["arrobas_produzidas"],
        })
    # melhor = maior lucro/@ (ou menor custo @) entre os viáveis
    melhor = min(range(len(saida)), key=lambda i: saida[i]["custo_arroba_produzida"])
    for i, s in enumerate(saida):
        s["melhor"] = (i == melhor)
    return saida
