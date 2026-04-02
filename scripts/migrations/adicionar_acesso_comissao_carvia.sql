-- Migration: Adicionar campo acesso_comissao_carvia na tabela usuarios
-- Executar no Render Shell: psql $DATABASE_URL < scripts/migrations/adicionar_acesso_comissao_carvia.sql

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'usuarios' AND column_name = 'acesso_comissao_carvia'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN acesso_comissao_carvia BOOLEAN NOT NULL DEFAULT FALSE;
        RAISE NOTICE 'Coluna acesso_comissao_carvia adicionada.';
    ELSE
        RAISE NOTICE 'Coluna acesso_comissao_carvia ja existe.';
    END IF;
END
$$;
