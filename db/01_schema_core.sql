-- ============================================================
-- BOVTURN INTELLIGENCE — Schema PostgreSQL + TimescaleDB
-- Versão 1.0 | Espelha o V15 BZBM + BPs + Power BI VPAgro
-- ============================================================
-- Execute na ordem: 01 → 02 → 03 → 04
-- Requisito: PostgreSQL 16 + extensão TimescaleDB
-- ============================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm; -- busca de texto

-- ============================================================
-- BLOCO 1: CADASTROS BASE
-- Espelha aba "Cadastros" e "Listas" do V15 BZBM
-- ============================================================

-- Clientes / proprietários (o consultor atende vários)
CREATE TABLE clientes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome            TEXT NOT NULL,
    documento       TEXT,          -- CPF ou CNPJ
    telefone        TEXT,
    email           TEXT,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Fazendas (uma por cliente ou múltiplas)
CREATE TABLE fazendas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id),
    nome            TEXT NOT NULL,
    municipio       TEXT,
    estado          CHAR(2),
    bioma           TEXT,          -- Cerrado, Amazônia, Pantanal, Caatinga, Mata Atlântica, Pampa
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6),
    area_total_ha   NUMERIC(10,2),
    area_util_ha    NUMERIC(10,2), -- área utilizável para pecuária
    nivel_tecnologico TEXT CHECK (nivel_tecnologico IN (
                        'extensivo','semi_intensivo','intensivo_sequeiro',
                        'intensivo_irrigado','confinamento')),
    tem_irrigacao   BOOLEAN DEFAULT FALSE,
    tem_confinamento BOOLEAN DEFAULT FALSE,
    tem_silagem     BOOLEAN DEFAULT FALSE,
    ativa           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Pivôs de irrigação (espelha aba "Cadastros" do V15 BZBM)
CREATE TABLE pivocentrais (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    nome            TEXT NOT NULL,          -- "Pivô 3", "Pivô 4"
    area_ha         NUMERIC(8,2),
    potencia_bomba_cv NUMERIC(6,1),
    consumo_energia_kwh_mes NUMERIC(8,2),
    forrageira      TEXT,
    status          TEXT DEFAULT 'ativo',   -- ativo, formação, reforma
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Módulos / piquetes (dentro dos pivôs ou áreas sequeiro)
CREATE TABLE modulos (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    pivocentral_id  UUID REFERENCES pivocentrais(id), -- NULL se sequeiro
    identificacao   TEXT NOT NULL,          -- "Módulo A", "Sede 1", "Pasto 8"
    area_ha         NUMERIC(8,2),
    aee_pct         NUMERIC(5,2),           -- aproveitamento efetivo de estoque
    aee_ha          NUMERIC(8,2),           -- área efetivamente explorada
    forrageira      TEXT,                   -- Miyagui, Mombaça, Ruziziensis, Marandu...
    uso_atual       TEXT CHECK (uso_atual IN (
                        'pastejo_irrigado','formacao','intensivo_sequeiro',
                        'semi_intensivo','extensivo','pulmao','silagem',
                        'diferimento','ilp','confinamento')),
    ativa           BOOLEAN DEFAULT TRUE
);

-- Funcionários por fazenda (espelha aba MÃO DE OBRA dos BPs)
CREATE TABLE funcionarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    funcao          TEXT NOT NULL,          -- "Gerente", "Vaqueiro", "Tratador"...
    remuneracao_mensal NUMERIC(10,2),
    encargos_pct    NUMERIC(5,2) DEFAULT 0.40,
    rateio_pct      NUMERIC(5,2) DEFAULT 1.0, -- quanto é rateado para pecuária
    ativo           BOOLEAN DEFAULT TRUE
);

-- ============================================================
-- BLOCO 2: REBANHO
-- Espelha abas "Rebanho atual", "Conferência Raças", "Rebanho projetado"
-- ============================================================

-- Categorias (espelha aba CATEGORIAS do V15 BZBM)
CREATE TABLE categorias_animal (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome            TEXT NOT NULL,          -- "Bezerro", "Garrote", "Boi Magro", "Boi Gordo"
    sexo            TEXT CHECK (sexo IN ('macho','femea','ambos')),
    peso_min_kg     NUMERIC(6,1),
    peso_max_kg     NUMERIC(6,1),
    peso_medio_kg   NUMERIC(6,1),
    peso_medio_ua   NUMERIC(5,3),           -- Peso médio em UA (peso/450)
    gmd_referencia  NUMERIC(4,3),           -- GMD de referência para essa categoria
    tempo_giro_meses NUMERIC(4,1)
);

-- Dados de referência iniciais (baseados no V15 BZBM)
INSERT INTO categorias_animal (nome, sexo, peso_min_kg, peso_max_kg, peso_medio_kg, peso_medio_ua, gmd_referencia, tempo_giro_meses) VALUES
('Bezerro',   'macho',  40,  260, 150, 0.333, 0.70, 10.3),
('Garrote',   'macho',  261, 360, 310, 0.689, 0.85,  3.9),
('Boi Magro', 'macho',  361, 390, 375, 0.833, 0.90,  1.1),
('Boi Gordo', 'macho',  391, 560, 475, 1.056, 0.70,  8.0),
('Bezerra',   'femea',  40,  260, 150, 0.333, 0.65, 12.0),
('Novilha',   'femea',  261, 360, 310, 0.689, 0.75,  4.4),
('Vaca',      'femea',  361, 500, 430, 0.956, 0.55, 12.0);

-- Registro individual de animais
-- Espelha "Rebanho atual" e "Conferência Raças" do V15 BZBM
-- Preparado para TimescaleDB — particionado por data_entrada
CREATE TABLE animais (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    id_usual        TEXT,                   -- número de manejo (ex: "976")
    id_eletronico   TEXT,                   -- SISBOV/brinco eletrônico
    nr_registro     TEXT,
    nome            TEXT,
    data_nascimento DATE,
    sexo            TEXT CHECK (sexo IN ('macho','femea')),
    raca            TEXT,                   -- Nelore, Cruzado, Aberdeen Angus, Guzerá...
    categoria_id    UUID REFERENCES categorias_animal(id),
    status          TEXT DEFAULT 'vivo' CHECK (status IN ('vivo','vendido','morto','transferido')),
    modulo_atual_id UUID REFERENCES modulos(id),
    data_entrada    DATE NOT NULL,
    peso_entrada_kg NUMERIC(6,1),
    tipo_entrada    TEXT CHECK (tipo_entrada IN ('compra','nascimento','transferencia')),
    fornecedor      TEXT,
    valor_compra    NUMERIC(10,2),
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Pesagens individuais (TimescaleDB — série temporal por animal)
CREATE TABLE pesagens (
    id              UUID DEFAULT uuid_generate_v4(),
    animal_id       UUID NOT NULL REFERENCES animais(id),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_pesagem    TIMESTAMPTZ NOT NULL,
    peso_kg         NUMERIC(6,1),
    modulo_id       UUID REFERENCES modulos(id),
    observacao      TEXT,
    PRIMARY KEY (id, data_pesagem)
);
-- Transformar em hipertabela TimescaleDB (partição por semana)
SELECT create_hypertable('pesagens', 'data_pesagem', if_not_exists => TRUE);

-- Vendas de animais
CREATE TABLE vendas_animais (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_venda      DATE NOT NULL,
    comprador       TEXT,
    categoria       TEXT,
    n_animais       INTEGER,
    peso_total_kg   NUMERIC(10,2),
    peso_medio_kg   NUMERIC(6,2),
    preco_kg        NUMERIC(8,2),
    preco_arroba    NUMERIC(8,2),
    valor_total     NUMERIC(12,2),
    tipo_venda      TEXT,                   -- "leilão", "direto", "frigorífico"
    observacao      TEXT,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Compras de animais
CREATE TABLE compras_animais (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_compra     DATE NOT NULL,
    vendedor        TEXT,
    categoria       TEXT,
    raca            TEXT,
    n_animais       INTEGER,
    peso_total_kg   NUMERIC(10,2),
    peso_medio_kg   NUMERIC(6,2),
    preco_kg        NUMERIC(8,2),
    preco_arroba    NUMERIC(8,2),
    valor_total     NUMERIC(12,2),
    comissao        NUMERIC(8,2),
    frete           NUMERIC(8,2),
    valor_cab       NUMERIC(10,2),          -- custo por cabeça (valor+comissao+frete)/n
    observacao      TEXT,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Mortes e morbidades
CREATE TABLE mortes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    animal_id       UUID REFERENCES animais(id),
    data_morte      DATE NOT NULL,
    causa           TEXT,
    peso_estimado   NUMERIC(6,1),
    valor_perda     NUMERIC(10,2),
    observacao      TEXT
);

CREATE TABLE morbidades (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    animal_id       UUID REFERENCES animais(id),
    data_registro   DATE NOT NULL,
    doenca          TEXT,
    tratamento      TEXT,
    custo           NUMERIC(8,2),
    recuperado      BOOLEAN,
    observacao      TEXT
);

-- ============================================================
-- BLOCO 3: GIROS (motor central)
-- Espelha lógica de todos os Excels de giro analisados
-- ============================================================

-- Lotes (grupos de animais num giro)
CREATE TABLE lotes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    nome            TEXT NOT NULL,          -- "Lote 89 setor 2", "Giro Recria Fêmea 26/27"
    safra           TEXT,                   -- "25/26", "26/27"
    sistema_producao TEXT CHECK (sistema_producao IN (
                        'recria','engorda','recria_engorda',
                        'confinamento','ciclo_completo','parceria')),
    sistema_hidrico TEXT CHECK (sistema_hidrico IN (
                        'irrigado','sequeiro','misto','confinamento')),
    sexo            TEXT CHECK (sexo IN ('macho','femea','misto')),
    raca_predominante TEXT,
    status          TEXT DEFAULT 'planejado' CHECK (status IN (
                        'planejado','ativo','finalizado','cancelado')),
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Giros planejados (o orçamento — o que foi projetado)
CREATE TABLE giros (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    lote_id         UUID NOT NULL REFERENCES lotes(id),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    modulo_id       UUID REFERENCES modulos(id),

    -- Datas
    data_inicio     DATE NOT NULL,
    data_fim_prevista DATE,
    dias_giro       INTEGER,

    -- Animal (entrada)
    n_animais       INTEGER,
    peso_entrada_kg NUMERIC(6,2),
    valor_animal_cab NUMERIC(10,2),         -- R$/cabeça já com comissão+frete
    preco_compra_arroba NUMERIC(8,2),
    idade_compra_meses INTEGER,

    -- Pastagem
    area_ha         NUMERIC(8,2),
    lotacao_ua_ha   NUMERIC(6,2),
    forrageira      TEXT,

    -- Projeções zootécnicas
    gmd_projetado   NUMERIC(4,3),
    peso_saida_projetado NUMERIC(6,2),
    rc_pct          NUMERIC(5,3) DEFAULT 0.50,

    -- Mercado
    preco_venda_arroba NUMERIC(8,2),

    -- Nutrição
    consumo_suplemento_pct_pv NUMERIC(6,4) DEFAULT 0.003,
    custo_kg_suplemento NUMERIC(6,2),
    tipo_suplemento TEXT,

    -- Custos fixos (R$/cab/mês)
    custo_mdo_cab_mes NUMERIC(8,2),
    custo_gastos_prod_cab_mes NUMERIC(8,2),
    custo_arrendamento_ua_mes NUMERIC(8,2) DEFAULT 0,
    custo_sanidade_cab_giro NUMERIC(8,2),

    -- Resultados projetados (preenchidos pelo motor de cenários)
    proj_receita_total      NUMERIC(14,2),
    proj_margem_bruta       NUMERIC(14,2),
    proj_lucro_liquido      NUMERIC(14,2),
    proj_custo_arroba       NUMERIC(8,2),
    proj_margem_cab         NUMERIC(10,2),
    proj_margem_ha          NUMERIC(10,2),
    proj_rentabilidade_am   NUMERIC(6,3),
    proj_lucratividade      NUMERIC(6,3),
    proj_arrobas_ha         NUMERIC(8,2),
    score_viabilidade       NUMERIC(5,1),
    classificacao_viabilidade TEXT,

    -- Cenários JSON (armazena todos os 6 cenários gerados)
    cenarios_json   JSONB,

    -- Fator climático na época do planejamento
    fator_climatico NUMERIC(5,3) DEFAULT 1.0,
    obs_climatica   TEXT,

    criado_em       TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Registros de acompanhamento durante o giro (TimescaleDB)
-- Espelha "Lançamento Pesagens" e "Análise Pecuária" do V15 BZBM
CREATE TABLE giro_registros (
    id              UUID DEFAULT uuid_generate_v4(),
    giro_id         UUID NOT NULL REFERENCES giros(id),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_registro   TIMESTAMPTZ NOT NULL,

    -- Pesagem do lote
    peso_medio_kg   NUMERIC(6,2),
    n_animais       INTEGER,               -- animais presentes na pesagem
    gmd_periodo     NUMERIC(4,3),          -- GMD calculado desde última pesagem

    -- Insumos lançados
    insumos_json    JSONB,                 -- {"suplemento_kg": 500, "ureia_kg": 20...}
    custo_insumos   NUMERIC(10,2),

    -- Dados climáticos do período (puxados via API automaticamente)
    clima_json      JSONB,                 -- {"chuva_mm": 85, "temp_max": 34...}

    observacao      TEXT,
    PRIMARY KEY (id, data_registro)
);
SELECT create_hypertable('giro_registros', 'data_registro', if_not_exists => TRUE);

-- Resultado final do giro (o que realmente aconteceu)
CREATE TABLE giro_resultados (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    giro_id             UUID NOT NULL UNIQUE REFERENCES giros(id),
    fazenda_id          UUID NOT NULL REFERENCES fazendas(id),
    data_finalizacao    DATE NOT NULL,

    -- Zootécnico realizado
    dias_giro_real      INTEGER,
    n_animais_final     INTEGER,
    peso_final_kg       NUMERIC(6,2),
    gmd_real            NUMERIC(4,3),
    mortalidade_pct     NUMERIC(5,3),

    -- Financeiro realizado
    preco_venda_arroba  NUMERIC(8,2),
    receita_total       NUMERIC(14,2),
    custo_total_gado    NUMERIC(14,2),
    custo_total_operacional NUMERIC(14,2),
    margem_bruta        NUMERIC(14,2),
    lucro_liquido       NUMERIC(14,2),
    custo_arroba_real   NUMERIC(8,2),
    margem_cab_real     NUMERIC(10,2),
    margem_ha_real      NUMERIC(10,2),
    rentabilidade_am_real NUMERIC(6,3),
    lucratividade_real  NUMERIC(6,3),
    arrobas_ha_real     NUMERIC(8,2),

    -- Desvios projetado x realizado
    desvio_gmd_pct      NUMERIC(6,2),
    desvio_margem_pct   NUMERIC(6,2),
    desvio_arroba_pct   NUMERIC(6,2),

    observacao          TEXT,
    criado_em           TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- BLOCO 4: NUTRIÇÃO E RAÇÃO
-- Espelha "Custo Ração", "Fábrica de Ração", "Ração" do V15 BZBM
-- ============================================================

-- Ingredientes / insumos de ração
CREATE TABLE ingredientes_racao (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome            TEXT NOT NULL,          -- "Milho fubá", "DDG", "Ureia", "Núcleo"
    custo_kg        NUMERIC(8,4),
    custo_ton       NUMERIC(10,2),
    unidade         TEXT DEFAULT 'kg',
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- Dietas (formulações de ração)
CREATE TABLE dietas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    nome            TEXT NOT NULL,          -- "Ração 0,1% PV", "Ração 0,3% Sem Dendê"
    fase            TEXT,                   -- "recria", "engorda_adaptação", "engorda_terminação"
    consumo_pct_pv  NUMERIC(6,4),
    custo_kg_final  NUMERIC(8,4),           -- custo do kg da dieta formulada
    composicao_json JSONB,                  -- {"milho": 0.48, "ddg": 0.11, "sal": 0.10...}
    ativa           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Consumo de ração por pivô/módulo (TimescaleDB)
-- Espelha "Nutrição" e "Consumo de Ração Por Pivô e Módulo" do Power BI
CREATE TABLE consumo_racao (
    id              UUID DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    modulo_id       UUID REFERENCES modulos(id),
    giro_id         UUID REFERENCES giros(id),
    data_lancamento TIMESTAMPTZ NOT NULL,
    dieta_id        UUID REFERENCES dietas(id),
    quantidade_kg   NUMERIC(10,2),
    custo_total     NUMERIC(10,2),
    consumo_pct_pv_real NUMERIC(6,4),      -- % PV realmente consumido
    score_cocho     NUMERIC(3,1),           -- 0 a 5 (Score Cocho do Power BI)
    score_fezes     NUMERIC(3,1),           -- 0 a 5 (Score Fezes do Power BI)
    PRIMARY KEY (id, data_lancamento)
);
SELECT create_hypertable('consumo_racao', 'data_lancamento', if_not_exists => TRUE);

-- ============================================================
-- BLOCO 5: PASTAGEM E ADUBAÇÃO
-- Espelha "Rebanho e Adubação", "Pastagens" do Power BI
-- e abas de orçamentação forrageira dos BPs
-- ============================================================

-- Capacidade de suporte por módulo por mês
-- Espelha tabela de UA/ha mês a mês dos BPs
CREATE TABLE capacidade_suporte (
    id              UUID DEFAULT uuid_generate_v4(),
    modulo_id       UUID NOT NULL REFERENCES modulos(id),
    competencia     TIMESTAMPTZ NOT NULL,   -- mês de referência
    lotacao_ua_ha   NUMERIC(6,2),
    n_animais       INTEGER,
    PRIMARY KEY (id, competencia)
);
SELECT create_hypertable('capacidade_suporte', 'competencia', if_not_exists => TRUE);

-- Adubações realizadas
CREATE TABLE adubacoes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    modulo_id       UUID REFERENCES modulos(id),
    data_aplicacao  DATE NOT NULL,
    safra           TEXT,
    insumo          TEXT NOT NULL,          -- "Ureia", "MAP", "KCL", "Calcário"...
    dose_ton_ha     NUMERIC(8,4),
    area_ha         NUMERIC(8,2),
    quantidade_ton  NUMERIC(10,3),
    custo_ton       NUMERIC(10,2),
    custo_total     NUMERIC(12,2),
    observacao      TEXT
);

-- ============================================================
-- BLOCO 6: FINANCEIRO
-- Espelha DFC Mensal, DFC Safra, DRE, DRE Gerencial do V15 BZBM
-- ============================================================

-- Categorias de contas (espelha "PLANO DE CONTAS" do V15 BZBM)
CREATE TABLE plano_contas (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    codigo          TEXT,
    descricao       TEXT NOT NULL,
    tipo            TEXT CHECK (tipo IN ('receita','despesa','investimento')),
    grupo           TEXT                    -- "Nutrição", "MDO", "Gastos de Produção"...
);

-- Lançamentos financeiros (TimescaleDB)
-- Espelha "Despesas", "Entrada de Produtos", DFC do V15 BZBM
CREATE TABLE lancamentos (
    id              UUID DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_lancamento TIMESTAMPTZ NOT NULL,
    conta_id        UUID REFERENCES plano_contas(id),
    descricao       TEXT NOT NULL,
    tipo            TEXT CHECK (tipo IN ('receita','despesa','investimento')),
    valor           NUMERIC(12,2),
    giro_id         UUID REFERENCES giros(id),   -- vincula ao giro, se aplicável
    modulo_id       UUID REFERENCES modulos(id),
    forma_pagamento TEXT,
    observacao      TEXT,
    PRIMARY KEY (id, data_lancamento)
);
SELECT create_hypertable('lancamentos', 'data_lancamento', if_not_exists => TRUE);

-- Estoque de materiais
-- Espelha aba "Estoque" do V15 BZBM
CREATE TABLE estoque (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    produto         TEXT NOT NULL,
    categoria       TEXT,                   -- "Adubo", "Ração", "Medicamento", "Combustível"
    unidade         TEXT,
    quantidade_atual NUMERIC(12,3),
    preco_unitario  NUMERIC(10,4),
    valor_estoque   NUMERIC(12,2),
    atualizado_em   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- BLOCO 7: CLIMA (TimescaleDB — séries temporais)
-- Motor climático NOAA + ECMWF + INMET + Open-Meteo
-- ============================================================

-- Série climática histórica por coordenada
CREATE TABLE clima_serie (
    id              UUID DEFAULT uuid_generate_v4(),
    lat             NUMERIC(9,6) NOT NULL,
    lng             NUMERIC(9,6) NOT NULL,
    data            TIMESTAMPTZ NOT NULL,
    temp_max        NUMERIC(5,2),
    temp_min        NUMERIC(5,2),
    temp_media      NUMERIC(5,2),
    precipitacao_mm NUMERIC(7,2),
    umidade_pct     NUMERIC(5,2),
    radiacao_solar  NUMERIC(8,2),
    fonte           TEXT,                   -- "open-meteo", "inmet", "era5"
    PRIMARY KEY (id, data)
);
SELECT create_hypertable('clima_serie', 'data', if_not_exists => TRUE);

-- Índices oceânicos (NOAA — atualizado mensalmente)
CREATE TABLE indices_oceanicos (
    id              UUID DEFAULT uuid_generate_v4(),
    data            TIMESTAMPTZ NOT NULL,
    oni_index       NUMERIC(5,2),           -- El Niño/La Niña: > +0.5 = El Niño
    pdo_index       NUMERIC(5,2),           -- Oscilação Decadal do Pacífico
    amo_index       NUMERIC(5,2),           -- Oscilação Multidecadal do Atlântico
    classificacao   TEXT CHECK (classificacao IN (
                        'elnino_forte','elnino_fraco','neutro',
                        'lanina_fraca','lanina_forte')),
    fonte           TEXT DEFAULT 'noaa_cpc',
    PRIMARY KEY (id, data)
);
SELECT create_hypertable('indices_oceanicos', 'data', if_not_exists => TRUE);

-- Previsões climáticas por fazenda (cache 6h — Open-Meteo 16 dias)
CREATE TABLE clima_previsao (
    id              UUID DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    data_previsao   TIMESTAMPTZ NOT NULL,
    data_geracao    TIMESTAMPTZ DEFAULT NOW(),
    previsao_json   JSONB,                  -- dados completos dos 16 dias
    prob_chuva_adequada NUMERIC(5,2),       -- probabilidade de chuva adequada no período
    risco_veranico  TEXT CHECK (risco_veranico IN ('baixo','moderado','alto','critico')),
    fator_ajuste_gmd NUMERIC(5,3),          -- fator climático para o motor de cenários
    PRIMARY KEY (id, data_previsao)
);
SELECT create_hypertable('clima_previsao', 'data_previsao', if_not_exists => TRUE);

-- ============================================================
-- BLOCO 8: MERCADO (TimescaleDB)
-- CEPEA/Esalq, B3, câmbio — atualizado diariamente
-- ============================================================

CREATE TABLE precos_mercado (
    id              UUID DEFAULT uuid_generate_v4(),
    data            TIMESTAMPTZ NOT NULL,
    produto         TEXT NOT NULL,          -- "boi_gordo","bezerro","milho","ureia","soja"
    preco           NUMERIC(12,4),
    unidade         TEXT,                   -- "@", "sc", "ton", "kg"
    regiao          TEXT,                   -- "Centro-Oeste", "São Paulo"
    fonte           TEXT,                   -- "cepea", "b3", "ptax"
    PRIMARY KEY (id, data)
);
SELECT create_hypertable('precos_mercado', 'data', if_not_exists => TRUE);

-- ============================================================
-- BLOCO 9: WHATSAPP IA
-- Sessões e mensagens do assistente conversacional
-- ============================================================

-- Usuários do WhatsApp (produtores)
CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fazenda_id      UUID NOT NULL REFERENCES fazendas(id),
    nome            TEXT,
    telefone        TEXT UNIQUE NOT NULL,
    perfil          TEXT CHECK (perfil IN ('gestor','produtor')) DEFAULT 'produtor',
    ativo           BOOLEAN DEFAULT TRUE,
    criado_em       TIMESTAMPTZ DEFAULT NOW()
);

-- Sessões de conversa (WhatsApp)
CREATE TABLE sessoes_whatsapp (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id      UUID NOT NULL REFERENCES usuarios(id),
    giro_id         UUID REFERENCES giros(id), -- giro em análise, se houver
    contexto_json   JSONB,                      -- dados coletados progressivamente
    nivel_confianca TEXT CHECK (nivel_confianca IN ('baixo','medio','alto')),
    iniciado_em     TIMESTAMPTZ DEFAULT NOW(),
    ultima_interacao TIMESTAMPTZ,
    expira_em       TIMESTAMPTZ
);

-- Mensagens trocadas
CREATE TABLE mensagens_whatsapp (
    id              UUID DEFAULT uuid_generate_v4(),
    sessao_id       UUID NOT NULL REFERENCES sessoes_whatsapp(id),
    data_mensagem   TIMESTAMPTZ NOT NULL,
    direcao         TEXT CHECK (direcao IN ('entrada','saida')),
    tipo_conteudo   TEXT CHECK (tipo_conteudo IN ('texto','audio','imagem')),
    conteudo_raw    TEXT,
    transcricao     TEXT,                   -- resultado do Whisper, se áudio
    entidades_json  JSONB,                  -- dados extraídos pelo Claude
    analise_json    JSONB,                  -- resultado da análise de giro
    tokens_usados   INTEGER,
    PRIMARY KEY (id, data_mensagem)
);
SELECT create_hypertable('mensagens_whatsapp', 'data_mensagem', if_not_exists => TRUE);

-- ============================================================
-- ÍNDICES — performance para consultas frequentes
-- ============================================================

CREATE INDEX idx_fazendas_cliente ON fazendas(cliente_id);
CREATE INDEX idx_modulos_fazenda  ON modulos(fazenda_id);
CREATE INDEX idx_animais_fazenda  ON animais(fazenda_id);
CREATE INDEX idx_animais_status   ON animais(status);
CREATE INDEX idx_giros_fazenda    ON giros(fazenda_id);
CREATE INDEX idx_giros_status     ON lotes(status);
CREATE INDEX idx_lancamentos_giro ON lancamentos(giro_id) WHERE giro_id IS NOT NULL;
CREATE INDEX idx_precos_produto   ON precos_mercado(produto, data DESC);
CREATE INDEX idx_clima_coord      ON clima_serie(lat, lng, data DESC);

-- Índice GIN para busca dentro dos JSONBs
CREATE INDEX idx_giros_cenarios   ON giros USING GIN(cenarios_json);
CREATE INDEX idx_sessao_contexto  ON sessoes_whatsapp USING GIN(contexto_json);

-- ============================================================
-- VIEW: Painel rápido por giro (espelha o PAINEL do Power BI)
-- ============================================================

CREATE VIEW vw_painel_giros AS
SELECT
    g.id,
    f.nome AS fazenda,
    l.nome AS lote,
    l.safra,
    l.sistema_producao,
    l.sistema_hidrico,
    g.data_inicio,
    g.data_fim_prevista,
    g.dias_giro,
    g.n_animais,
    g.peso_entrada_kg,
    g.gmd_projetado,
    g.score_viabilidade,
    g.classificacao_viabilidade,
    g.proj_receita_total,
    g.proj_lucro_liquido,
    g.proj_margem_cab,
    g.proj_margem_ha,
    g.proj_rentabilidade_am,
    g.proj_arrobas_ha,
    -- Resultado real (quando finalizado)
    gr.dias_giro_real,
    gr.gmd_real,
    gr.receita_total AS receita_real,
    gr.lucro_liquido AS lucro_real,
    gr.margem_cab_real,
    gr.desvio_gmd_pct,
    gr.desvio_margem_pct,
    l.status
FROM giros g
JOIN lotes l ON g.lote_id = l.id
JOIN fazendas f ON g.fazenda_id = f.id
LEFT JOIN giro_resultados gr ON g.id = gr.giro_id;

COMMENT ON VIEW vw_painel_giros IS 
'Painel consolidado de giros — espelha o PAINEL e DRE Gerencial do Power BI VPAgro';

