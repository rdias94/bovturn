-- ============================================================
-- SEED do AGENTE — torna o VPAgro consultável pelo telefone
-- e popula histórico real de giros para o agente "aprender".
-- Depende de: 01_schema_core.sql + 02_dados_vpagro.sql
-- Idempotente (ON CONFLICT / WHERE NOT EXISTS).
-- ============================================================

-- Telefone do produtor → fazenda VPAgro
INSERT INTO usuarios (id, fazenda_id, nome, telefone, perfil)
VALUES ('00000000-0000-0000-0000-0000000000a1',
        '00000000-0000-0000-0000-000000000002',
        'Riesley', '+5565999999999', 'gestor')
ON CONFLICT (telefone) DO UPDATE
    SET fazenda_id = EXCLUDED.fazenda_id, nome = EXCLUDED.nome;

-- ── Lote + giro + resultado: Nelore MACHO irrigado (GMD real 0.83) ──
INSERT INTO lotes (id, fazenda_id, nome, safra, sistema_producao,
                   sistema_hidrico, sexo, raca_predominante, status)
VALUES ('00000000-0000-0000-0000-0000000000b1',
        '00000000-0000-0000-0000-000000000002',
        'Recria/Engorda Macho 24/25', '24/25', 'recria_engorda',
        'irrigado', 'macho', 'Nelore', 'finalizado')
ON CONFLICT (id) DO NOTHING;

INSERT INTO giros (id, lote_id, fazenda_id, data_inicio, dias_giro,
                   n_animais, peso_entrada_kg, gmd_projetado,
                   lotacao_ua_ha, custo_mdo_cab_mes,
                   custo_gastos_prod_cab_mes, custo_arrendamento_ua_mes)
VALUES ('00000000-0000-0000-0000-0000000000c1',
        '00000000-0000-0000-0000-0000000000b1',
        '00000000-0000-0000-0000-000000000002',
        DATE '2024-05-01', 240, 50, 220, 0.85,
        10.0, 9.86, 41.48, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO giro_resultados (id, giro_id, fazenda_id, data_finalizacao,
                             dias_giro_real, n_animais_final, peso_final_kg,
                             gmd_real, margem_cab_real, rentabilidade_am_real)
VALUES ('00000000-0000-0000-0000-0000000000d1',
        '00000000-0000-0000-0000-0000000000c1',
        '00000000-0000-0000-0000-000000000002',
        DATE '2025-01-01', 240, 50, 420,
        0.83, 1148, 5.6)
ON CONFLICT (giro_id) DO NOTHING;

-- ── Lote + giro + resultado: Nelore FÊMEA irrigado (GMD real 0.72) ──
INSERT INTO lotes (id, fazenda_id, nome, safra, sistema_producao,
                   sistema_hidrico, sexo, raca_predominante, status)
VALUES ('00000000-0000-0000-0000-0000000000b2',
        '00000000-0000-0000-0000-000000000002',
        'Recria Fêmea 24/25', '24/25', 'recria',
        'irrigado', 'femea', 'Nelore', 'finalizado')
ON CONFLICT (id) DO NOTHING;

INSERT INTO giros (id, lote_id, fazenda_id, data_inicio, dias_giro,
                   n_animais, peso_entrada_kg, gmd_projetado,
                   lotacao_ua_ha, custo_mdo_cab_mes,
                   custo_gastos_prod_cab_mes, custo_arrendamento_ua_mes)
VALUES ('00000000-0000-0000-0000-0000000000c2',
        '00000000-0000-0000-0000-0000000000b2',
        '00000000-0000-0000-0000-000000000002',
        DATE '2024-06-01', 180, 60, 200, 0.74,
        10.0, 9.86, 41.48, 0)
ON CONFLICT (id) DO NOTHING;

INSERT INTO giro_resultados (id, giro_id, fazenda_id, data_finalizacao,
                             dias_giro_real, n_animais_final, peso_final_kg,
                             gmd_real, margem_cab_real, rentabilidade_am_real)
VALUES ('00000000-0000-0000-0000-0000000000d2',
        '00000000-0000-0000-0000-0000000000c2',
        '00000000-0000-0000-0000-000000000002',
        DATE '2024-12-01', 180, 60, 330,
        0.72, 720, 4.1)
ON CONFLICT (giro_id) DO NOTHING;
