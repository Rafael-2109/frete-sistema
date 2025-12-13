-- Script para dropar a tabela agent_events (não mais usada)
-- Executar no Shell do Render

-- Verifica quantos registros existem (opcional)
SELECT COUNT(*) as total_registros FROM agent_events;

-- Dropa a tabela
DROP TABLE IF EXISTS agent_events CASCADE;

-- Confirma que foi removida
SELECT 'Tabela agent_events removida com sucesso!' as status;
