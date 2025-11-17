-- ============================================================================
-- Script SQL para corrigir tipo do campo odoo_invoice_ids
-- ============================================================================
--
-- PROBLEMA: Campo odoo_invoice_ids definido como VARCHAR(20) causando erro:
--           "value too long for type character varying(20)"
--
-- SOLUÇÃO: Alterar campo para TEXT para comportar arrays JSON de IDs
--
-- EXECUTAR NO SHELL DO RENDER:
-- psql $DATABASE_URL < fix_odoo_invoice_ids_type.sql
--
-- ============================================================================

-- Verificar tipo atual
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name = 'odoo_invoice_ids';

-- Alterar tipo do campo
ALTER TABLE conhecimento_transporte
ALTER COLUMN odoo_invoice_ids TYPE TEXT;

-- Verificar tipo após alteração
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name = 'odoo_invoice_ids';

-- ============================================================================
-- Resultado esperado:
-- odoo_invoice_ids | text | NULL
-- ============================================================================
