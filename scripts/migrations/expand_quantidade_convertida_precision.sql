-- Migration: Expandir precisao de quantidade_convertida para 4 casas decimais
-- Motivo: divisoes como 1/6 = 0.1667 precisam de 4 casas para manter integridade
--         no roundtrip (0.167 * 6 = 1.002, mas 0.1667 * 6 = 1.0002)
-- Tabela: nf_devolucao_linha
-- Data: 2026-04-10

-- Verificar tipo atual
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'nf_devolucao_linha'
          AND column_name = 'quantidade_convertida'
          AND numeric_scale = 3
    ) THEN
        ALTER TABLE nf_devolucao_linha
        ALTER COLUMN quantidade_convertida TYPE NUMERIC(15, 4);

        RAISE NOTICE 'quantidade_convertida expandida para NUMERIC(15,4)';
    ELSE
        RAISE NOTICE 'quantidade_convertida ja possui precisao >= 4 ou nao existe';
    END IF;
END $$;
