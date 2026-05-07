-- HORA 35: limpa motos vinculadas a modelos absorvidos (aliases).
-- Idempotente: rodar 2x e a 2a corrida nao altera nada.

-- Diagnostico ANTES (informativo):
SELECT
    mt.numero_chassi,
    mt.modelo_id,
    m.nome_modelo AS modelo_alias_nome,
    m.merged_em_id AS canonico_id,
    c.nome_modelo AS canonico_nome
FROM hora_moto mt
JOIN hora_modelo m ON m.id = mt.modelo_id
JOIN hora_modelo c ON c.id = m.merged_em_id
WHERE m.merged_em_id IS NOT NULL
ORDER BY mt.numero_chassi;

-- UPDATE: cada moto vinculada a alias passa a apontar para o canonico.
UPDATE hora_moto AS mt
SET modelo_id = m.merged_em_id
FROM hora_modelo AS m
WHERE mt.modelo_id = m.id
  AND m.merged_em_id IS NOT NULL;

-- Diagnostico DEPOIS — deve retornar 0 linhas.
SELECT COUNT(*) AS motos_ainda_em_alias
FROM hora_moto mt
JOIN hora_modelo m ON m.id = mt.modelo_id
WHERE m.merged_em_id IS NOT NULL;
