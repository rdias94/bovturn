-- ============================================================
-- MIGRAÇÃO VPAgro — Primeiro cliente / dados de referência
-- Baseado nos arquivos V15 BZBM e Controle VPAgro
-- ============================================================

-- Cliente VPAgro
INSERT INTO clientes (id, nome) VALUES
('00000000-0000-0000-0000-000000000001', 'VPAgro');

-- Fazenda VPAgro (dados do V15 BZBM)
INSERT INTO fazendas (id, cliente_id, nome, estado, bioma,
    area_total_ha, nivel_tecnologico, tem_irrigacao) VALUES
('00000000-0000-0000-0000-000000000002',
 '00000000-0000-0000-0000-000000000001',
 'Fazenda VPAgro', 'PA', 'Amazônia',
 589.79, 'intensivo_irrigado', TRUE);

-- Pivôs (dados do V15 BZBM: Premissas e Referências)
INSERT INTO pivocentrais (fazenda_id, nome, area_ha, forrageira) VALUES
('00000000-0000-0000-0000-000000000002', 'Pivô 3', 74.8,  'Miyagui'),
('00000000-0000-0000-0000-000000000002', 'Pivô 4', 100.0, 'Miyagui'),
('00000000-0000-0000-0000-000000000002', 'Pivô 5', 100.0, 'Miyagui'),
('00000000-0000-0000-0000-000000000002', 'Pivô 6', 0.0,   'Em formação');

-- Ingredientes de ração (do V15 BZBM — aba Custo Ração)
INSERT INTO ingredientes_racao (nome, custo_kg, custo_ton) VALUES
('Milho fubá',              1.10,  1100.00),
('DDG',                     1.40,  1400.00),
('Sal branco',              0.70,   700.00),
('Ureia',                   4.00,  4000.00),
('Núcleo mineral',          5.80,  5800.00),
('Farelo de soja',          2.73,  2728.89),
('Silagem de capim',        0.34,   340.00),
('Sorgo moído',             0.65,   652.20),
('Grão reidratado',         0.43,   425.00);

-- Dietas base (do V15 BZBM e BPs)
-- Será vinculada à fazenda após inserção

