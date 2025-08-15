-- Script SQL para alterar campo numero_cte
-- Execute no Render: psql $DATABASE_URL < alterar_cte.sql

ALTER TABLE fretes ALTER COLUMN numero_cte TYPE VARCHAR(255);

-- Verificar alteração
\d fretes