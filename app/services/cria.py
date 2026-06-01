"""
BovTurn — Motor de Cria (rebanho + reprodutivo)
================================================
Rebanho total; quem produz bezerro são as FÊMEAS EXPOSTAS na estação de monta.
Índices reprodutivos completos com benchmarks. Custo da vaca por componentes.
Bezerro vendido por KG ao desmame. Projeção ano a ano (rebanho estável/crescente,
sem oscilação artificial).

Cadeia reprodutiva:
  expostas → prenhez% → (− perda gestacional) natalidade → (− mortalidade) desmame
  taxa_desmame = prenhez × (1−perda) × (1−mort_bezerro)

Benchmarks (literatura — ajustáveis):
  prenhez ≥85% bom · 75–85 ok · <75 ruim
  desmame ≥80% bom · 70–80 ok · <70 ruim
  IEP ≤14 meses bom · mortalidade bezerro ≤4% bom
"""

from dataclasses import dataclass, field


@dataclass
class CustoVacaAno:
    pasto_arrendamento: float = 0.0
    sal_mineral: float = 0.0
    sanidade: float = 0.0
    mao_de_obra: float = 0.0
    outros: float = 0.0

    @property
    def total(self) -> float:
        return (self.pasto_arrendamento + self.sal_mineral + self.sanidade
                + self.mao_de_obra + self.outros)


@dataclass
class CriaEntrada:
    matrizes: int = 1000              # vacas + novilhas expostas na estação de monta
    touros: int = 40

    # Índices reprodutivos
    taxa_prenhez: float = 0.85
    perda_gestacional: float = 0.03    # aborto/perda entre prenhez e parto
    mortalidade_bezerro: float = 0.04  # nascimento ao desmame
    idade_primeiro_parto_meses: int = 36
    taxa_descarte_vacas: float = 0.16
    taxa_crescimento_rebanho: float = 0.0   # 0 = manter rebanho estável
    proporcao_machos: float = 0.50

    # Pesos e preços
    peso_desmame_kg: float = 210.0
    preco_kg_bezerro: float = 13.5
    preco_kg_bezerra: float = 11.5
    peso_vaca_descarte_kg: float = 450.0
    rendimento_vaca: float = 0.50
    preco_arroba_vaca: float = 280.0

    custo: CustoVacaAno = field(default_factory=CustoVacaAno)
    anos: int = 5


def _verdito(valor, bom, ok, maior=True):
    if maior:
        return "bom" if valor >= bom else ("atencao" if valor >= ok else "ruim")
    return "bom" if valor <= bom else ("atencao" if valor <= ok else "ruim")


def projetar(e: CriaEntrada) -> dict:
    custo_vaca = e.custo.total
    taxa_natalidade = e.taxa_prenhez * (1 - e.perda_gestacional)
    taxa_desmame = taxa_natalidade * (1 - e.mortalidade_bezerro)
    iep_meses = 12.0 / e.taxa_prenhez if e.taxa_prenhez > 0 else 0  # intervalo entre partos aprox.

    matrizes = float(e.matrizes)
    anos_proj = []
    for ano in range(1, e.anos + 1):
        expostas = matrizes
        desmamados = expostas * taxa_desmame
        machos = desmamados * e.proporcao_machos
        femeas = desmamados * (1 - e.proporcao_machos)

        descartadas = matrizes * e.taxa_descarte_vacas
        reposicao = descartadas + matrizes * e.taxa_crescimento_rebanho
        reposicao = min(reposicao, femeas)
        femeas_vendidas = max(femeas - reposicao, 0)

        custo_total = matrizes * custo_vaca
        receita_machos = machos * e.peso_desmame_kg * e.preco_kg_bezerro
        receita_femeas = femeas_vendidas * e.peso_desmame_kg * e.preco_kg_bezerra
        arrobas_vaca = e.peso_vaca_descarte_kg * e.rendimento_vaca / 15.0
        receita_descarte = descartadas * arrobas_vaca * e.preco_arroba_vaca
        receita_total = receita_machos + receita_femeas + receita_descarte

        custo_por_bezerro = custo_total / desmamados if desmamados else 0
        preco_venda_bezerro = e.peso_desmame_kg * e.preco_kg_bezerro
        lucro_por_bezerro = preco_venda_bezerro - custo_por_bezerro
        lucro_total = receita_total - custo_total
        kg_desmamado_por_vaca = desmamados * e.peso_desmame_kg / expostas if expostas else 0
        desfrute = (machos + femeas_vendidas + descartadas) / matrizes if matrizes else 0

        anos_proj.append({
            "ano": ano,
            "matrizes": round(matrizes),
            "expostas": round(expostas),
            "bezerros_desmamados": round(desmamados),
            "machos_vendidos": round(machos),
            "femeas_vendidas": round(femeas_vendidas),
            "vacas_descartadas": round(descartadas),
            "custo_total": round(custo_total, 2),
            "receita_total": round(receita_total, 2),
            "lucro_total": round(lucro_total, 2),
            "custo_por_bezerro": round(custo_por_bezerro, 2),
            "preco_venda_bezerro": round(preco_venda_bezerro, 2),
            "lucro_por_bezerro": round(lucro_por_bezerro, 2),
            "lucro_por_vaca_exposta": round(lucro_total / expostas, 2) if expostas else 0,
            "kg_desmamado_por_vaca": round(kg_desmamado_por_vaca, 1),
            "desfrute_pct": round(desfrute * 100, 1),
        })
        matrizes = matrizes * (1 + e.taxa_crescimento_rebanho)

    base = anos_proj[0]
    return {
        "anos": anos_proj,
        "reprodutivo": {
            "taxa_prenhez_pct": round(e.taxa_prenhez * 100, 1),
            "taxa_prenhez_verdito": _verdito(e.taxa_prenhez, 0.85, 0.75),
            "taxa_natalidade_pct": round(taxa_natalidade * 100, 1),
            "taxa_desmame_pct": round(taxa_desmame * 100, 1),
            "taxa_desmame_verdito": _verdito(taxa_desmame, 0.80, 0.70),
            "mortalidade_bezerro_pct": round(e.mortalidade_bezerro * 100, 1),
            "mortalidade_verdito": _verdito(e.mortalidade_bezerro, 0.04, 0.07, maior=False),
            "iep_meses": round(iep_meses, 1),
            "iep_verdito": _verdito(iep_meses, 14, 16, maior=False),
            "idade_primeiro_parto_meses": e.idade_primeiro_parto_meses,
            "ipp_verdito": _verdito(e.idade_primeiro_parto_meses, 30, 36, maior=False),
        },
        "resumo": {
            "custo_vaca_ano": round(custo_vaca, 2),
            "custo_por_bezerro": base["custo_por_bezerro"],
            "preco_venda_bezerro": base["preco_venda_bezerro"],
            "lucro_por_bezerro": base["lucro_por_bezerro"],
            "lucro_por_vaca_exposta": base["lucro_por_vaca_exposta"],
            "kg_desmamado_por_vaca": base["kg_desmamado_por_vaca"],
            "desfrute_pct": base["desfrute_pct"],
            "viavel": base["lucro_por_bezerro"] > 0,
            "semaforo": "🟢" if base["lucro_por_bezerro"] > 0 else "🔴",
            "rebanho_inicial": base["matrizes"],
            "rebanho_final": anos_proj[-1]["matrizes"],
        },
        "componentes_custo": {
            "pasto_arrendamento": e.custo.pasto_arrendamento,
            "sal_mineral": e.custo.sal_mineral,
            "sanidade": e.custo.sanidade,
            "mao_de_obra": e.custo.mao_de_obra,
            "outros": e.custo.outros,
        },
    }
