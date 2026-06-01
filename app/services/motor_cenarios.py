"""
BovTurn Intelligence — Motor de Cenários v2
=============================================
Aceita o preço do animal em qualquer formato:
  - R$/kg  (mais comum em leilão — "14 reais o kg")
  - R$/@   (padrão técnico — "380 reais a arroba")
  - R$/cab total (quando já tem o valor fechado)

Frete e comissão separados do preço de mercado.
Calcula automaticamente os demais a partir de qualquer um.

Também aceita modo WhatsApp com inputs mínimos:
  - peso entrada + preco_kg → cenário genérico
  - peso entrada + peso saída + preco_kg → cenário com GMD real
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────

class SistemaHidrico(str, Enum):
    IRRIGADO    = "irrigado"
    SEQUEIRO    = "sequeiro"
    MISTO       = "misto"
    CONFINAMENTO= "confinamento"

class SistemaProducao(str, Enum):
    RECRIA          = "recria"
    ENGORDA         = "engorda"
    RECRIA_ENGORDA  = "recria_engorda"
    CONFINAMENTO    = "confinamento"
    CICLO_COMPLETO  = "ciclo_completo"

class Sexo(str, Enum):
    MACHO = "macho"
    FEMEA = "femea"

class TipoCenario(str, Enum):
    BASE        = "base"
    OTIMISTA    = "otimista"
    CONSERVADOR = "conservador"
    PESSIMISTA  = "pessimista"
    CLIMATICO   = "climatico"
    HISTORICO   = "historico"


# ─────────────────────────────────────────
# ENTRADA DO GIRO — flexível por design
# ─────────────────────────────────────────

@dataclass
class EntradaGiro:
    """
    Entrada flexível: aceita preço do animal em qualquer um dos 3 formatos.
    Basta informar UM dos três — o sistema calcula os outros.

    PRIORIDADE DE CÁLCULO:
      1. preco_compra_kg   → calcula arroba e total
      2. preco_compra_arroba → calcula kg e total
      3. valor_animal_mercado → calcula kg e arroba

    Frete e comissão são SEMPRE separados do preço de mercado.
    O custo real por cabeça = valor_mercado + frete + comissão.

    MODO WHATSAPP (mínimo viável):
      - peso_entrada_kg + preco_compra_kg → cenário com defaults históricos
      - peso_entrada_kg + peso_saida_kg + preco_compra_kg → mais preciso
    """

    # ── Obrigatório sempre ────────────────────────────────────────
    peso_entrada_kg:    float   # Peso médio de entrada em kg

    # ── Preço de compra — informe APENAS UM dos três ─────────────
    preco_compra_kg:        Optional[float] = None  # R$/kg  (ex: 14.00)
    preco_compra_arroba:    Optional[float] = None  # R$/@   (ex: 285.00)
    valor_animal_mercado:   Optional[float] = None  # R$/cab sem frete/comissão

    # ── Frete e comissão — sempre separados ───────────────────────
    frete_cab:      float = 0.0   # R$/cab de frete
    comissao_cab:   float = 0.0   # R$/cab fixo de comissão
    comissao_pct:   float = 0.0   # % sobre o valor (alternativo ao fixo)
                                  # se informar ambos, soma os dois

    # ── Saída e prazo ─────────────────────────────────────────────
    preco_venda_arroba: float = 0.0   # R$/@ esperado na venda
    preco_venda_kg:     Optional[float] = None  # alternativo — converte auto

    dias_giro:          int   = 90    # Duração esperada em dias
    gmd_esperado:       float = 0.0   # kg/dia — se 0, usa referência histórica
    peso_saida_kg:      Optional[float] = None  # se informado, calcula GMD

    # ── Área ─────────────────────────────────────────────────────
    area_ha:        float = 1.0
    lotacao_ua_ha:  float = 1.0

    # ── Contexto (para defaults inteligentes) ─────────────────────
    sistema_hidrico:    SistemaHidrico  = SistemaHidrico.SEQUEIRO
    sistema_producao:   SistemaProducao = SistemaProducao.ENGORDA
    sexo:               Sexo            = Sexo.MACHO
    raca:               str             = "nelore"
    idade_compra_meses: Optional[int]   = None

    # ── Nutrição ─────────────────────────────────────────────────
    consumo_suplemento_pct_pv:  float = 0.003
    custo_kg_suplemento:        float = 3.50

    # ── Custos fixos ─────────────────────────────────────────────
    custo_mdo_cab_mes:          float = 20.0
    custo_gastos_prod_cab_mes:  float = 20.0
    custo_arrendamento_ua_mes:  float = 0.0
    custo_sanidade_cab_giro:    float = 16.27

    # ── Impostos ─────────────────────────────────────────────────
    aliquota_funrural_irpj: float = 0.0755

    # ── Fator climático ───────────────────────────────────────────
    fator_ajuste_climatico: float = 1.0

    # ── Campos calculados (preenchidos automaticamente) ───────────
    # NÃO informe estes — são gerados pelo __post_init__
    _preco_compra_kg_calc:      float = field(default=0.0, init=False, repr=False)
    _preco_compra_arroba_calc:  float = field(default=0.0, init=False, repr=False)
    _valor_animal_mercado_calc: float = field(default=0.0, init=False, repr=False)
    _valor_animal_custo_total:  float = field(default=0.0, init=False, repr=False)
    _comissao_real_cab:         float = field(default=0.0, init=False, repr=False)

    def __post_init__(self):
        """
        Resolve o preço do animal independente de como foi informado.
        Prioridade: kg > arroba > total.
        Sempre calcula os 3 formatos e o custo real por cabeça.
        """
        peso_arroba = self.peso_entrada_kg / 30.0

        # ── 1. Resolver preço de mercado base ─────────────────────
        if self.preco_compra_kg is not None and self.preco_compra_kg > 0:
            # Informou R$/kg — mais comum em leilão
            kg = self.preco_compra_kg
            self._preco_compra_kg_calc      = kg
            self._preco_compra_arroba_calc  = kg * 30.0
            self._valor_animal_mercado_calc = kg * self.peso_entrada_kg

        elif self.preco_compra_arroba is not None and self.preco_compra_arroba > 0:
            # Informou R$/@ — padrão técnico
            self._preco_compra_arroba_calc  = self.preco_compra_arroba
            self._preco_compra_kg_calc      = self.preco_compra_arroba / 30.0
            self._valor_animal_mercado_calc = self.preco_compra_arroba * peso_arroba

        elif self.valor_animal_mercado is not None and self.valor_animal_mercado > 0:
            # Informou total por cabeça
            self._valor_animal_mercado_calc = self.valor_animal_mercado
            self._preco_compra_kg_calc      = self.valor_animal_mercado / self.peso_entrada_kg
            self._preco_compra_arroba_calc  = self._preco_compra_kg_calc * 30.0

        else:
            raise ValueError(
                "Informe pelo menos um dos preços de compra: "
                "preco_compra_kg, preco_compra_arroba ou valor_animal_mercado"
            )

        # ── 2. Calcular comissão real ─────────────────────────────
        comissao_pct_valor = self._valor_animal_mercado_calc * self.comissao_pct
        self._comissao_real_cab = self.comissao_cab + comissao_pct_valor

        # ── 3. Custo total por cabeça (mercado + frete + comissão) ─
        self._valor_animal_custo_total = (
            self._valor_animal_mercado_calc
            + self.frete_cab
            + self._comissao_real_cab
        )

        # ── 4. Resolver preço de venda ────────────────────────────
        if self.preco_venda_kg is not None and self.preco_venda_kg > 0:
            self.preco_venda_arroba = self.preco_venda_kg * 30.0

        # ── 5. Resolver GMD se peso de saída foi informado ────────
        if self.peso_saida_kg is not None and self.peso_saida_kg > 0 and self.dias_giro > 0:
            self.gmd_esperado = (self.peso_saida_kg - self.peso_entrada_kg) / self.dias_giro

        # ── 6. Defaults inteligentes se GMD ainda for 0 ──────────
        if self.gmd_esperado <= 0:
            self.gmd_esperado = _gmd_referencia(
                self.sistema_hidrico,
                self.sistema_producao,
                self.sexo,
                self.raca,
            )

    # ── Properties públicas para uso no motor ─────────────────────

    @property
    def kg_compra(self) -> float:
        """Preço de mercado em R$/kg"""
        return self._preco_compra_kg_calc

    @property
    def arroba_compra(self) -> float:
        """Preço de mercado em R$/@"""
        return self._preco_compra_arroba_calc

    @property
    def valor_mercado_cab(self) -> float:
        """Valor de mercado por cabeça (sem frete/comissão)"""
        return self._valor_animal_mercado_calc

    @property
    def custo_total_cab_compra(self) -> float:
        """Custo real por cabeça (mercado + frete + comissão)"""
        return self._valor_animal_custo_total

    @property
    def resumo_preco_entrada(self) -> dict:
        """Devolve os 3 formatos de preço + composição do custo"""
        return {
            "preco_kg":             round(self._preco_compra_kg_calc, 4),
            "preco_arroba":         round(self._preco_compra_arroba_calc, 2),
            "valor_mercado_cab":    round(self._valor_animal_mercado_calc, 2),
            "frete_cab":            round(self.frete_cab, 2),
            "comissao_cab":         round(self._comissao_real_cab, 2),
            "custo_total_cab":      round(self._valor_animal_custo_total, 2),
        }


# ─────────────────────────────────────────
# GMD DE REFERÊNCIA (histórico calibrado)
# Usado quando cliente não informa GMD
# ─────────────────────────────────────────

def _gmd_referencia(hidrico: SistemaHidrico, producao: SistemaProducao,
                    sexo: Sexo, raca: str) -> float:
    """
    GMD médio histórico por combinação de sistema + sexo.
    Baseado nos dados reais dos BPs e análises de giro fornecidos.
    Será refinado pelo ML conforme giros reais são registrados.
    """
    tabela = {
        # (hidrico, producao, sexo): gmd
        (SistemaHidrico.IRRIGADO,   SistemaProducao.RECRIA,         Sexo.MACHO):  0.83,
        (SistemaHidrico.IRRIGADO,   SistemaProducao.RECRIA,         Sexo.FEMEA):  0.70,
        (SistemaHidrico.IRRIGADO,   SistemaProducao.ENGORDA,        Sexo.MACHO):  1.10,
        (SistemaHidrico.IRRIGADO,   SistemaProducao.RECRIA_ENGORDA, Sexo.MACHO):  0.83,
        (SistemaHidrico.SEQUEIRO,   SistemaProducao.RECRIA,         Sexo.MACHO):  0.55,
        (SistemaHidrico.SEQUEIRO,   SistemaProducao.RECRIA,         Sexo.FEMEA):  0.45,
        (SistemaHidrico.SEQUEIRO,   SistemaProducao.ENGORDA,        Sexo.MACHO):  1.00,
        (SistemaHidrico.SEQUEIRO,   SistemaProducao.ENGORDA,        Sexo.FEMEA):  0.85,
        (SistemaHidrico.SEQUEIRO,   SistemaProducao.RECRIA_ENGORDA, Sexo.MACHO):  0.60,
        (SistemaHidrico.CONFINAMENTO, SistemaProducao.ENGORDA,      Sexo.MACHO):  1.40,
        (SistemaHidrico.CONFINAMENTO, SistemaProducao.ENGORDA,      Sexo.FEMEA):  1.20,
    }
    chave = (hidrico, producao, sexo)
    gmd = tabela.get(chave, 0.80)   # default 0,80 se combinação não mapeada

    # Ajuste por raça: cruzado +8%, nelore base, angus +5%
    ajuste_raca = {"cruzado": 1.08, "nelore": 1.00, "angus": 1.05,
                   "guzera": 0.95, "brahman": 0.98}
    fator = ajuste_raca.get(raca.lower(), 1.00)
    return round(gmd * fator, 3)


# ─────────────────────────────────────────
# RESULTADO DO CENÁRIO
# ─────────────────────────────────────────

@dataclass
class ResultadoCenario:
    tipo:   TipoCenario
    nome:   str

    # Parâmetros do cenário
    gmd:                    float
    preco_venda_arroba:     float
    custo_kg_suplemento:    float

    # Dimensionamento
    n_animais:              int
    peso_saida_kg:          float
    peso_saida_arroba:      float
    arrobas_produzidas_total: float
    arrobas_por_ha:         float
    arrobas_por_ha_ano:     float

    # Custos por cabeça
    custo_compra_cab:       float   # custo real (mercado + frete + comissão)
    custo_nutricao_cab:     float
    custo_mdo_cab:          float
    custo_gastos_prod_cab:  float
    custo_arrendamento_cab: float
    custo_sanidade_cab:     float
    custo_operacional_cab:  float   # soma dos custos SEM o animal
    custo_total_cab:        float   # compra + operacional
    custo_arroba_produzida: float

    # Financeiro
    investimento_gado_total: float
    receita_total:          float
    margem_bruta_total:     float
    lucro_liquido:          float
    margem_cab:             float
    margem_ha:              float

    # Rentabilidade
    rentabilidade_giro:     float   # % no período
    rentabilidade_am:       float   # % ao mês
    lucratividade:          float   # margem / receita

    # Score
    score_viabilidade:      float
    classificacao_viabilidade: str

    # Outros
    giros_por_ano:          float
    idade_venda_meses:      Optional[int]

    # Resumo de preços para exibição
    preco_entrada_resumo:   dict


# ─────────────────────────────────────────
# MOTOR — calcula um cenário
# ─────────────────────────────────────────

def calcular_cenario(entrada: EntradaGiro, tipo: TipoCenario,
                     fator_gmd: float = 1.0,
                     fator_custo_insumo: float = 1.0,
                     fator_preco_venda: float = 1.0) -> ResultadoCenario:

    gmd         = entrada.gmd_esperado * fator_gmd * entrada.fator_ajuste_climatico
    custo_sup   = entrada.custo_kg_suplemento * fator_custo_insumo
    preco_venda = entrada.preco_venda_arroba * fator_preco_venda

    # ── Dimensionamento ───────────────────────────────────────────
    peso_medio  = entrada.peso_entrada_kg + (gmd * entrada.dias_giro / 2)
    ua_cab      = peso_medio / 450.0
    n_animais   = max(int((entrada.area_ha * entrada.lotacao_ua_ha) / ua_cab), 1)

    peso_saida_kg       = entrada.peso_entrada_kg + (gmd * entrada.dias_giro)
    arr_entrada         = entrada.peso_entrada_kg / 30.0
    arr_saida           = peso_saida_kg / 30.0
    arrobas_prod_cab    = arr_saida - arr_entrada
    arrobas_total       = arrobas_prod_cab * n_animais
    giros_por_ano       = 365.0 / entrada.dias_giro
    arrobas_ha          = arrobas_total / entrada.area_ha
    arrobas_ha_ano      = arrobas_ha * giros_por_ano

    # ── Custos operacionais por cabeça ───────────────────────────
    consumo_dia     = peso_medio * entrada.consumo_suplemento_pct_pv
    custo_nutricao  = consumo_dia * custo_sup * entrada.dias_giro

    meses           = entrada.dias_giro / 30.0
    custo_mdo       = entrada.custo_mdo_cab_mes * meses
    custo_gastos    = entrada.custo_gastos_prod_cab_mes * meses
    custo_arrend    = entrada.custo_arrendamento_ua_mes * ua_cab * meses
    custo_sanidade  = entrada.custo_sanidade_cab_giro

    custo_op_cab    = custo_nutricao + custo_mdo + custo_gastos + custo_arrend + custo_sanidade

    # Custo da @ produzida (só sobre o operacional, não a compra)
    custo_arroba_prod = custo_op_cab / arrobas_prod_cab if arrobas_prod_cab > 0 else 0

    # ── Custo total por cabeça (compra + operacional) ─────────────
    custo_compra    = entrada.custo_total_cab_compra   # já tem frete + comissão
    custo_total_cab = custo_compra + custo_op_cab

    # ── Financeiro ────────────────────────────────────────────────
    investimento    = custo_compra * n_animais
    receita_cab     = arr_saida * preco_venda
    receita_total   = receita_cab * n_animais

    margem_cab      = receita_cab - custo_total_cab
    margem_total    = margem_cab * n_animais
    margem_ha       = margem_total / entrada.area_ha
    lucro_liquido   = margem_total - (receita_total * entrada.aliquota_funrural_irpj)

    # ── Rentabilidade ─────────────────────────────────────────────
    rent_giro = margem_cab / custo_compra if custo_compra > 0 else 0
    rent_am   = ((1 + rent_giro) ** (30 / entrada.dias_giro) - 1
                 if entrada.dias_giro > 0 and rent_giro > -1 else 0.0)
    lucratividade = margem_total / receita_total if receita_total > 0 else 0

    # ── Score ─────────────────────────────────────────────────────
    score = _score(rent_giro, lucratividade, preco_venda,
                   custo_arroba_prod, entrada.fator_ajuste_climatico)

    # ── Idade de venda ────────────────────────────────────────────
    idade_venda = None
    if entrada.idade_compra_meses:
        idade_venda = entrada.idade_compra_meses + int(entrada.dias_giro / 30)

    nomes = {
        TipoCenario.BASE:        "Cenário Base",
        TipoCenario.OTIMISTA:    "Cenário Otimista",
        TipoCenario.CONSERVADOR: "Cenário Conservador",
        TipoCenario.PESSIMISTA:  "Cenário Pessimista",
        TipoCenario.CLIMATICO:   "Cenário Climático",
        TipoCenario.HISTORICO:   "Cenário Histórico",
    }

    return ResultadoCenario(
        tipo=tipo, nome=nomes.get(tipo, "Cenário"),
        gmd=round(gmd, 3),
        preco_venda_arroba=round(preco_venda, 2),
        custo_kg_suplemento=round(custo_sup, 2),
        n_animais=n_animais,
        peso_saida_kg=round(peso_saida_kg, 1),
        peso_saida_arroba=round(arr_saida, 2),
        arrobas_produzidas_total=round(arrobas_total, 1),
        arrobas_por_ha=round(arrobas_ha, 2),
        arrobas_por_ha_ano=round(arrobas_ha_ano, 2),
        custo_compra_cab=round(custo_compra, 2),
        custo_nutricao_cab=round(custo_nutricao, 2),
        custo_mdo_cab=round(custo_mdo, 2),
        custo_gastos_prod_cab=round(custo_gastos, 2),
        custo_arrendamento_cab=round(custo_arrend, 2),
        custo_sanidade_cab=round(custo_sanidade, 2),
        custo_operacional_cab=round(custo_op_cab, 2),
        custo_total_cab=round(custo_total_cab, 2),
        custo_arroba_produzida=round(custo_arroba_prod, 2),
        investimento_gado_total=round(investimento, 2),
        receita_total=round(receita_total, 2),
        margem_bruta_total=round(margem_total, 2),
        lucro_liquido=round(lucro_liquido, 2),
        margem_cab=round(margem_cab, 2),
        margem_ha=round(margem_ha, 2),
        rentabilidade_giro=round(rent_giro * 100, 2),
        rentabilidade_am=round(rent_am * 100, 2),
        lucratividade=round(lucratividade * 100, 2),
        score_viabilidade=round(score, 1),
        classificacao_viabilidade=_classificar(score),
        giros_por_ano=round(giros_por_ano, 2),
        idade_venda_meses=idade_venda,
        preco_entrada_resumo=entrada.resumo_preco_entrada,
    )


def gerar_todos_cenarios(entrada: EntradaGiro) -> list[ResultadoCenario]:
    return [
        calcular_cenario(entrada, TipoCenario.BASE),
        calcular_cenario(entrada, TipoCenario.OTIMISTA,      1.15, 0.90, 1.05),
        calcular_cenario(entrada, TipoCenario.CONSERVADOR,   0.90, 1.08, 0.97),
        calcular_cenario(entrada, TipoCenario.PESSIMISTA,    0.75, 1.20, 0.90),
        calcular_cenario(entrada, TipoCenario.CLIMATICO),     # fator já no input
        calcular_cenario(entrada, TipoCenario.HISTORICO),     # placeholder ML
    ]


# ─────────────────────────────────────────
# SCORE E CLASSIFICAÇÃO
# ─────────────────────────────────────────

def _score(rent_giro, lucratividade, preco_venda,
           custo_arroba_prod, fator_climatico) -> float:
    comp_margem  = min(rent_giro / 0.20,  1.0) * 35
    comp_lucr    = min(lucratividade / 0.30, 1.0) * 25
    comp_clima   = max((fator_climatico - 0.7) / 0.3, 0.0) * 20
    spread       = preco_venda - custo_arroba_prod
    comp_spread  = min(max(spread / 100.0, 0.0), 1.0) * 20
    return comp_margem + comp_lucr + comp_clima + comp_spread

def _classificar(score: float) -> str:
    if score < 40:   return "Alto risco"
    elif score < 66: return "Risco moderado"
    elif score < 86: return "Favorável"
    else:            return "Muito favorável"


# ─────────────────────────────────────────
# PARSER WHATSAPP — extrai dados de texto livre
# ─────────────────────────────────────────

def parsear_mensagem_whatsapp(texto: str, contexto_fazenda: dict = None) -> dict:
    """
    Tenta extrair parâmetros de uma mensagem em linguagem natural.
    Retorna dict com os campos encontrados e os que faltam.

    Exemplos que consegue parsear:
    - "200 nelore machos 360kg 3500 reais o animal"
    - "olhando um leilão 360kg a 380 reais a arroba"
    - "bezerro 220kg 14 reais o kg sequeiro"
    """
    import re

    resultado = {
        "dados_encontrados": {},
        "dados_faltando": [],
        "confianca": "baixa",
        "mensagem_original": texto,
    }

    t = texto.lower()

    # N° de animais
    n = re.search(r'(\d+)\s*(animais?|cabeças?|cab\.?|bois?|nelores?|novilh)', t)
    if n: resultado["dados_encontrados"]["n_animais_referencia"] = int(n.group(1))

    # Peso de entrada — número de 2-3 dígitos seguido de kg SEM contexto de preço
    pe = re.search(r'(?<!\$)(?<!\d\s)(\d{2,3})\s*kg\b', t)
    if pe: resultado["dados_encontrados"]["peso_entrada_kg"] = float(pe.group(1))

    # Preço R$/kg: "14 reais o kg", "14 o kg", "r$14/kg"
    # Exige contexto explícito de preço para não confundir com o peso
    pkg = re.search(r'r?\$?\s*(\d+[,.]?\d*)\s*(?:reais?\s*o\s*kg|o\s*kg\b|\/kg)', t)
    if pkg:
        resultado["dados_encontrados"]["preco_compra_kg"] = float(pkg.group(1).replace(',','.'))

    # Preço R$/@: "380 a arroba", "r$380/@", "380 reais a arroba"
    parr = re.search(r'r?\$?\s*(\d+[,.]?\d*)\s*(?:reais?\s*a\s*arroba|a\s*arroba|\/arroba|\s*@\b)', t)
    if parr:
        resultado["dados_encontrados"]["preco_compra_arroba"] = float(parr.group(1).replace(',','.'))

    # Preço R$/cab: "3500 reais o animal", "3.500 por cabeça"
    pcab = re.search(r'r?\$?\s*(\d[\d.,]*)\s*(?:reais?\s*o\s*animal|por\s*cabeça|\/cab|o\s*animal)', t)
    if pcab:
        val = pcab.group(1).replace('.','').replace(',','.')
        resultado["dados_encontrados"]["valor_animal_mercado"] = float(val)

    # Sexo
    if any(p in t for p in ['macho','boi','garrote','novilho']): resultado["dados_encontrados"]["sexo"] = "macho"
    if any(p in t for p in ['fêmea','femea','novilha','vaca']):  resultado["dados_encontrados"]["sexo"] = "femea"

    # Sistema
    if 'irrigad' in t: resultado["dados_encontrados"]["sistema_hidrico"] = "irrigado"
    if 'sequeiro' in t or 'seco' in t: resultado["dados_encontrados"]["sistema_hidrico"] = "sequeiro"
    if 'confinamento' in t or 'confin' in t: resultado["dados_encontrados"]["sistema_hidrico"] = "confinamento"

    # Raça
    for raca in ['nelore','cruzado','angus','guzera','brahman','anelorado']:
        if raca in t: resultado["dados_encontrados"]["raca"] = raca; break

    # Suplemento / % PV
    sup = re.search(r'(\d[,.]?\d*)\s*%\s*(pv|peso)', t)
    if sup: resultado["dados_encontrados"]["consumo_suplemento_pct_pv"] = float(sup.group(1).replace(',','.'))/100

    # Dias / período
    dias = re.search(r'(\d+)\s*dias', t)
    if dias: resultado["dados_encontrados"]["dias_giro"] = int(dias.group(1))

    # Avaliar confiança
    encontrados = len(resultado["dados_encontrados"])
    tem_peso    = "peso_entrada_kg" in resultado["dados_encontrados"]
    tem_preco   = any(k in resultado["dados_encontrados"]
                      for k in ["preco_compra_kg","preco_compra_arroba","valor_animal_mercado"])

    if tem_peso and tem_preco and encontrados >= 4:
        resultado["confianca"] = "alta"
    elif tem_peso and tem_preco:
        resultado["confianca"] = "media"
    elif tem_peso or tem_preco:
        resultado["confianca"] = "baixa"

    # Dados faltando
    if not tem_peso:  resultado["dados_faltando"].append("peso de entrada (kg)")
    if not tem_preco: resultado["dados_faltando"].append("preço do animal (R$/kg, R$/@ ou R$/cab)")
    if "preco_venda_arroba" not in resultado["dados_encontrados"]:
        resultado["dados_faltando"].append("preço de venda (@ esperada)")

    return resultado
