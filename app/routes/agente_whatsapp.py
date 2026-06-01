"""
BovTurn Intelligence — Agente WhatsApp
========================================
O segundo cérebro do consultor.

Recebe qualquer entrada (texto, áudio, foto de leilão)
e responde como o consultor responderia — com os dados
do cliente quando disponíveis, com defaults históricos
quando não.

FLUXO:
  1. Recebe mensagem (texto / áudio / imagem)
  2. Transcribe áudio com Whisper se necessário
  3. Extrai entidades (peso, preço, raça, sistema...)
  4. Busca contexto do cliente no banco (fazenda, histórico)
  5. Preenche lacunas com defaults calibrados
  6. Roda o motor de cenários
  7. Gera resposta na voz do consultor
  8. Pergunta o que falta para refinar

PERSONALIDADE DO CONSULTOR (ajuste conforme seu estilo):
  - Direto, sem enrolação
  - Fala os números que importam primeiro
  - Dá a recomendação, não fica em cima do muro
  - Faz uma pergunta por vez para refinar
  - Usa linguagem do campo, não de planilha
"""

import os
import json
import base64
import httpx
from typing import Optional
from dataclasses import asdict

from app import db

# Claude API via httpx direto (sem SDK — compatível com endpoints async)
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-6"


def _chamar_claude(messages: list, max_tokens: int = 400,
                   system: Optional[str] = None) -> str:
    """Chama a API da Anthropic via httpx e retorna o texto da resposta."""
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    r = httpx.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    d = r.json()
    if "content" in d:
        return d["content"][0]["text"]
    return f"[Erro {r.status_code}: {d.get('error', {}).get('message', d)}]"


# Motor de cenários local
from app.services.motor_cenarios import (
    EntradaGiro, SistemaHidrico, SistemaProducao, Sexo,
    gerar_todos_cenarios, parsear_mensagem_whatsapp, _gmd_referencia
)


# ─────────────────────────────────────────────────────────────
# PROMPT DO SISTEMA — a personalidade do consultor
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Você é o assistente de análise pecuária de um consultor especializado 
em pecuária de corte brasileira. Você fala COM A VOZ DO CONSULTOR — não como uma IA.

SEU CONHECIMENTO:
- Sistemas de cria, recria e engorda (sequeiro e irrigado)
- Forrageiras tropicais (Miyagui, Mombaça, Marandu, Ruziziensis, Tifton, Zuri)
- GMD por sistema e raça, capacidade de suporte, custo de @ produzida
- Mercado de boi gordo, bezerro, insumos
- Impacto de clima (El Niño, La Niña, veranico, geada) por sistema
- Suplementação (mineral, proteico, energético), % PV, viabilidade econômica

SEU ESTILO:
- Direto. O produtor quer o número, não a explicação de como você chegou nele.
- Dá a recomendação. Nunca fica em cima do muro.
- Usa linguagem do campo. "Arroba", "cabeça", "giro", "cabo de vassoura", não "unidade animal equivalente".
- Quando o cenário é ruim, diz que é ruim — e explica o que mudaria para ficar bom.
- Faz UMA pergunta por vez para refinar a análise.
- Nunca menciona que é uma IA ou que está calculando. Responde como o consultor responderia pelo WhatsApp.

QUANDO TEM DADOS DO CLIENTE:
- Use o histórico de GMD da fazenda dele, não a tabela genérica.
- Mencione o pasto específico se souber ("no Pivô 3 você costuma bater 0,90...").
- Compare com giros anteriores dele ("na última recria de macho você fez X").

QUANDO NÃO TEM DADOS:
- Use as médias históricas calibradas da base.
- Seja transparente que é uma estimativa: "sem saber o pasto, estou usando 0,80 de GMD".
- Convide a refinar: faça uma pergunta.

FORMATO DA RESPOSTA:
- Máximo 3-4 linhas de texto.
- Depois os números em tópicos curtos.
- Fecha com UMA pergunta de refinamento OU uma recomendação clara.
- Nunca listas longas. Nunca parágrafos acadêmicos.
"""

# ─────────────────────────────────────────────────────────────
# FUNÇÕES DE TRANSCRIÇÃO E VISÃO
# ─────────────────────────────────────────────────────────────

def transcrever_audio(audio_bytes: bytes, formato: str = "ogg") -> str:
    """
    Transcreve áudio usando Whisper via API da OpenAI.
    (Requer openai instalado: pip install openai)
    """
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=f".{formato}", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            with open(f.name, "rb") as audio_file:
                resultado = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="pt"
                )
        return resultado.text
    except Exception as e:
        return f"[Erro na transcrição: {e}]"


def analisar_imagem_leilao(imagem_base64: str, mime_type: str = "image/jpeg") -> str:
    """
    Analisa foto de leilão com Claude Vision.
    Extrai: peso, preço, raça, número de animais visíveis.
    """
    messages = [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": imagem_base64,
                }
            },
            {
                "type": "text",
                "text": """Você está analisando uma foto de leilão de gado ou catálogo de leilão.

Extraia SOMENTE o que conseguir ler claramente na imagem:
- Número de animais (lote)
- Peso médio ou peso individual
- Preço (R$/kg, R$/@ ou lance total)
- Raça
- Sexo/categoria (bezerro, garrote, boi magro, novilha...)
- Qualquer outro dado pecuário visível

Responda APENAS com o que você viu, no formato:
"Vi na imagem: [lista do que encontrou]"
Se não conseguir ler nada, diga "Imagem ilegível"."""
            }
        ]
    }]
    return _chamar_claude(messages, max_tokens=500)


# ─────────────────────────────────────────────────────────────
# CONTEXTO DO CLIENTE — busca no banco
# ─────────────────────────────────────────────────────────────

_CONTEXTO_MOCK = {
    # Telefone: contexto da fazenda (usado quando não há banco conectado)
    "+5565999999999": {
        "nome": "Riesley",
        "fazenda": "VPAgro",
        "sistema_predominante": "irrigado",
        "forrageira": "Miyagui",
        "gmd_historico_macho_irrigado": 0.89,
        "gmd_historico_femea_irrigado": 0.72,
        "custo_mdo_cab_mes": 9.86,
        "custo_gastos_prod_cab_mes": 41.48,
        "preco_arrendamento": 0,
        "lotacao_media_ua_ha": 10.0,
        "ultimo_giro": {
            "categoria": "Nelore macho",
            "peso_entrada": 220,
            "peso_saida": 420,
            "dias": 240,
            "gmd_real": 0.83,
            "margem_cab": 1148,
            "rent_am": 5.6,
        }
    }
}


async def buscar_contexto_cliente(telefone: str) -> dict:
    """
    Busca dados do cliente para personalizar a análise.

    Com banco conectado, puxa contexto REAL e que aprende:
      - GMD histórico por sexo+sistema (média dos giros finalizados)
      - custos médios e lotação dos giros da fazenda
      - o último giro realizado
    Sem banco (DATABASE_URL ausente), cai no mock de desenvolvimento.
    Em qualquer erro de query, degrada para {} (o agente usa defaults).
    """
    if not db.tem_banco():
        return _CONTEXTO_MOCK.get(telefone, {})
    try:
        return await _contexto_do_banco(telefone)
    except Exception as e:
        print(f"[agente] Falha ao buscar contexto no banco ({e}). Usando defaults.")
        return {}


async def _contexto_do_banco(telefone: str) -> dict:
    """Monta o contexto do cliente a partir do PostgreSQL."""
    async with db.pool().acquire() as con:
        # 1. Identificar a fazenda pelo telefone (usuarios → ou clientes)
        fazenda = await con.fetchrow(
            """
            SELECT f.id   AS fazenda_id,
                   f.nome AS fazenda,
                   f.area_util_ha,
                   f.tem_irrigacao,
                   f.nivel_tecnologico,
                   COALESCE(u.nome, c.nome) AS nome
            FROM usuarios u
            JOIN fazendas f ON f.id = u.fazenda_id
            JOIN clientes c ON c.id = f.cliente_id
            WHERE u.telefone = $1 AND u.ativo
            LIMIT 1
            """,
            telefone,
        )
        if fazenda is None:
            # Tentativa secundária: telefone cadastrado direto no cliente
            fazenda = await con.fetchrow(
                """
                SELECT f.id   AS fazenda_id,
                       f.nome AS fazenda,
                       f.area_util_ha,
                       f.tem_irrigacao,
                       f.nivel_tecnologico,
                       c.nome AS nome
                FROM clientes c
                JOIN fazendas f ON f.cliente_id = c.id AND f.ativa
                WHERE c.telefone = $1
                ORDER BY f.criado_em
                LIMIT 1
                """,
                telefone,
            )
        if fazenda is None:
            return {}

        fazenda_id = fazenda["fazenda_id"]
        sistema = ("irrigado" if fazenda["tem_irrigacao"]
                   or (fazenda["nivel_tecnologico"] or "").endswith("irrigado")
                   else "sequeiro")

        ctx = {
            "nome": fazenda["nome"],
            "fazenda": fazenda["fazenda"],
            "sistema_predominante": sistema,
        }
        # Só inclui area_ha quando há valor — chave None anularia o default do motor
        if fazenda["area_util_ha"]:
            ctx["area_ha"] = float(fazenda["area_util_ha"])

        # 2. Forrageira predominante (pivôs/módulos da fazenda)
        forrageira = await con.fetchval(
            """
            SELECT forrageira FROM (
                SELECT forrageira FROM pivocentrais
                WHERE fazenda_id = $1 AND forrageira IS NOT NULL
                  AND forrageira NOT ILIKE '%formação%'
                UNION ALL
                SELECT forrageira FROM modulos
                WHERE fazenda_id = $1 AND forrageira IS NOT NULL
            ) t
            GROUP BY forrageira
            ORDER BY COUNT(*) DESC
            LIMIT 1
            """,
            fazenda_id,
        )
        if forrageira:
            ctx["forrageira"] = forrageira

        # 3. GMD histórico por sexo+sistema (aprende dos giros finalizados)
        gmds = await con.fetch(
            """
            SELECT l.sexo, l.sistema_hidrico, AVG(gr.gmd_real)::float AS gmd
            FROM giro_resultados gr
            JOIN giros g ON g.id = gr.giro_id
            JOIN lotes l ON l.id = g.lote_id
            WHERE gr.fazenda_id = $1 AND gr.gmd_real IS NOT NULL
              AND l.sexo IN ('macho','femea')
            GROUP BY l.sexo, l.sistema_hidrico
            """,
            fazenda_id,
        )
        for row in gmds:
            ctx[f"gmd_historico_{row['sexo']}_{row['sistema_hidrico']}"] = round(row["gmd"], 3)

        # 4. Custos e lotação médios dos giros da fazenda
        custos = await con.fetchrow(
            """
            SELECT AVG(custo_mdo_cab_mes)::float          AS custo_mdo,
                   AVG(custo_gastos_prod_cab_mes)::float  AS custo_gastos,
                   AVG(custo_arrendamento_ua_mes)::float  AS arrendamento,
                   AVG(lotacao_ua_ha)::float              AS lotacao
            FROM giros
            WHERE fazenda_id = $1
            """,
            fazenda_id,
        )
        if custos and custos["custo_mdo"] is not None:
            ctx["custo_mdo_cab_mes"] = round(custos["custo_mdo"], 2)
        if custos and custos["custo_gastos"] is not None:
            ctx["custo_gastos_prod_cab_mes"] = round(custos["custo_gastos"], 2)
        if custos and custos["arrendamento"] is not None:
            ctx["preco_arrendamento"] = round(custos["arrendamento"], 2)
        if custos and custos["lotacao"] is not None:
            ctx["lotacao_media_ua_ha"] = round(custos["lotacao"], 2)

        # 5. Último giro realizado
        ultimo = await con.fetchrow(
            """
            SELECT l.raca_predominante, l.sexo,
                   g.peso_entrada_kg, gr.peso_final_kg,
                   gr.dias_giro_real, gr.gmd_real,
                   gr.margem_cab_real, gr.rentabilidade_am_real
            FROM giro_resultados gr
            JOIN giros g ON g.id = gr.giro_id
            JOIN lotes l ON l.id = g.lote_id
            WHERE gr.fazenda_id = $1
            ORDER BY gr.data_finalizacao DESC
            LIMIT 1
            """,
            fazenda_id,
        )
        if ultimo:
            raca = (ultimo["raca_predominante"] or "").strip().title()
            sexo = ultimo["sexo"] or ""
            ctx["ultimo_giro"] = {
                "categoria": f"{raca} {sexo}".strip(),
                "peso_entrada": float(ultimo["peso_entrada_kg"]) if ultimo["peso_entrada_kg"] else None,
                "peso_saida": float(ultimo["peso_final_kg"]) if ultimo["peso_final_kg"] else None,
                "dias": ultimo["dias_giro_real"],
                "gmd_real": float(ultimo["gmd_real"]) if ultimo["gmd_real"] else None,
                "margem_cab": float(ultimo["margem_cab_real"]) if ultimo["margem_cab_real"] else None,
                "rent_am": float(ultimo["rentabilidade_am_real"]) if ultimo["rentabilidade_am_real"] else None,
            }

        return ctx


# ─────────────────────────────────────────────────────────────
# MOTOR DE RESPOSTA PRINCIPAL
# ─────────────────────────────────────────────────────────────

async def processar_mensagem(
    conteudo: str,                    # texto ou transcrição do áudio
    telefone: str,                    # para buscar contexto do cliente
    sessao_contexto: dict = None,     # dados acumulados na conversa
    imagem_descricao: str = None,     # descrição extraída de foto
) -> dict:
    """
    Processa a mensagem e gera resposta completa.
    Retorna: {resposta, cenarios, contexto_atualizado, pergunta_refinamento}
    """

    sessao = sessao_contexto or {}

    # ── 1. Buscar contexto do cliente ─────────────────────────
    cliente = await buscar_contexto_cliente(telefone)
    tem_historico = bool(cliente)

    # ── 2. Combinar texto + imagem se houver foto ─────────────
    texto_completo = conteudo
    if imagem_descricao:
        texto_completo = f"{conteudo}\n[Da foto]: {imagem_descricao}"

    # ── 3. Parsear dados da mensagem ──────────────────────────
    dados_msg = parsear_mensagem_whatsapp(texto_completo)
    dados_encontrados = dados_msg["dados_encontrados"]

    # Merge com contexto da sessão (dados anteriores da conversa)
    dados_merged = {**sessao, **dados_encontrados}

    # ── 4. Preencher lacunas com dados do cliente ou defaults ─
    sistema_h = SistemaHidrico(dados_merged.get("sistema_hidrico",
        cliente.get("sistema_predominante", "sequeiro")))
    sistema_p = SistemaProducao(dados_merged.get("sistema_producao", "engorda"))
    sexo      = Sexo(dados_merged.get("sexo", "macho"))
    raca      = dados_merged.get("raca", "nelore")

    # GMD: histórico do cliente > dado da mensagem > default da tabela
    gmd = (
        cliente.get(f"gmd_historico_{sexo.value}_{sistema_h.value}")
        or dados_merged.get("gmd_esperado", 0)
        or 0
    )

    # ── 5. Verificar se tem dados suficientes para calcular ───
    tem_peso   = "peso_entrada_kg" in dados_merged
    tem_preco  = any(k in dados_merged for k in
                     ["preco_compra_kg", "preco_compra_arroba", "valor_animal_mercado"])

    cenarios = None
    resumo_calculo = None

    if tem_peso and tem_preco:
        try:
            # Preço de venda: do cliente, da mensagem, ou pede ao usuário
            preco_venda = dados_merged.get("preco_venda_arroba", 0)
            if not preco_venda:
                # Usar preço médio de mercado como default
                preco_venda = 280  # TODO: puxar do banco de preços em tempo real

            entrada = EntradaGiro(
                peso_entrada_kg=dados_merged["peso_entrada_kg"],
                preco_compra_kg=dados_merged.get("preco_compra_kg"),
                preco_compra_arroba=dados_merged.get("preco_compra_arroba"),
                valor_animal_mercado=dados_merged.get("valor_animal_mercado"),
                preco_venda_arroba=preco_venda,
                dias_giro=dados_merged.get("dias_giro", 90),
                gmd_esperado=gmd,
                area_ha=dados_merged.get("area_ha", cliente.get("area_ha", 100)),
                lotacao_ua_ha=dados_merged.get("lotacao_ua_ha",
                              cliente.get("lotacao_media_ua_ha", 1.2)),
                sistema_hidrico=sistema_h,
                sistema_producao=sistema_p,
                sexo=sexo,
                raca=raca,
                frete_cab=dados_merged.get("frete_cab", 0),
                comissao_pct=dados_merged.get("comissao_pct", 0),
                custo_mdo_cab_mes=cliente.get("custo_mdo_cab_mes", 20),
                custo_gastos_prod_cab_mes=cliente.get("custo_gastos_prod_cab_mes", 20),
                custo_arrendamento_ua_mes=cliente.get("preco_arrendamento", 0),
                fator_ajuste_climatico=dados_merged.get("fator_ajuste_climatico", 1.0),
            )
            cenarios = gerar_todos_cenarios(entrada)
            base = cenarios[0]
            pessimista = cenarios[3]

            resumo_calculo = {
                "semaforo": "🟢" if base.score_viabilidade >= 66 else
                            ("🟡" if base.score_viabilidade >= 41 else "🔴"),
                "score": base.score_viabilidade,
                "classificacao": base.classificacao_viabilidade,
                "n_animais": base.n_animais,
                "peso_saida": base.peso_saida_kg,
                "gmd_usado": base.gmd,
                "fonte_gmd": "histórico da fazenda" if tem_historico and gmd else "estimativa",
                "preco_entrada": base.preco_entrada_resumo,
                "custo_arroba": base.custo_arroba_produzida,
                "margem_cab": base.margem_cab,
                "lucro_base": base.lucro_liquido,
                "lucro_pessimista": pessimista.lucro_liquido,
                "rent_am": base.rentabilidade_am,
                "pior_positivo": pessimista.lucro_liquido > 0,
                "preco_equilibrio": round(
                    (base.custo_compra_cab + base.custo_operacional_cab) / base.peso_saida_arroba, 2
                ),
                "usou_dados_cliente": tem_historico,
            }
        except Exception as e:
            resumo_calculo = {"erro": str(e)}

    # ── 6. Gerar resposta com Claude ──────────────────────────
    contexto_para_claude = _montar_contexto(
        mensagem=texto_completo,
        cliente=cliente,
        dados_encontrados=dados_merged,
        resumo=resumo_calculo,
        confianca=dados_msg["confianca"],
        dados_faltando=dados_msg["dados_faltando"],
    )

    resposta_texto = _chamar_claude(
        messages=[{"role": "user", "content": contexto_para_claude}],
        max_tokens=400,
        system=SYSTEM_PROMPT,
    )

    # ── 7. Atualizar contexto da sessão ───────────────────────
    contexto_atualizado = {**sessao, **dados_encontrados}
    if resumo_calculo and "erro" not in resumo_calculo:
        contexto_atualizado["ultimo_calculo"] = resumo_calculo

    return {
        "resposta":           resposta_texto,
        "cenarios":           [asdict(c) for c in cenarios] if cenarios else None,
        "resumo":             resumo_calculo,
        "contexto_sessao":    contexto_atualizado,
        "confianca":          dados_msg["confianca"],
        "dados_faltando":     dados_msg["dados_faltando"],
        "usou_cliente":       tem_historico,
    }


def _montar_contexto(mensagem, cliente, dados_encontrados,
                     resumo, confianca, dados_faltando) -> str:
    """Monta o prompt de contexto para o Claude gerar a resposta."""

    partes = [f'Mensagem do produtor: "{mensagem}"\n']

    if cliente:
        partes.append(
            f"Cliente: {cliente.get('nome')} | Fazenda: {cliente.get('fazenda')} | "
            f"Sistema: {cliente.get('sistema_predominante')} | "
            f"GMD histórico macho: {cliente.get('gmd_historico_macho_irrigado', 'não registrado')}"
        )
        ultimo = cliente.get("ultimo_giro")
        if ultimo:
            partes.append(
                f"Último giro dele: {ultimo['categoria']} "
                f"{ultimo['peso_entrada']}→{ultimo['peso_saida']}kg, "
                f"GMD {ultimo['gmd_real']}, margem R${ultimo['margem_cab']}/cab"
            )
    else:
        partes.append("Cliente não cadastrado — usar dados genéricos.")

    if resumo and "erro" not in resumo:
        partes.append(f"""
Resultado do cálculo:
  {resumo['semaforo']} {resumo['classificacao']} (score {resumo['score']:.0f}/100)
  Preço entrada: R${resumo['preco_entrada']['preco_arroba']:.0f}/@ 
               = R${resumo['preco_entrada']['custo_total_cab']:.0f}/cab (com frete/comissão)
  GMD usado: {resumo['gmd_usado']} kg/dia ({resumo['fonte_gmd']})
  Peso saída: {resumo['peso_saida']} kg
  Custo @ produzida: R${resumo['custo_arroba']:.0f}
  Margem/cab: R${resumo['margem_cab']:.0f}
  Lucro base: R${resumo['lucro_base']:,.0f}
  Lucro pessimista: R${resumo['lucro_pessimista']:,.0f} ({'positivo ✓' if resumo['pior_positivo'] else 'NEGATIVO ✗'})
  Rentabilidade: {resumo['rent_am']:.1f}% a.m.
  Ponto de equilíbrio: R${resumo['preco_equilibrio']:.0f}/@
""")
    elif resumo and "erro" in resumo:
        partes.append(f"Não consegui calcular: {resumo['erro']}")
    else:
        partes.append(f"Dados insuficientes para calcular. Confiança: {confianca}")
        if dados_faltando:
            partes.append(f"Faltando: {', '.join(dados_faltando)}")

    partes.append(
        "\nGere a resposta do consultor para o WhatsApp. "
        "Se calculou, mostre os números principais e dê a recomendação. "
        "Feche com UMA pergunta para refinar se necessário. "
        "Máximo 5 linhas no total."
    )

    return "\n".join(partes)


# ─────────────────────────────────────────────────────────────
# WEBHOOK WHATSAPP — recebe e roteia mensagens
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()

# Armazena sessões em memória (substituir por Redis em produção)
_sessoes: dict[str, dict] = {}


@router.get("/webhook", response_class=PlainTextResponse)
async def verificar_webhook(request: Request):
    """Verificação do webhook Meta Cloud API."""
    params = dict(request.query_params)
    token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "bovturn2026")
    if (params.get("hub.mode") == "subscribe" and
            params.get("hub.verify_token") == token):
        return params.get("hub.challenge", "")
    raise HTTPException(403, "Token inválido")


@router.post("/webhook")
async def receber_mensagem(request: Request):
    """
    Recebe mensagens do WhatsApp via Meta Cloud API.
    Rota todas as mensagens pelo agente.
    """
    body = await request.json()

    try:
        entry    = body["entry"][0]
        changes  = entry["changes"][0]
        value    = changes["value"]
        mensagem = value["messages"][0]

        telefone = mensagem["from"]
        tipo     = mensagem["type"]
        sessao   = _sessoes.get(telefone, {})

        # ── Rotear por tipo de mensagem ───────────────────────
        if tipo == "text":
            texto = mensagem["text"]["body"]
            resultado = await processar_mensagem(texto, telefone, sessao)

        elif tipo == "audio":
            # Baixar e transcrever o áudio
            audio_id = mensagem["audio"]["id"]
            audio_bytes = _baixar_midia_whatsapp(audio_id)
            texto = transcrever_audio(audio_bytes, "ogg")
            resultado = await processar_mensagem(texto, telefone, sessao)

        elif tipo == "image":
            # Analisar a foto (leilão, catálogo, pasto...)
            image_id = mensagem["image"]["id"]
            img_bytes = _baixar_midia_whatsapp(image_id)
            img_b64   = base64.b64encode(img_bytes).decode()
            descricao = analisar_imagem_leilao(img_b64)
            caption   = mensagem["image"].get("caption", "")
            resultado = await processar_mensagem(caption, telefone, sessao,
                                                 imagem_descricao=descricao)
        else:
            return {"status": "tipo não suportado"}

        # ── Salvar sessão e enviar resposta ───────────────────
        _sessoes[telefone] = resultado["contexto_sessao"]
        await _enviar_whatsapp(telefone, resultado["resposta"])

        return {"status": "ok"}

    except (KeyError, IndexError):
        return {"status": "ok"}  # Meta exige 200 mesmo em erros


def _baixar_midia_whatsapp(media_id: str) -> bytes:
    """Baixa mídia do WhatsApp via API."""
    import httpx
    token = os.environ.get("WHATSAPP_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}

    # Primeiro pega a URL
    r = httpx.get(f"https://graph.facebook.com/v18.0/{media_id}", headers=headers)
    url = r.json()["url"]

    # Depois baixa o arquivo
    r2 = httpx.get(url, headers=headers)
    return r2.content


async def _enviar_whatsapp(telefone: str, mensagem: str):
    """Envia resposta de texto via Meta Cloud API."""
    import httpx
    token   = os.environ.get("WHATSAPP_TOKEN")
    phone_id= os.environ.get("WHATSAPP_PHONE_ID")

    async with httpx.AsyncClient() as client:
        await client.post(
            f"https://graph.facebook.com/v18.0/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={
                "messaging_product": "whatsapp",
                "to": telefone,
                "type": "text",
                "text": {"body": mensagem}
            }
        )


# ─────────────────────────────────────────────────────────────
# ENDPOINT DE TESTE — simula uma mensagem sem WhatsApp real
# ─────────────────────────────────────────────────────────────

@router.post("/testar")
async def testar_agente(body: dict):
    """
    Testa o agente sem precisar do WhatsApp.
    Útil para desenvolvimento e para o consultor avaliar as respostas.

    Body: {"mensagem": "...", "telefone": "...", "sessao": {}}
    """
    resultado = await processar_mensagem(
        conteudo=body.get("mensagem", ""),
        telefone=body.get("telefone", "+5500000000000"),
        sessao_contexto=body.get("sessao", {}),
    )
    return resultado
