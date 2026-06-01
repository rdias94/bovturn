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
