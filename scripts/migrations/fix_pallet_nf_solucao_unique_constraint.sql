-- Migration: Alterar UNIQUE constraint de pallet_nf_solucoes
-- Data: 2026-03-28
-- Fix: PYTHON-FLASK-A7 (UniqueViolation em chave_nfe_solucao)
-- Problema: unique=True em chave_nfe_solucao impede 1:N (1 devolução → N remessas)
-- Solução: Trocar UNIQUE simples por UNIQUE composto (chave_nfe_solucao, nf_remessa_id)
-- Uso: Executar no Render Shell (SQL idempotente)

-- 1. Remover constraint UNIQUE simples
ALTER TABLE pallet_nf_solucoes
    DROP CONSTRAINT IF EXISTS pallet_nf_solucoes_chave_nfe_solucao_key;

-- 2. Remover índice UNIQUE simples (se existir como índice separado)
DROP INDEX IF EXISTS ix_pallet_nf_solucoes_chave_nfe_solucao;

-- 3. Criar UNIQUE composto: mesma chave_nfe pode aparecer em remessas diferentes
--    mas NÃO pode aparecer duas vezes na mesma remessa
CREATE UNIQUE INDEX IF NOT EXISTS uq_pallet_nf_solucoes_chave_remessa
    ON pallet_nf_solucoes (chave_nfe_solucao, nf_remessa_id)
    WHERE chave_nfe_solucao IS NOT NULL AND ativo = true;
