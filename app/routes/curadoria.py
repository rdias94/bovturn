"""
BovTurn Intelligence — Sistema de Curadoria
=============================================
Aqui o consultor (você) avalia as respostas do agente,
corrige o que estiver errado, e alimenta o sistema
para que ele melhore continuamente.

É o mecanismo pelo qual o app vira seu segundo cérebro:
  - Você vê: o que o cliente perguntou + o que o agente respondeu
  - Você avalia: aprovado / com correção / errado
  - Você corrige se necessário
  - O sistema aprende com cada correção

Com o tempo, o agente passa a responder como você responderia
sem precisar da sua intervenção.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

router = APIRouter()

# Em produção, vai para o PostgreSQL
# Por enquanto, arquivo JSON local para desenvolvimento
CURADORIA_FILE = "curadoria_log.json"


# ─────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────

class AvaliacaoRequest(BaseModel):
    # O que aconteceu
    mensagem_cliente:   str
    resposta_agente:    str
    dados_calculados:   Optional[dict] = None

    # Sua avaliação
    aprovado:           bool
    nota:               int             # 1 a 5
    correcao_texto:     Optional[str] = None   # sua versão correta da resposta
    comentario:         Optional[str] = None   # o que estava errado

    # Contexto
    telefone_cliente:   Optional[str] = None
    fazenda:            Optional[str] = None


class InsightRequest(BaseModel):
    """
    Você manda um insight / regra que o agente deve aprender.
    Ex: "No Maranhão, no período seco, GMD de macho nelore
         em sequeiro raramente passa de 0,50."
    """
    categoria:  str     # "gmd", "mercado", "clima", "nutricao", "regiao"
    regiao:     Optional[str] = None
    insight:    str
    exemplos:   Optional[list] = None


# ─────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────

@router.get("/pendentes", summary="Respostas aguardando sua avaliação")
def listar_pendentes():
    """
    Lista as últimas respostas do agente que ainda não foram avaliadas.
    Interface principal do consultor para curadoria.
    """
    log = _ler_log()
    pendentes = [r for r in log if not r.get("avaliado")]
    return {
        "total_pendentes": len(pendentes),
        "ultimos_10": pendentes[-10:],
    }


@router.post("/avaliar", summary="Aprovar ou corrigir uma resposta do agente")
def avaliar_resposta(avaliacao: AvaliacaoRequest):
    """
    Você avalia a resposta do agente.
    Se corrigiu, o sistema salva sua versão como referência
    para calibrar futuras respostas similares.
    """
    registro = {
        "timestamp":        datetime.now().isoformat(),
        "avaliado":         True,
        "mensagem_cliente": avaliacao.mensagem_cliente,
        "resposta_agente":  avaliacao.resposta_agente,
        "aprovado":         avaliacao.aprovado,
        "nota":             avaliacao.nota,
        "correcao":         avaliacao.correcao_texto,
        "comentario":       avaliacao.comentario,
        "fazenda":          avaliacao.fazenda,
        "dados":            avaliacao.dados_calculados,
    }

    log = _ler_log()
    log.append(registro)
    _salvar_log(log)

    # Se aprovou com nota alta, adiciona ao banco de exemplos positivos
    if avaliacao.aprovado and avaliacao.nota >= 4:
        _registrar_exemplo_positivo(registro)

    # Se corrigiu, salva como exemplo de correção
    if avaliacao.correcao_texto:
        _registrar_correcao(registro)

    return {
        "sucesso": True,
        "mensagem": "Avaliação registrada. O agente aprende com cada correção.",
        "total_avaliacoes": len(log),
    }


@router.post("/insight", summary="Ensinar uma regra nova ao agente")
def adicionar_insight(insight: InsightRequest):
    """
    Você ensina algo novo ao agente.
    Pode ser uma regra regional, um padrão de mercado,
    um comportamento específico de forrageira, etc.

    Ex: "Miyagui irrigado no PA, safra das águas (out-mar),
         com lotação 10 UA/ha → GMD macho nelore 0,85-0,95"
    """
    registro = {
        "timestamp": datetime.now().isoformat(),
        "tipo": "insight_consultor",
        "categoria": insight.categoria,
        "regiao": insight.regiao,
        "insight": insight.insight,
        "exemplos": insight.exemplos or [],
    }

    insights = _ler_insights()
    insights.append(registro)
    _salvar_insights(insights)

    return {
        "sucesso": True,
        "mensagem": f"Insight registrado na categoria '{insight.categoria}'. "
                    f"Total de insights: {len(insights)}",
    }


@router.get("/dashboard", summary="Painel de desempenho do agente")
def dashboard_curadoria():
    """
    Visão geral de como o agente está indo.
    Taxa de aprovação, temas mais corrigidos, evolução.
    """
    log = _ler_log()
    avaliados = [r for r in log if r.get("avaliado")]

    if not avaliados:
        return {"mensagem": "Nenhuma avaliação registrada ainda."}

    aprovados  = [r for r in avaliados if r.get("aprovado")]
    corrigidos = [r for r in avaliados if r.get("correcao")]
    notas      = [r["nota"] for r in avaliados if "nota" in r]

    return {
        "total_interacoes":     len(log),
        "total_avaliados":      len(avaliados),
        "taxa_aprovacao":       f"{len(aprovados)/len(avaliados)*100:.0f}%",
        "nota_media":           f"{sum(notas)/len(notas):.1f}/5" if notas else "N/A",
        "total_correcoes":      len(corrigidos),
        "total_insights":       len(_ler_insights()),
        "mensagem":             _avaliar_maturidade(len(aprovados), len(avaliados)),
    }


@router.get("/exemplos", summary="Banco de exemplos aprovados — memória do agente")
def listar_exemplos():
    """
    Os exemplos que o agente usa como referência ao responder.
    Quanto mais exemplos aprovados, mais preciso o agente fica.
    """
    return {
        "exemplos_positivos": _ler_exemplos_positivos()[-20:],
        "insights_consultor": _ler_insights()[-10:],
    }


# ─────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ─────────────────────────────────────────

def _avaliar_maturidade(aprovados: int, total: int) -> str:
    """Mensagem de status baseada no volume de dados de treinamento."""
    if total < 10:
        return "🌱 Agente em fase inicial. Avalie mais respostas para ele aprender."
    elif total < 50:
        return "🌿 Aprendendo. Continue avaliando — melhora a cada correção."
    elif aprovados / total >= 0.80:
        return "🌳 Agente calibrado. Taxa de aprovação alta — próximo do seu estilo."
    else:
        return "⚙️ Em calibração. Corrija os erros recorrentes com a função /insight."

def _ler_log() -> list:
    try:
        return json.loads(open(CURADORIA_FILE).read())
    except:
        return []

def _salvar_log(log: list):
    open(CURADORIA_FILE, 'w').write(json.dumps(log, ensure_ascii=False, indent=2))

def _ler_insights() -> list:
    try:
        return json.loads(open("insights_consultor.json").read())
    except:
        return []

def _salvar_insights(insights: list):
    open("insights_consultor.json", 'w').write(
        json.dumps(insights, ensure_ascii=False, indent=2))

def _ler_exemplos_positivos() -> list:
    try:
        return json.loads(open("exemplos_positivos.json").read())
    except:
        return []

def _registrar_exemplo_positivo(registro: dict):
    exemplos = _ler_exemplos_positivos()
    exemplos.append(registro)
    open("exemplos_positivos.json", 'w').write(
        json.dumps(exemplos, ensure_ascii=False, indent=2))

def _registrar_correcao(registro: dict):
    try:
        correcoes = json.loads(open("correcoes.json").read())
    except:
        correcoes = []
    correcoes.append(registro)
    open("correcoes.json", 'w').write(
        json.dumps(correcoes, ensure_ascii=False, indent=2))
