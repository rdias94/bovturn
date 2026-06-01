#!/bin/bash
# BovTurn Intelligence — Setup completo
# Cole no terminal do Cursor e pressione Enter

BASE=~/bovturn
mkdir -p $BASE/app/routes $BASE/app/services

# ── main.py ──────────────────────────────────────────────
cat > $BASE/app/__init__.py << 'EOF'
EOF

cat > $BASE/app/routes/__init__.py << 'EOF'
EOF

cat > $BASE/app/services/__init__.py << 'EOF'
EOF

cat > $BASE/app/main.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import giros

app = FastAPI(title="BovTurn Intelligence API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(giros.router, prefix="/api/giros", tags=["Giros"])

@app.get("/")
def raiz():
    return {"status": "BovTurn Intelligence online", "versao": "1.0.0"}
EOF

# ── motor_cenarios.py ─────────────────────────────────────
cat > $BASE/app/services/motor_cenarios.py << 'MOTOR'
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class SistemaHidrico(str, Enum):
    IRRIGADO = "irrigado"
    SEQUEIRO = "sequeiro"

class SistemaProducao(str, Enum):
    RECRIA = "recria"
    ENGORDA = "engorda"
    RECRIA_ENGORDA = "recria_engorda"
    CONFINAMENTO = "confinamento"
    CICLO_COMPLETO = "ciclo_completo"

class Sexo(str, Enum):
    MACHO = "macho"
    FEMEA = "femea"

class TipoCenario(str, Enum):
    BASE = "base"
    OTIMISTA = "otimista"
    CONSERVADOR = "conservador"
    PESSIMISTA = "pessimista"
    CLIMATICO = "climatico"
    HISTORICO = "historico"

@dataclass
class EntradaGiro:
    valor_animal_cab: float
    peso_entrada_kg: float
    sexo: Sexo
    dias_giro: int
    gmd_esperado: float
    area_ha: float
    lotacao_ua_ha: float
    sistema_hidrico: SistemaHidrico
    sistema_producao: SistemaProducao
    preco_compra_arroba: float
    preco_venda_arroba: float
    consumo_suplemento_pct_pv: float = 0.003
    custo_kg_suplemento: float = 3.50
    custo_mdo_cab_mes: float = 20.0
    custo_gastos_prod_cab_mes: float = 20.0
    custo_arrendamento_ua_mes: float = 0.0
    custo_sanidade_cab_giro: float = 16.27
    rendimento_carcaca: float = 0.50
    idade_compra_meses: Optional[int] = None
    raca: str = "nelore"
    aliquota_funrural_irpj: float = 0.0755
    fator_ajuste_climatico: float = 1.0

@dataclass
class ResultadoCenario:
    tipo: TipoCenario
    nome: str
    gmd: float
    custo_kg_suplemento: float
    preco_venda_arroba: float
    consumo_suplemento_pct_pv: float
    n_animais: int
    peso_saida_kg: float
    peso_saida_arroba: float
    arrobas_produzidas_total: float
    arrobas_por_ha: float
    arrobas_por_ha_ano: float
    custo_nutricao_cab: float
    custo_mdo_cab: float
    custo_gastos_prod_cab: float
    custo_arrendamento_cab: float
    custo_sanidade_cab: float
    custo_total_cab: float
    custo_arroba_produzida: float
    investimento_gado_total: float
    receita_total: float
    margem_bruta_total: float
    lucro_liquido: float
    margem_cab: float
    margem_ha: float
    rentabilidade_giro: float
    rentabilidade_am: float
    lucratividade: float
    score_viabilidade: float
    classificacao_viabilidade: str
    giros_por_ano: float
    idade_venda_meses: Optional[int]

def calcular_cenario(entrada: EntradaGiro, tipo: TipoCenario,
                     fator_gmd=1.0, fator_custo_insumo=1.0,
                     fator_preco_venda=1.0, fator_consumo=1.0) -> ResultadoCenario:
    gmd = entrada.gmd_esperado * fator_gmd * entrada.fator_ajuste_climatico
    custo_kg_sup = entrada.custo_kg_suplemento * fator_custo_insumo
    preco_venda = entrada.preco_venda_arroba * fator_preco_venda
    consumo_pct = entrada.consumo_suplemento_pct_pv * fator_consumo

    peso_medio_sistema = entrada.peso_entrada_kg + (gmd * entrada.dias_giro / 2)
    ua_cab = peso_medio_sistema / 450.0
    n_animais = max(int((entrada.area_ha * entrada.lotacao_ua_ha) / ua_cab), 1)

    peso_saida_kg = entrada.peso_entrada_kg + (gmd * entrada.dias_giro)
    peso_entrada_arroba = entrada.peso_entrada_kg / 30.0
    peso_saida_arroba = peso_saida_kg / 30.0
    arrobas_produzidas_cab = peso_saida_arroba - peso_entrada_arroba
    arrobas_produzidas_total = arrobas_produzidas_cab * n_animais
    giros_por_ano = 365.0 / entrada.dias_giro
    arrobas_por_ha = arrobas_produzidas_total / entrada.area_ha
    arrobas_por_ha_ano = arrobas_por_ha * giros_por_ano

    consumo_kg_dia = peso_medio_sistema * consumo_pct
    custo_nutricao_cab = consumo_kg_dia * custo_kg_sup * entrada.dias_giro
    meses_giro = entrada.dias_giro / 30.0
    custo_mdo_cab = entrada.custo_mdo_cab_mes * meses_giro
    custo_gastos_prod_cab = entrada.custo_gastos_prod_cab_mes * meses_giro
    custo_arrendamento_cab = entrada.custo_arrendamento_ua_mes * ua_cab * meses_giro
    custo_sanidade_cab = entrada.custo_sanidade_cab_giro
    custo_total_cab = (custo_nutricao_cab + custo_mdo_cab +
                       custo_gastos_prod_cab + custo_arrendamento_cab + custo_sanidade_cab)
    custo_arroba = custo_total_cab / arrobas_produzidas_cab if arrobas_produzidas_cab > 0 else 0

    investimento_gado_total = entrada.valor_animal_cab * n_animais
    receita_cab = peso_saida_arroba * preco_venda
    receita_total = receita_cab * n_animais
    margem_cab = receita_cab - (entrada.valor_animal_cab + custo_total_cab)
    margem_bruta_total = margem_cab * n_animais
    margem_ha = margem_bruta_total / entrada.area_ha
    impostos = receita_total * entrada.aliquota_funrural_irpj
    lucro_liquido = margem_bruta_total - impostos

    rentabilidade_giro = margem_cab / entrada.valor_animal_cab if entrada.valor_animal_cab > 0 else 0
    rentabilidade_am = ((1 + rentabilidade_giro) ** (30 / entrada.dias_giro) - 1
                        if entrada.dias_giro > 0 and rentabilidade_giro > -1 else 0.0)
    lucratividade = margem_bruta_total / receita_total if receita_total > 0 else 0

    score = _calcular_score(rentabilidade_giro, lucratividade,
                            arrobas_por_ha, custo_arroba, preco_venda,
                            entrada.fator_ajuste_climatico)
    classificacao = _classificar_score(score)
    idade_venda = (entrada.idade_compra_meses + int(entrada.dias_giro / 30)
                   if entrada.idade_compra_meses else None)

    nomes = {TipoCenario.BASE:"Cenário Base", TipoCenario.OTIMISTA:"Cenário Otimista",
             TipoCenario.CONSERVADOR:"Cenário Conservador", TipoCenario.PESSIMISTA:"Cenário Pessimista",
             TipoCenario.CLIMATICO:"Cenário Climático", TipoCenario.HISTORICO:"Cenário Histórico"}

    return ResultadoCenario(
        tipo=tipo, nome=nomes.get(tipo,"Cenário"),
        gmd=round(gmd,3), custo_kg_suplemento=round(custo_kg_sup,2),
        preco_venda_arroba=round(preco_venda,2), consumo_suplemento_pct_pv=round(consumo_pct,4),
        n_animais=n_animais, peso_saida_kg=round(peso_saida_kg,1),
        peso_saida_arroba=round(peso_saida_arroba,2),
        arrobas_produzidas_total=round(arrobas_produzidas_total,1),
        arrobas_por_ha=round(arrobas_por_ha,2), arrobas_por_ha_ano=round(arrobas_por_ha_ano,2),
        custo_nutricao_cab=round(custo_nutricao_cab,2), custo_mdo_cab=round(custo_mdo_cab,2),
        custo_gastos_prod_cab=round(custo_gastos_prod_cab,2),
        custo_arrendamento_cab=round(custo_arrendamento_cab,2),
        custo_sanidade_cab=round(custo_sanidade_cab,2), custo_total_cab=round(custo_total_cab,2),
        custo_arroba_produzida=round(custo_arroba,2), investimento_gado_total=round(investimento_gado_total,2),
        receita_total=round(receita_total,2), margem_bruta_total=round(margem_bruta_total,2),
        lucro_liquido=round(lucro_liquido,2), margem_cab=round(margem_cab,2),
        margem_ha=round(margem_ha,2), rentabilidade_giro=round(rentabilidade_giro*100,2),
        rentabilidade_am=round(rentabilidade_am*100,2), lucratividade=round(lucratividade*100,2),
        score_viabilidade=round(score,1), classificacao_viabilidade=classificacao,
        giros_por_ano=round(giros_por_ano,2), idade_venda_meses=idade_venda,
    )

def gerar_todos_cenarios(entrada: EntradaGiro):
    return [
        calcular_cenario(entrada, TipoCenario.BASE),
        calcular_cenario(entrada, TipoCenario.OTIMISTA,      1.15, 0.90, 1.05),
        calcular_cenario(entrada, TipoCenario.CONSERVADOR,   0.90, 1.08, 0.97),
        calcular_cenario(entrada, TipoCenario.PESSIMISTA,    0.75, 1.20, 0.90),
        calcular_cenario(entrada, TipoCenario.CLIMATICO),
        calcular_cenario(entrada, TipoCenario.HISTORICO),
    ]

def _calcular_score(rent, lucr, arrobas_ha, custo_arroba, preco_venda, fator_climatico):
    comp_margem  = min(rent / 0.20, 1.0) * 35
    comp_lucr    = min(lucr / 0.30, 1.0) * 25
    comp_clima   = max((fator_climatico - 0.7) / 0.3, 0.0) * 20
    spread       = preco_venda - custo_arroba
    comp_spread  = min(max(spread / 100.0, 0.0), 1.0) * 20
    return comp_margem + comp_lucr + comp_clima + comp_spread

def _classificar_score(score):
    if score < 40:   return "Alto risco"
    elif score < 66: return "Risco moderado"
    elif score < 86: return "Favorável"
    else:            return "Muito favorável"
MOTOR

# ── routes/giros.py ───────────────────────────────────────
cat > $BASE/app/routes/giros.py << 'ROTA'
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from dataclasses import asdict
from app.services.motor_cenarios import (
    EntradaGiro, SistemaHidrico, SistemaProducao, Sexo, gerar_todos_cenarios
)

router = APIRouter()

class GiroRequest(BaseModel):
    valor_animal_cab:           float = Field(..., gt=0)
    peso_entrada_kg:            float = Field(..., gt=0)
    sexo:                       str   = Field(...)
    dias_giro:                  int   = Field(..., gt=0)
    gmd_esperado:               float = Field(..., gt=0)
    area_ha:                    float = Field(..., gt=0)
    lotacao_ua_ha:              float = Field(..., gt=0)
    sistema_hidrico:            str   = Field(...)
    sistema_producao:           str   = Field(...)
    preco_compra_arroba:        float = Field(..., gt=0)
    preco_venda_arroba:         float = Field(..., gt=0)
    consumo_suplemento_pct_pv:  float = 0.003
    custo_kg_suplemento:        float = 3.50
    custo_mdo_cab_mes:          float = 21.0
    custo_gastos_prod_cab_mes:  float = 21.0
    custo_arrendamento_ua_mes:  float = 0.0
    custo_sanidade_cab_giro:    float = 16.27
    idade_compra_meses:         Optional[int] = None
    raca:                       Optional[str] = "nelore"
    fator_ajuste_climatico:     float = 1.0

@router.post("/")
def criar_giro(dados: GiroRequest):
    try:
        entrada = EntradaGiro(
            valor_animal_cab=dados.valor_animal_cab,
            peso_entrada_kg=dados.peso_entrada_kg,
            sexo=Sexo(dados.sexo),
            dias_giro=dados.dias_giro,
            gmd_esperado=dados.gmd_esperado,
            area_ha=dados.area_ha,
            lotacao_ua_ha=dados.lotacao_ua_ha,
            sistema_hidrico=SistemaHidrico(dados.sistema_hidrico),
            sistema_producao=SistemaProducao(dados.sistema_producao),
            preco_compra_arroba=dados.preco_compra_arroba,
            preco_venda_arroba=dados.preco_venda_arroba,
            consumo_suplemento_pct_pv=dados.consumo_suplemento_pct_pv,
            custo_kg_suplemento=dados.custo_kg_suplemento,
            custo_mdo_cab_mes=dados.custo_mdo_cab_mes,
            custo_gastos_prod_cab_mes=dados.custo_gastos_prod_cab_mes,
            custo_arrendamento_ua_mes=dados.custo_arrendamento_ua_mes,
            custo_sanidade_cab_giro=dados.custo_sanidade_cab_giro,
            idade_compra_meses=dados.idade_compra_meses,
            raca=dados.raca or "nelore",
            fator_ajuste_climatico=dados.fator_ajuste_climatico,
        )
        cenarios = gerar_todos_cenarios(entrada)
        cenarios_dict = []
        for c in cenarios:
            d = asdict(c)
            d['tipo'] = d['tipo']
            cenarios_dict.append(d)

        base = cenarios[0]
        pessimista = cenarios[3]
        spread = dados.preco_venda_arroba - base.custo_arroba_produzida
        preco_eq = (dados.valor_animal_cab + base.custo_total_cab) / base.peso_saida_arroba
        score = base.score_viabilidade
        semaforo = "verde" if score >= 66 else ("amarelo" if score >= 41 else "vermelho")

        return {
            "sucesso": True,
            "cenarios": cenarios_dict,
            "resumo": {
                "semaforo": semaforo,
                "classificacao": base.classificacao_viabilidade,
                "score": score,
                "lucro_base": base.lucro_liquido,
                "lucro_pessimista": pessimista.lucro_liquido,
                "margem_cab": base.margem_cab,
                "rentabilidade_am": base.rentabilidade_am,
                "spread_arroba": round(spread, 2),
                "preco_equilibrio": round(preco_eq, 2),
                "n_animais": base.n_animais,
                "arrobas_ha": base.arrobas_por_ha,
            }
        }
    except ValueError as e:
        raise HTTPException(422, f"Dado inválido: {e}")
    except Exception as e:
        raise HTTPException(500, f"Erro: {e}")
ROTA

echo ""
echo "✅ BovTurn criado em ~/bovturn"
echo ""
echo "Estrutura:"
find ~/bovturn/app -type f | sort
echo ""
echo "Para rodar a API:"
echo "  cd ~/bovturn"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --port 8000"
