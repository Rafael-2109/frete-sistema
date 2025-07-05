
-- Remove referência à migração inexistente
DELETE FROM alembic_version WHERE version_num = '1d81b88a3038';

-- Verificar migrações atuais
SELECT version_num FROM alembic_version;
