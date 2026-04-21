-- Migracao: PessoalExclusaoEmpresa -> PessoalRegraCategorizacao (grupo Desconsiderar)
--
-- Converte cada padrao de exclusao ativa em uma regra PADRAO apontando para a
-- categoria 'Desconsiderar / Empresa (Migrado)' e desativa os registros originais.
--
-- IMPORTANTE: o script Python (migrar_exclusoes_para_desconsiderar.py) e a FONTE
-- CANONICA — aplica normalizacao com unidecode + upper + strip + collapse spaces.
-- Este SQL aplica apenas UPPER+TRIM (nao remove acentos). Use este SQL somente se
-- nao houver acesso a shell Python no ambiente alvo.
--
-- Idempotente: pode rodar varias vezes sem efeito colateral.

BEGIN;

-- 1. Garantir categoria receptora
INSERT INTO pessoal_categorias (grupo, nome, icone, ativa, criado_em)
SELECT 'Desconsiderar', 'Empresa (Migrado)', 'fa-ban', TRUE, NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM pessoal_categorias
    WHERE grupo = 'Desconsiderar' AND nome = 'Empresa (Migrado)'
);

-- 2. Criar regras PADRAO a partir de exclusoes ativas (skip duplicatas)
INSERT INTO pessoal_regras_categorizacao (
    padrao_historico, tipo_regra, categoria_id, origem, ativo,
    vezes_usado, confianca, criado_em, atualizado_em
)
SELECT
    UPPER(TRIM(e.padrao)),
    'PADRAO',
    c.id,
    'manual',
    TRUE,
    0,
    100,
    NOW(),
    NOW()
FROM pessoal_exclusoes_empresa e
CROSS JOIN (
    SELECT id FROM pessoal_categorias
    WHERE grupo = 'Desconsiderar' AND nome = 'Empresa (Migrado)'
    LIMIT 1
) c
WHERE e.ativo = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM pessoal_regras_categorizacao r
      WHERE r.padrao_historico = UPPER(TRIM(e.padrao))
        AND r.categoria_id = c.id
        AND r.tipo_regra = 'PADRAO'
  );

-- 3. Desativar exclusoes originais
UPDATE pessoal_exclusoes_empresa SET ativo = FALSE WHERE ativo = TRUE;

COMMIT;

-- =============================================================================
-- Verificacao pos-execucao (rodar APOS o COMMIT):
-- =============================================================================
-- SELECT COUNT(*) AS exclusoes_ativas_pos FROM pessoal_exclusoes_empresa WHERE ativo = TRUE;
-- -- Esperado: 0
--
-- SELECT COUNT(*) AS regras_migradas
-- FROM pessoal_regras_categorizacao r
-- JOIN pessoal_categorias c ON c.id = r.categoria_id
-- WHERE c.grupo = 'Desconsiderar'
--   AND c.nome = 'Empresa (Migrado)'
--   AND r.tipo_regra = 'PADRAO'
--   AND r.ativo = TRUE;
-- -- Esperado: >= qtd de exclusoes ativas antes da migracao
