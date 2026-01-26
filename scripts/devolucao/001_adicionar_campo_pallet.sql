-- Script SQL para adicionar campo e_pallet_devolucao na tabela nf_devolucao.
--
-- Este campo indica se uma NFD é de devolução de pallet/vasilhame (CFOP 1920/2920/5920/6920)
-- e deve ser tratada no módulo de pallet, não no módulo de devoluções de produto.
--
-- Autor: Sistema de Fretes
-- Data: 25/01/2026
--
-- Uso no Render Shell:
--   psql $DATABASE_URL < scripts/devolucao/001_adicionar_campo_pallet.sql

-- Verificar se coluna já existe antes de adicionar
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'nf_devolucao'
        AND column_name = 'e_pallet_devolucao'
    ) THEN
        -- Adicionar coluna
        ALTER TABLE nf_devolucao
        ADD COLUMN e_pallet_devolucao BOOLEAN NOT NULL DEFAULT FALSE;

        RAISE NOTICE '✅ Coluna e_pallet_devolucao adicionada com sucesso!';
    ELSE
        RAISE NOTICE '✅ Coluna e_pallet_devolucao já existe na tabela nf_devolucao';
    END IF;
END $$;

-- Criar índice (IF NOT EXISTS para segurança)
CREATE INDEX IF NOT EXISTS idx_nf_devolucao_pallet
ON nf_devolucao (e_pallet_devolucao);

-- Mostrar estatísticas
SELECT
    'Total de NFDs' AS info,
    COUNT(*)::text AS valor
FROM nf_devolucao
UNION ALL
SELECT
    'NFDs de pallet (inicial)' AS info,
    COUNT(*)::text AS valor
FROM nf_devolucao
WHERE e_pallet_devolucao = TRUE;
