"""
BovTurn — Motor de Engorda (peso final por FRAME SCORE)
=======================================================
O peso de abate não é chute: sai do FRAME SCORE do animal.
Fonte: sistema de frame score para Nelore (SciELO/Ciência Animal Brasileira) —
escala 1–11, cada ponto = 1 @ de carcaça (15 kg), a ~54% de rendimento.

  Macho:  @ de abate = 11 + frame   (frame 5→16@/444kg · 7→18@ · 11→22@/611kg)
  Fêmea:  @ de abate =  8 + frame   (frame 5→13@/361kg · 11→19@/528kg)

Frame pequeno = precoce, termina leve e gordo; frame grande = tardio, pesado e magro.
Serve para engorda a pasto OU confinamento (informe GMD e diária).
"""

from dataclasses import dataclass
from typing import Optional

ARROBA_CARCACA_KG = 15.0


def arroba_abate_por_frame(frame: float, sexo: str) -> float:
    """@ de carcaça no abate em função do frame score (Nelore)."""
    frame = max(1.0, min(frame, 11.0))
    base = 11.0 if sexo == "macho" else 8.0
    return base + frame


# Fator peso de abate / peso da vaca adulta (dimorfismo sexual + grau de maturidade).
# O macho abate ~1,2× o peso adulto da matriz (Scot 2020: vaca ~445-500kg → boi
# gordo ~589kg/~20@). A fêmea (novilha) abate ~0,9× o peso da matriz.
# Ajustável — o consultor calibra ao abate real dos rebanhos dele.
FATOR_ABATE_MATRIZ = {"macho": 1.20, "femea": 0.90}


def peso_abate_por_matriz(peso_vaca_adulta: float, sexo: str, fator: Optional[float] = None) -> float:
    f = fator or FATOR_ABATE_MATRIZ.get(sexo, 1.20)
    return peso_vaca_adulta * f


@dataclass
class EngordaEntrada:
    peso_entrada_kg: float = 360.0
    frame_score: float = 6.0
    sexo: str = "macho"
    rendimento_carcaca: float = 54.0       # %
    gmd_esperado: float = 1.0              # kg/dia (peso vivo)
    preco_compra_arroba: float = 320.0     # R$/@ carcaça (reposição)
    preco_venda_arroba: float = 349.7      # R$/@ carcaça (CEPEA boi gordo)
    diaria_total: float = 6.0              # R$/cab/dia (alimentar + operacional)
    arroba_abate_alvo: Optional[float] = None  # @ de abate direto (tem prioridade)
    peso_vaca_adulta: Optional[float] = None   # peso adulto da matriz (proxy do peso de abate)
    fator_abate_matriz: Optional[float] = None # peso de abate ÷ peso da vaca (ajustável)


def calcular(e: EngordaEntrada) -> dict:
    rc = e.rendimento_carcaca / 100.0
    # Prioridade: @ alvo direto > peso da vaca adulta > frame score
    if e.arroba_abate_alvo:
        arroba_abate = e.arroba_abate_alvo
        peso_abate = arroba_abate * ARROBA_CARCACA_KG / rc
        origem = "@ alvo informado"
    elif e.peso_vaca_adulta:
        peso_abate = peso_abate_por_matriz(e.peso_vaca_adulta, e.sexo, e.fator_abate_matriz)
        arroba_abate = peso_abate * rc / ARROBA_CARCACA_KG
        origem = "peso da matriz"
    else:
        arroba_abate = arroba_abate_por_frame(e.frame_score, e.sexo)
        peso_abate = arroba_abate * ARROBA_CARCACA_KG / rc
        origem = "frame informado"
    frame = round(arroba_abate - (11.0 if e.sexo == "macho" else 8.0), 1)  # frame implícito

    arroba_entrada = e.peso_entrada_kg * rc / ARROBA_CARCACA_KG
    arrobas_produzidas = max(arroba_abate - arroba_entrada, 0.01)
    ganho_total_kg = max(peso_abate - e.peso_entrada_kg, 0.0)
    dias = ganho_total_kg / e.gmd_esperado if e.gmd_esperado > 0 else 0

    custo_animal = arroba_entrada * e.preco_compra_arroba
    custo_op = dias * e.diaria_total
    custo_total = custo_animal + custo_op
    receita = arroba_abate * e.preco_venda_arroba
    margem = receita - custo_total

    agio_cab = (e.preco_compra_arroba - e.preco_venda_arroba) * arroba_entrada
    custo_arroba_prod = custo_op / arrobas_produzidas
    tir_am = ((receita / custo_total) ** (30.0 / dias) - 1) if dias > 0 and custo_total > 0 else 0

    return {
        "frame_score": frame,
        "frame_origem": origem,
        "sexo": e.sexo,
        "arroba_abate": round(arroba_abate, 1),
        "peso_abate_kg": round(peso_abate, 1),
        "arroba_entrada": round(arroba_entrada, 2),
        "arrobas_produzidas": round(arrobas_produzidas, 2),
        "dias": round(dias),
        "gmd_esperado": e.gmd_esperado,
        "custo_animal": round(custo_animal, 2),
        "custo_operacional": round(custo_op, 2),
        "custo_total": round(custo_total, 2),
        "receita": round(receita, 2),
        "margem_cab": round(margem, 2),
        "custo_arroba_produzida": round(custo_arroba_prod, 2),
        "agio_cab": round(agio_cab, 2),
        "tir_am_pct": round(tir_am * 100, 2),
        "viavel": margem > 0,
        "semaforo": "🟢" if margem > 0 else "🔴",
    }


def tabela_frame(sexo: str, rc: float = 54.0) -> list[dict]:
    """Tabela de referência frame → @ → peso de abate (para o dashboard)."""
    r = rc / 100.0
    linhas = []
    for f in range(1, 12):
        a = arroba_abate_por_frame(f, sexo)
        linhas.append({
            "frame": f,
            "arroba_abate": round(a, 1),
            "peso_abate_kg": round(a * ARROBA_CARCACA_KG / r),
        })
    return linhas
