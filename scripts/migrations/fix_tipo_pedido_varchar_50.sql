-- ============================================================================
-- Script SQL para corrigir tamanho do campo tipo_pedido
-- ============================================================================
--
-- CONTEXTO:
-- CTe DFe ID: 28699
-- Chave: 35250950346989000168570010001053821030972112
-- Tipo: 'serv-industrializacao' (Serviço de Industrialização)
--
-- O QUE É SERVIÇO DE INDUSTRIALIZAÇÃO?
-- - NACOM envia matéria-prima (resina, tampas) para terceiro processar
-- - Terceiro processa e transforma em produto acabado (frascos)
-- - Terceiro devolve produto acabado para NACOM
-- - CTe documenta esse transporte com tipo='serv-industrializacao'
--
-- PROBLEMA:
-- Campo tipo_pedido definido como VARCHAR(20) causando erro:
-- "value too long for type character varying(20)"
-- Valor: 'serv-industrializacao' (22 caracteres)
--
-- SOLUÇÃO:
-- Alterar campo para VARCHAR(50) para comportar TODOS os 38 tipos do Odoo Brasil
-- (Maior valor: 22 caracteres)
--
-- EXECUTAR NO SHELL DO RENDER:
-- psql $DATABASE_URL < fix_tipo_pedido_varchar_50.sql
--
-- ============================================================================

-- Verificar tipo atual
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name = 'tipo_pedido';

-- Verificar valores atuais (maiores primeiro)
SELECT DISTINCT
    tipo_pedido,
    LENGTH(tipo_pedido) as tamanho
FROM conhecimento_transporte
WHERE tipo_pedido IS NOT NULL
ORDER BY tamanho DESC
LIMIT 15;

-- Alterar tipo do campo
ALTER TABLE conhecimento_transporte
ALTER COLUMN tipo_pedido TYPE VARCHAR(50);

-- Verificar tipo após alteração
SELECT
    column_name,
    data_type,
    character_maximum_length
FROM information_schema.columns
WHERE table_name = 'conhecimento_transporte'
AND column_name = 'tipo_pedido';

-- ============================================================================
-- Resultado esperado:
-- tipo_pedido | character varying | 50
-- ============================================================================
