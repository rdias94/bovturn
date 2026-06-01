"""
BovTurn — Motor de Análise Estatística
=======================================
Pega um giro-base e VARRE GMD × preço de compra × preço de venda,
gerando um relatório completo com:
  - métricas financeiras (TIR a.m., desembolso/@, desembolso/cab/mês,
    ágio do bezerro, relação de troca @/saca de milho, perfil de desembolso)
  - benchmarks (o que é bom/atenção/ruim) por métrica
  - visão estatística: em quantos % dos cenários deu bom × ruim
  - curvas de sensibilidade (margem por GMD, por compra, por venda)

Tudo calculado em cima do motor de cenários existente.
"""

from dataclasses import dataclass, field, replace
from typing import Optional

from app.services.motor_cenarios import (
    EntradaGiro, TipoCenario, calcular_cenario,
)

ARROBA_KG = 30.0  # peso vivo por arroba (padrão do motor de pasto)


# ── Benchmarks padrão (ajustáveis) ────────────────────────────
BENCHMARKS = {
    "tir_am":            {"bom": 0.020, "ok": 0.010, "dir": "maior"},   # /mês
    "lucratividade":     {"bom": 0.15,  "ok": 0.05,  "dir": "maior"},
    "desembolso_cab_mes": {"bom": 70,   "ok": 100,   "dir": "menor"},   # R$
    "agio_bezerro_pct":  {"bom": 0.20,  "ok": 0.40,  "dir": "menor"},   # fração
    "relacao_troca_milho": {"bom": 3.0, "ok": 2.0,   "dir": "maior"},   # sacas/@
}


def _verdito(metrica: str, valor: float) -> str:
    """Classifica uma métrica em bom/atenção/ruim conforme benchmark."""
    b = BENCHMARKS.get(metrica)
    if not b:
        return "neutro"
    if b["dir"] == "maior":
        if valor >= b["bom"]:
            return "bom"
        if valor >= b["ok"]:
            return "atencao"
        return "ruim"
    else:  # menor é melhor
        if valor <= b["bom"]:
            return "bom"
        if valor <= b["ok"]:
            return "atencao"
        return "ruim"


def _tir_am(receita_cab: float, custo_total_cab: float, dias: int) -> float:
    """TIR ao mês: retorno mensal composto do capital total imobilizado."""
    if custo_total_cab <= 0 or dias <= 0:
        return 0.0
    razao = receita_cab / custo_total_cab
    if razao <= 0:
        return -1.0
    return razao ** (30.0 / dias) - 1.0


def _metricas_extra(entrada: EntradaGiro, r, preco_saca_milho: float) -> dict:
    """Métricas financeiras adicionais a partir de um ResultadoCenario."""
    meses = entrada.dias_giro / 30.0
    receita_cab = r.peso_saida_arroba * r.preco_venda_arroba
    tir = _tir_am(receita_cab, r.custo_total_cab, entrada.dias_giro)

    # Ágio do bezerro: quanto a mais se paga na @ de entrada vs @ de venda
    preco_arroba_compra = entrada.arroba_compra
    agio = ((preco_arroba_compra - r.preco_venda_arroba) / r.preco_venda_arroba
            if r.preco_venda_arroba > 0 else 0.0)

    # Relação de troca: quantas sacas de milho 1 @ de boi compra
    rel_troca = r.preco_venda_arroba / preco_saca_milho if preco_saca_milho > 0 else 0.0

    desembolso_cab_mes = r.custo_operacional_cab / meses if meses > 0 else 0.0
    arrobas_prod = max(r.peso_saida_arroba - (entrada.peso_entrada_kg / ARROBA_KG), 0.001)
    desembolso_por_arroba = r.custo_operacional_cab / arrobas_prod

    # Perfil de desembolso (% do desembolso total por cabeça)
    total = r.custo_total_cab
    perfil = {
        "compra_animal": r.custo_compra_cab,
        "nutricao": r.custo_nutricao_cab,
        "mao_de_obra": r.custo_mdo_cab,
        "gastos_producao": r.custo_gastos_prod_cab,
        "arrendamento": r.custo_arrendamento_cab,
        "sanidade": r.custo_sanidade_cab,
    }
    perfil_pct = {k: round(v / total * 100, 1) if total else 0 for k, v in perfil.items()}

    return {
        "tir_am": round(tir, 4),
        "tir_am_pct": round(tir * 100, 2),
        "tir_am_verdito": _verdito("tir_am", tir),
        "lucratividade_pct": r.lucratividade,
        "lucratividade_verdito": _verdito("lucratividade", r.lucratividade / 100),
        "desembolso_cab_mes": round(desembolso_cab_mes, 2),
        "desembolso_cab_mes_verdito": _verdito("desembolso_cab_mes", desembolso_cab_mes),
        "desembolso_por_arroba": round(desembolso_por_arroba, 2),
        "agio_bezerro_pct": round(agio * 100, 2),
        "agio_bezerro_verdito": _verdito("agio_bezerro_pct", agio),
        "relacao_troca_milho": round(rel_troca, 2),
        "relacao_troca_verdito": _verdito("relacao_troca_milho", rel_troca),
        "margem_cab": r.margem_cab,
        "receita_cab": round(receita_cab, 2),
        "perfil_desembolso": {k: round(v, 2) for k, v in perfil.items()},
        "perfil_desembolso_pct": perfil_pct,
    }


def _faixa_fatores(amplitude: float, passos: int) -> list[float]:
    """Gera fatores simétricos em torno de 1.0 (ex: 0.8 ... 1.2)."""
    if passos < 2:
        return [1.0]
    inicio = 1.0 - amplitude
    fim = 1.0 + amplitude
    step = (fim - inicio) / (passos - 1)
    return [round(inicio + i * step, 4) for i in range(passos)]


def analisar(entrada: EntradaGiro, preco_saca_milho: float = 65.0,
             amplitude_gmd: float = 0.20,
             amplitude_compra: float = 0.15,
             amplitude_venda: float = 0.15) -> dict:
    """Relatório completo: base + métricas + varredura estatística + sensibilidade."""

    # ── 1. Cenário base + métricas ────────────────────────────
    base = calcular_cenario(entrada, TipoCenario.BASE)
    metricas_base = _metricas_extra(entrada, base, preco_saca_milho)

    fatores_gmd = _faixa_fatores(amplitude_gmd, 9)
    fatores_compra = _faixa_fatores(amplitude_compra, 7)
    fatores_venda = _faixa_fatores(amplitude_venda, 7)

    # ── 2. Varredura completa (GMD × compra × venda) ──────────
    n_total = n_bom = n_atencao = n_ruim = 0
    tirs = []
    margens = []
    melhor = None
    pior = None
    preco_compra_arroba_base = entrada.arroba_compra

    for fc in fatores_compra:
        # rebuild entrada com preço de compra escalado (via arroba)
        ent_c = replace(
            entrada,
            preco_compra_kg=None,
            preco_compra_arroba=preco_compra_arroba_base * fc,
            valor_animal_mercado=None,
            peso_saida_kg=None,  # deixa o gmd_esperado mandar
        )
        for fg in fatores_gmd:
            for fv in fatores_venda:
                r = calcular_cenario(ent_c, TipoCenario.BASE,
                                     fator_gmd=fg, fator_preco_venda=fv)
                receita_cab = r.peso_saida_arroba * r.preco_venda_arroba
                tir = _tir_am(receita_cab, r.custo_total_cab, entrada.dias_giro)
                n_total += 1
                tirs.append(tir)
                margens.append(r.margem_cab)
                if r.margem_cab <= 0:
                    n_ruim += 1
                    classe = "ruim"
                elif tir >= BENCHMARKS["tir_am"]["bom"]:
                    n_bom += 1
                    classe = "bom"
                else:
                    n_atencao += 1
                    classe = "atencao"
                ponto = {
                    "fator_gmd": fg, "fator_compra": fc, "fator_venda": fv,
                    "gmd": r.gmd, "margem_cab": r.margem_cab,
                    "tir_am_pct": round(tir * 100, 2), "classe": classe,
                }
                if melhor is None or r.margem_cab > melhor["margem_cab"]:
                    melhor = ponto
                if pior is None or r.margem_cab < pior["margem_cab"]:
                    pior = ponto

    pct = lambda n: round(n / n_total * 100, 1) if n_total else 0

    # ── 3. Sensibilidade 1D (varia uma variável, fixa as outras) ─
    def curva(variavel: str) -> list[dict]:
        pts = []
        fonte = {"gmd": fatores_gmd, "compra": fatores_compra, "venda": fatores_venda}[variavel]
        for f in fonte:
            ent = entrada
            fg = fv = 1.0
            if variavel == "compra":
                ent = replace(entrada, preco_compra_kg=None,
                              preco_compra_arroba=preco_compra_arroba_base * f,
                              valor_animal_mercado=None, peso_saida_kg=None)
            elif variavel == "gmd":
                fg = f
            elif variavel == "venda":
                fv = f
            r = calcular_cenario(ent, TipoCenario.BASE, fator_gmd=fg, fator_preco_venda=fv)
            receita_cab = r.peso_saida_arroba * r.preco_venda_arroba
            tir = _tir_am(receita_cab, r.custo_total_cab, entrada.dias_giro)
            rotulo = {
                "gmd": f"{r.gmd:.2f}",
                "compra": f"R${preco_compra_arroba_base * f:.0f}/@",
                "venda": f"R${entrada.preco_venda_arroba * f:.0f}/@",
            }[variavel]
            pts.append({
                "fator": f, "rotulo": rotulo,
                "margem_cab": r.margem_cab, "tir_am_pct": round(tir * 100, 2),
            })
        return pts

    # ── 4. Histograma de margem/cab ───────────────────────────
    def histograma(valores, n_bins=10):
        if not valores:
            return []
        lo, hi = min(valores), max(valores)
        if hi == lo:
            return [{"faixa": round(lo), "n": len(valores)}]
        w = (hi - lo) / n_bins
        bins = [0] * n_bins
        for v in valores:
            idx = min(int((v - lo) / w), n_bins - 1)
            bins[idx] += 1
        return [{"faixa": round(lo + i * w), "n": bins[i]} for i in range(n_bins)]

    return {
        "base": {
            "gmd": base.gmd,
            "peso_saida_kg": base.peso_saida_kg,
            "preco_venda_arroba": base.preco_venda_arroba,
            "preco_compra_arroba": round(preco_compra_arroba_base, 2),
            "custo_arroba_produzida": base.custo_arroba_produzida,
            "score": base.score_viabilidade,
            "classificacao": base.classificacao_viabilidade,
            "n_animais": base.n_animais,
        },
        "metricas": metricas_base,
        "estatistica": {
            "n_cenarios": n_total,
            "pct_bom": pct(n_bom),
            "pct_atencao": pct(n_atencao),
            "pct_ruim": pct(n_ruim),
            "n_bom": n_bom, "n_atencao": n_atencao, "n_ruim": n_ruim,
            "margem_media": round(sum(margens) / len(margens), 2) if margens else 0,
            "margem_min": round(min(margens), 2) if margens else 0,
            "margem_max": round(max(margens), 2) if margens else 0,
            "tir_media_pct": round(sum(tirs) / len(tirs) * 100, 2) if tirs else 0,
            "melhor": melhor,
            "pior": pior,
        },
        "sensibilidade": {
            "gmd": curva("gmd"),
            "compra": curva("compra"),
            "venda": curva("venda"),
        },
        "histograma_margem": histograma(margens),
        "benchmarks": BENCHMARKS,
        "preco_saca_milho": preco_saca_milho,
    }
