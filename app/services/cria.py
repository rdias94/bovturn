"""
BovTurn — Motor de Cria (evolução de rebanho)
==============================================
Olha o REBANHO TOTAL, mas quem produz bezerro são as FÊMEAS EXPOSTAS
na estação de monta. Projeta ano a ano com reposição e descarte.

Custo da vaca/ano: por COMPONENTES → total.
Bezerro: vendido por KG ao desmame. Lucro/cab = preço de venda − custo do bezerro.

Índices de referência (literatura — ajustáveis):
  prenhez 85-90% (bom), natalidade ~82%, desmame ~80% das expostas,
  período de serviço 75-80 dias, descarte de vacas ~15-18%/ano.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CustoVacaAno:
    """Custo por matriz/ano por componentes (R$/vaca/ano)."""
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
    # Rebanho inicial
    vacas: int = 1000                 # matrizes em reprodução
    novilhas: int = 250               # novilhas que entram na monta no próximo ciclo
    bezerras_retidas: int = 0         # bezerras retidas (entram em ~2 anos)
    touros: int = 40

    # Índices reprodutivos
    taxa_desmame: float = 0.80        # bezerros desmamados / fêmeas expostas
    mortalidade_bezerro: float = 0.03
    taxa_descarte_vacas: float = 0.16 # % de vacas descartadas/ano
    proporcao_machos: float = 0.50

    # Pesos e preços
    peso_desmame_kg: float = 200.0
    preco_kg_bezerro: float = 13.0    # R$/kg (bezerro ao desmame)
    preco_kg_bezerra: float = 11.0    # fêmea excedente costuma valer menos/kg
    peso_vaca_descarte_kg: float = 450.0
    rendimento_vaca: float = 0.50
    preco_arroba_vaca: float = 280.0  # R$/@ carcaça da vaca de descarte

    # Custo
    custo: CustoVacaAno = field(default_factory=CustoVacaAno)

    anos: int = 5


def projetar(e: CriaEntrada) -> dict:
    vacas = float(e.vacas)
    nov2 = float(e.novilhas)        # novilhas que vão ser expostas neste ano
    nov1 = float(e.bezerras_retidas)  # bezerras retidas (viram nov2 no ano seguinte)
    custo_vaca = e.custo.total

    anos_proj = []
    for ano in range(1, e.anos + 1):
        expostas = vacas + nov2
        desmamados = expostas * e.taxa_desmame
        machos = desmamados * e.proporcao_machos
        femeas = desmamados * (1 - e.proporcao_machos)

        descartadas = vacas * e.taxa_descarte_vacas
        # retém fêmeas para repor o descarte (limitado pelas fêmeas disponíveis)
        reposicao = min(femeas, descartadas)
        femeas_vendidas = femeas - reposicao

        # Economia do ano
        rebanho_matrizes = vacas + nov2 + nov1
        custo_total = rebanho_matrizes * custo_vaca

        receita_machos = machos * e.peso_desmame_kg * e.preco_kg_bezerro
        receita_femeas = femeas_vendidas * e.peso_desmame_kg * e.preco_kg_bezerra
        arrobas_vaca = e.peso_vaca_descarte_kg * e.rendimento_vaca / 15.0
        receita_descarte = descartadas * arrobas_vaca * e.preco_arroba_vaca
        receita_total = receita_machos + receita_femeas + receita_descarte

        custo_por_bezerro = custo_total / desmamados if desmamados else 0
        preco_venda_bezerro = e.peso_desmame_kg * e.preco_kg_bezerro
        lucro_por_bezerro = preco_venda_bezerro - custo_por_bezerro
        lucro_total = receita_total - custo_total

        anos_proj.append({
            "ano": ano,
            "vacas": round(vacas),
            "novilhas": round(nov2),
            "expostas": round(expostas),
            "bezerros_desmamados": round(desmamados),
            "machos_vendidos": round(machos),
            "femeas_vendidas": round(femeas_vendidas),
            "vacas_descartadas": round(descartadas),
            "rebanho_matrizes": round(rebanho_matrizes),
            "custo_total": round(custo_total, 2),
            "receita_total": round(receita_total, 2),
            "lucro_total": round(lucro_total, 2),
            "custo_por_bezerro": round(custo_por_bezerro, 2),
            "preco_venda_bezerro": round(preco_venda_bezerro, 2),
            "lucro_por_bezerro": round(lucro_por_bezerro, 2),
            "lucro_por_vaca_exposta": round(lucro_total / expostas, 2) if expostas else 0,
        })

        # Transição para o próximo ano (pipeline de idade)
        vacas = vacas - descartadas + nov2   # novilhas expostas que pariram viram vacas
        nov2 = nov1                           # bezerras retidas viram novilhas
        nov1 = reposicao                      # novas bezerras retidas

    base = anos_proj[0]
    return {
        "anos": anos_proj,
        "resumo": {
            "custo_vaca_ano": round(custo_vaca, 2),
            "taxa_desmame": e.taxa_desmame,
            "custo_por_bezerro": base["custo_por_bezerro"],
            "preco_venda_bezerro": base["preco_venda_bezerro"],
            "lucro_por_bezerro": base["lucro_por_bezerro"],
            "lucro_por_vaca_exposta": base["lucro_por_vaca_exposta"],
            "viavel": base["lucro_por_bezerro"] > 0,
            "semaforo": "🟢" if base["lucro_por_bezerro"] > 0 else "🔴",
            "rebanho_final": anos_proj[-1]["rebanho_matrizes"],
            "rebanho_inicial": base["rebanho_matrizes"],
        },
        "componentes_custo": {
            "pasto_arrendamento": e.custo.pasto_arrendamento,
            "sal_mineral": e.custo.sal_mineral,
            "sanidade": e.custo.sanidade,
            "mao_de_obra": e.custo.mao_de_obra,
            "outros": e.custo.outros,
        },
    }
