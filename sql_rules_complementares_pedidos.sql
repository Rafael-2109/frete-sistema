-- =====================================================
-- RULES COMPLEMENTARES PARA VIEW PEDIDOS
-- Data: 2025-09-03
-- 
-- Adiciona RULES que podem estar faltando
-- =====================================================

-- IMPORTANTE: Execute este script APÓS sql_criar_view_pedidos_final.sql

-- 1. RULE GENÉRICA para qualquer UPDATE
-- =====================================================
-- Esta RULE captura QUALQUER tentativa de UPDATE e não faz nada
-- Evita o erro "UPDATE statement on table 'pedidos' expected to update 1 row(s); 0 were matched"
-- As RULES específicas acima têm prioridade sobre esta

CREATE OR REPLACE RULE pedidos_update_generico AS
ON UPDATE TO pedidos
DO INSTEAD NOTHING;

-- Nota: As RULES específicas já criadas no script principal têm prioridade
-- Esta RULE genérica só será executada se nenhuma RULE específica corresponder

-- 2. ALTERNATIVA: RULE para campos de cliente (se necessário)
-- =====================================================
-- Descomente se precisar atualizar dados do cliente

-- CREATE OR REPLACE RULE pedidos_update_cliente AS
-- ON UPDATE TO pedidos
-- WHERE (NEW.cnpj_cpf IS DISTINCT FROM OLD.cnpj_cpf
--     OR NEW.raz_social_red IS DISTINCT FROM OLD.raz_social_red
--     OR NEW.nome_cidade IS DISTINCT FROM OLD.nome_cidade
--     OR NEW.cod_uf IS DISTINCT FROM OLD.cod_uf)
-- DO INSTEAD
-- UPDATE separacao
-- SET 
--     cnpj_cpf = NEW.cnpj_cpf,
--     raz_social_red = NEW.raz_social_red,
--     nome_cidade = NEW.nome_cidade,
--     cod_uf = NEW.cod_uf
-- WHERE separacao_lote_id = NEW.separacao_lote_id;

-- 3. VERIFICAÇÃO DE RULES INSTALADAS
-- =====================================================
-- Execute esta query para verificar todas as RULES da VIEW pedidos:

/*
SELECT 
    r.rulename,
    pg_get_ruledef(r.oid) as definition
FROM pg_rewrite r
JOIN pg_class c ON r.ev_class = c.oid
WHERE c.relname = 'pedidos'
ORDER BY r.rulename;
*/

-- 4. TESTE DE UPDATE
-- =====================================================
-- Teste se UPDATEs funcionam sem erro:

/*
-- Teste 1: Update de status (tem RULE específica)
UPDATE pedidos SET status = status WHERE id = (SELECT id FROM pedidos LIMIT 1);

-- Teste 2: Update de campo sem RULE específica (usa RULE genérica)
UPDATE pedidos SET transportadora = 'TESTE' WHERE id = (SELECT id FROM pedidos LIMIT 1);

-- Se não houver erro, as RULES estão funcionando!
*/