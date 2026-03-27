-- Migration: Adicionar colunas valor em cotacao_motos + categorias de moto
-- Data: 2026-03-27
-- Uso: Executar no Render Shell (SQL idempotente)

-- 1. Colunas faltantes em carvia_cotacao_motos (fix erro 500)
ALTER TABLE carvia_cotacao_motos
    ADD COLUMN IF NOT EXISTS valor_unitario NUMERIC(15,2),
    ADD COLUMN IF NOT EXISTS valor_total NUMERIC(15,2);

-- 2. Categorias de moto (veiculos eletricos)
--    Leve: ate 140 kg | Medio: 140-190 kg | Pesado: acima 190 kg
INSERT INTO carvia_categorias_moto (nome, descricao, ordem, ativo, criado_em, criado_por)
VALUES
    ('Leve',     'Ate 140 kg (MCQ3, POP, Joy Super, X12, MC20, X11 Mini, Bob)', 1, true, NOW(), 'rafael'),
    ('Medio',    '140 a 190 kg (Ret, Soma, Joy Tri, Mia, Dot, Giga, Sofia, Jet, X15, S8)', 2, true, NOW(), 'rafael'),
    ('Pesado',   'Acima de 190 kg (Big Tri, Jetmax, Roma, Rome, Ved, Mia Tri)', 3, true, NOW(), 'rafael'),
    ('Bike',     'Bicicletas eletricas (Bike)', 4, true, NOW(), 'rafael'),
    ('Patinete', 'Patinetes eletricos (Patinete, G5)', 5, true, NOW(), 'rafael')
ON CONFLICT (nome) DO NOTHING;

-- 3. Vincular modelos as categorias (por peso medio)
-- Patinete (ate ~50 kg)
UPDATE carvia_modelos_moto SET categoria_moto_id = (SELECT id FROM carvia_categorias_moto WHERE nome = 'Patinete')
WHERE nome IN ('PATINETE', 'G5') AND categoria_moto_id IS NULL;

-- Bike
UPDATE carvia_modelos_moto SET categoria_moto_id = (SELECT id FROM carvia_categorias_moto WHERE nome = 'Bike')
WHERE nome IN ('BIKE') AND categoria_moto_id IS NULL;

-- Leve (ate 140 kg)
UPDATE carvia_modelos_moto SET categoria_moto_id = (SELECT id FROM carvia_categorias_moto WHERE nome = 'Leve')
WHERE nome IN ('MCQ3', 'POP', 'JOY SUPER', 'X12', 'MC20', 'X11 MINI', 'BOB') AND categoria_moto_id IS NULL;

-- Medio (140 a 190 kg)
UPDATE carvia_modelos_moto SET categoria_moto_id = (SELECT id FROM carvia_categorias_moto WHERE nome = 'Medio')
WHERE nome IN ('RET', 'SOMA', 'JOY TRI', 'MIA', 'DOT', 'GIGA', 'SOFIA', 'JET', 'X15', 'S8') AND categoria_moto_id IS NULL;

-- Pesado (acima de 190 kg)
UPDATE carvia_modelos_moto SET categoria_moto_id = (SELECT id FROM carvia_categorias_moto WHERE nome = 'Pesado')
WHERE nome IN ('BIG TRI', 'JETMAX', 'ROMA', 'ROME', 'VED', 'MIA TRI') AND categoria_moto_id IS NULL;
