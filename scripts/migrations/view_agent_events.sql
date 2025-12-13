-- Script para visualizar dados da tabela agent_events
-- Executar no Shell do Render

-- Total de registros
SELECT COUNT(*) as total_registros FROM agent_events;

-- Agrupado por tipo de evento
SELECT event_type, COUNT(*) as qtd
FROM agent_events
GROUP BY event_type
ORDER BY qtd DESC;

-- Agrupado por usuario
SELECT user_id, COUNT(*) as qtd
FROM agent_events
GROUP BY user_id
ORDER BY qtd DESC;

-- Ultimos 20 eventos
SELECT
    id,
    user_id,
    event_type,
    session_id,
    created_at,
    LEFT(data::text, 200) as data_preview
FROM agent_events
ORDER BY created_at DESC
LIMIT 20;
