-- ========================================
-- Script para alterar o tamanho do campo filial
-- Tabela: portal_sendas_filial_depara
-- Campo: filial - alterando de VARCHAR(20) para VARCHAR(100)
-- Data: 06/09/2025
-- ========================================

-- Alterar o tamanho do campo filial diretamente (tabela vazia)
ALTER TABLE portal_sendas_filial_depara 
ALTER COLUMN filial TYPE VARCHAR(100);

-- Verificar se a alteração foi aplicada
SELECT 
    column_name,
    data_type,
    character_maximum_length
FROM 
    information_schema.columns
WHERE 
    table_name = 'portal_sendas_filial_depara'
    AND column_name = 'filial';

-- Mensagem de conclusão
SELECT 'Campo filial alterado com sucesso para VARCHAR(100)' as status;