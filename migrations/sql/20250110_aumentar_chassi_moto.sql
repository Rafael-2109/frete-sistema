-- ================================================================
-- Migração: Aumentar tamanho do campo numero_chassi de 17 para 30
-- Data: 2025-01-10
-- Motivo: Suportar variações de VIN com mais de 17 caracteres
-- Tabela afetada: moto
-- ================================================================

-- Verificar registros existentes antes da alteração
DO $$
BEGIN
    RAISE NOTICE 'Total de motos cadastradas: %', (SELECT COUNT(*) FROM moto);
    RAISE NOTICE 'Maior chassi atual: % caracteres', (SELECT MAX(LENGTH(numero_chassi)) FROM moto);
END $$;

-- Alterar tamanho do campo numero_chassi
ALTER TABLE moto
ALTER COLUMN numero_chassi TYPE VARCHAR(30);

-- Confirmar alteração
DO $$
BEGIN
    RAISE NOTICE 'Campo numero_chassi alterado para VARCHAR(30) com sucesso!';
END $$;

-- ================================================================
-- ROLLBACK (caso necessário):
-- ALTER TABLE moto ALTER COLUMN numero_chassi TYPE VARCHAR(17);
-- ================================================================
