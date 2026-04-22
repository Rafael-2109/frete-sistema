-- Migration: Grupo 'Movimentacoes Empresa' + 2 categorias compensaveis.
-- Idempotente.

BEGIN;

INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, compensavel_tipo, criado_em)
VALUES ('Empresa - Entrada', 'Movimentacoes Empresa', 'fa-arrow-down', TRUE, 'E', NOW())
ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING;

INSERT INTO pessoal_categorias (nome, grupo, icone, ativa, compensavel_tipo, criado_em)
VALUES ('Empresa - Saida', 'Movimentacoes Empresa', 'fa-arrow-up', TRUE, 'S', NOW())
ON CONFLICT ON CONSTRAINT uq_pessoal_categorias_grupo_nome DO NOTHING;

COMMIT;

SELECT id, nome, grupo, compensavel_tipo, ativa
FROM pessoal_categorias
WHERE grupo = 'Movimentacoes Empresa'
ORDER BY nome;
