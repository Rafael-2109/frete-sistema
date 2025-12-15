-- ============================================================================
-- MIGRAÇÃO: Separar FKs de títulos no ExtratoItem
-- ============================================================================
-- PROBLEMA:
-- O modelo ExtratoItem tinha apenas um campo titulo_id com FK para contas_a_receber,
-- mas era usado tanto para recebimentos (clientes) quanto pagamentos (fornecedores).
-- Isso causava o bug de mostrar nome de cliente quando deveria mostrar fornecedor.
--
-- SOLUÇÃO:
-- - titulo_receber_id -> FK para contas_a_receber (clientes)
-- - titulo_pagar_id -> FK para contas_a_pagar (fornecedores)
-- - titulo_cnpj -> Campo cache para CNPJ
-- - titulo_id -> Mantido sem FK (deprecado) para compatibilidade
--
-- Data: 2025-12-15
-- ============================================================================

-- 1. Adicionar campo titulo_receber_id (FK para clientes)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_receber_id INTEGER REFERENCES contas_a_receber(id);

-- 2. Adicionar campo titulo_pagar_id (FK para fornecedores)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_pagar_id INTEGER REFERENCES contas_a_pagar(id);

-- 3. Adicionar campo titulo_cnpj (cache)
ALTER TABLE extrato_item
ADD COLUMN IF NOT EXISTS titulo_cnpj VARCHAR(20);

-- 4. Migrar dados de titulo_id para titulo_receber_id (apenas lotes de recebimento)
UPDATE extrato_item ei
SET titulo_receber_id = titulo_id
FROM extrato_lote el
WHERE ei.lote_id = el.id
AND ei.titulo_id IS NOT NULL
AND ei.titulo_receber_id IS NULL
AND (el.tipo_transacao = 'entrada' OR el.tipo_transacao IS NULL);

-- 5. Criar índices para os novos campos
CREATE INDEX IF NOT EXISTS ix_extrato_item_titulo_receber_id ON extrato_item(titulo_receber_id);
CREATE INDEX IF NOT EXISTS ix_extrato_item_titulo_pagar_id ON extrato_item(titulo_pagar_id);

-- 6. Verificar itens de pagamento que precisam reprocessamento
-- (Não migrar automaticamente porque titulo_id apontava para ContasAReceber errado)
SELECT COUNT(*) as pagamentos_para_reprocessar
FROM extrato_item ei
JOIN extrato_lote el ON ei.lote_id = el.id
WHERE el.tipo_transacao = 'saida'
AND ei.titulo_id IS NOT NULL;

-- ============================================================================
-- NOTAS IMPORTANTES:
-- ============================================================================
-- 1. O campo titulo_id foi mantido SEM FK (estava apontando para contas_a_receber)
--    Isso permite que dados antigos continuem funcionando
--
-- 2. Para lotes de PAGAMENTO (tipo_transacao = 'saida'), os titulo_id antigos
--    NÃO foram migrados porque apontavam para ContasAReceber (errado!)
--    Esses itens precisarão ser reprocessados manualmente ou via matching
--
-- 3. O código agora usa:
--    - titulo_receber_id para lotes de recebimento (clientes)
--    - titulo_pagar_id para lotes de pagamento (fornecedores)
-- ============================================================================
