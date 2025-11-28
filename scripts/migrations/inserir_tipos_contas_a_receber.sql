-- =============================================================================
-- MIGRAÇÃO: Inserir Tipos de Contas a Receber
-- =============================================================================
-- Data: 2025-11-27
-- Autor: Sistema de Fretes
--
-- Tipos:
-- - confirmacao: CONFIRMADO, ABERTO
-- - forma_confirmacao: PORTAL, EMAIL, TELEFONE, LOGISTICA
-- - acao_necessaria: LIGAR, MANDAR EMAIL, VERIFICAR PORTAL
-- - tipo (abatimento): VERBA, ACAO COMERCIAL, DEVOLUCAO
-- =============================================================================


-- =============================================================================
-- CONFIRMAÇÃO (contas_a_receber.confirmacao)
-- =============================================================================

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'CONFIRMADO', TRUE, 'contas_a_receber', 'confirmacao', 'Título com confirmação de entrega validada', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'CONFIRMADO' AND tabela = 'contas_a_receber' AND campo = 'confirmacao'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'ABERTO', TRUE, 'contas_a_receber', 'confirmacao', 'Título ainda não confirmado', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'ABERTO' AND tabela = 'contas_a_receber' AND campo = 'confirmacao'
);


-- =============================================================================
-- FORMA DE CONFIRMAÇÃO (contas_a_receber.forma_confirmacao)
-- =============================================================================

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'PORTAL', TRUE, 'contas_a_receber', 'forma_confirmacao', 'Confirmação via portal do cliente', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'PORTAL' AND tabela = 'contas_a_receber' AND campo = 'forma_confirmacao'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'EMAIL', TRUE, 'contas_a_receber', 'forma_confirmacao', 'Confirmação via e-mail', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'EMAIL' AND tabela = 'contas_a_receber' AND campo = 'forma_confirmacao'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'TELEFONE', TRUE, 'contas_a_receber', 'forma_confirmacao', 'Confirmação via telefone', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'TELEFONE' AND tabela = 'contas_a_receber' AND campo = 'forma_confirmacao'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'LOGISTICA', TRUE, 'contas_a_receber', 'forma_confirmacao', 'Confirmação via logística/transportadora', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'LOGISTICA' AND tabela = 'contas_a_receber' AND campo = 'forma_confirmacao'
);


-- =============================================================================
-- AÇÃO NECESSÁRIA (contas_a_receber.acao_necessaria)
-- =============================================================================

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'LIGAR', TRUE, 'contas_a_receber', 'acao_necessaria', 'Necessário ligar para o cliente', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'LIGAR' AND tabela = 'contas_a_receber' AND campo = 'acao_necessaria'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'MANDAR EMAIL', TRUE, 'contas_a_receber', 'acao_necessaria', 'Necessário enviar e-mail para o cliente', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'MANDAR EMAIL' AND tabela = 'contas_a_receber' AND campo = 'acao_necessaria'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'VERIFICAR PORTAL', TRUE, 'contas_a_receber', 'acao_necessaria', 'Necessário verificar portal do cliente', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'VERIFICAR PORTAL' AND tabela = 'contas_a_receber' AND campo = 'acao_necessaria'
);


-- =============================================================================
-- TIPO DE ABATIMENTO (contas_a_receber_abatimento.tipo)
-- =============================================================================

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'VERBA', TRUE, 'contas_a_receber_abatimento', 'tipo', 'Abatimento por verba comercial', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'VERBA' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'ACAO COMERCIAL', TRUE, 'contas_a_receber_abatimento', 'tipo', 'Abatimento por ação comercial', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'ACAO COMERCIAL' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);

INSERT INTO contas_a_receber_tipos (tipo, considera_a_receber, tabela, campo, explicacao, ativo, criado_por, criado_em)
SELECT 'DEVOLUCAO', TRUE, 'contas_a_receber_abatimento', 'tipo', 'Abatimento por devolução de mercadoria', TRUE, 'Sistema', CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM contas_a_receber_tipos WHERE tipo = 'DEVOLUCAO' AND tabela = 'contas_a_receber_abatimento' AND campo = 'tipo'
);


-- =============================================================================
-- VERIFICAÇÃO
-- =============================================================================

SELECT tabela, campo, COUNT(*) as qtd
FROM contas_a_receber_tipos
GROUP BY tabela, campo
ORDER BY tabela, campo;


-- =============================================================================
-- FIM DA MIGRAÇÃO
-- =============================================================================
