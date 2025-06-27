-- 🔍 QUERIES PARA VALIDAR RESPOSTAS DO CLAUDE AI
-- Use estas queries para comparar com as respostas do sistema

-- 1. CONSULTAS BÁSICAS
-- 1.2) Total de clientes
SELECT COUNT(DISTINCT nome_cliente) as total_clientes
FROM relatorio_faturamento_importado
WHERE nome_cliente IS NOT NULL;

-- 1.3) Transportadoras ativas
SELECT id, razao_social, cidade, uf, freteiro
FROM transportadoras
ORDER BY razao_social;

-- 2. FATURAMENTO
-- 2.1) Faturamento de hoje
SELECT COALESCE(SUM(valor_total), 0) as faturamento_hoje
FROM relatorio_faturamento_importado
WHERE DATE(data_fatura) = CURRENT_DATE;

-- 2.2) Faturamento de ontem
SELECT COALESCE(SUM(valor_total), 0) as faturamento_ontem
FROM relatorio_faturamento_importado
WHERE DATE(data_fatura) = CURRENT_DATE - INTERVAL '1 day';

-- 2.3) Faturamento últimos 7 dias
SELECT COALESCE(SUM(valor_total), 0) as faturamento_semana
FROM relatorio_faturamento_importado
WHERE data_fatura >= CURRENT_DATE - INTERVAL '7 days';

-- 2.4) Faturamento de junho/2024
SELECT COALESCE(SUM(valor_total), 0) as faturamento_junho_2025
FROM relatorio_faturamento_importado
WHERE EXTRACT(YEAR FROM data_fatura) = 2025
  AND EXTRACT(MONTH FROM data_fatura) = 6;

-- 3. CONSULTAS POR CLIENTE
-- 3.1) Entregas do Assai
SELECT COUNT(*) as total_entregas_assai
FROM entregas_monitoradas em
JOIN relatorio_faturamento_importado rfi ON em.numero_nf = rfi.numero_nf
WHERE UPPER(rfi.nome_cliente) LIKE '%ASSAI%';

-- 3.2) Faturamento Atacadão mês atual
SELECT COALESCE(SUM(valor_total), 0) as faturamento_atacadao_mes
FROM relatorio_faturamento_importado
WHERE UPPER(nome_cliente) LIKE '%ATACAD%'
  AND EXTRACT(YEAR FROM data_fatura) = EXTRACT(YEAR FROM CURRENT_DATE)
  AND EXTRACT(MONTH FROM data_fatura) = EXTRACT(MONTH FROM CURRENT_DATE);

-- 3.3) Entregas pendentes Carrefour
SELECT COUNT(*) as entregas_pendentes_carrefour
FROM entregas_monitoradas em
JOIN relatorio_faturamento_importado rfi ON em.numero_nf = rfi.numero_nf
WHERE UPPER(rfi.nome_cliente) LIKE '%CARREFOUR%'
  AND em.entregue = false;

-- 4. FILTROS GEOGRÁFICOS
-- 4.1) Entregas pendentes em SP
SELECT COUNT(*) as entregas_pendentes_sp
FROM entregas_monitoradas
WHERE uf_destino = 'SP'
  AND entregue = false;

-- 4.2) Faturamento RJ última semana
SELECT COALESCE(SUM(rfi.valor_total), 0) as faturamento_rj_semana
FROM relatorio_faturamento_importado rfi
JOIN entregas_monitoradas em ON rfi.numero_nf = em.numero_nf
WHERE em.uf_destino = 'RJ'
  AND rfi.data_fatura >= CURRENT_DATE - INTERVAL '7 days';

-- 5. STATUS E PROBLEMAS
-- 5.1) Entregas atrasadas
SELECT COUNT(*) as entregas_atrasadas
FROM entregas_monitoradas
WHERE entregue = false
  AND data_prevista_entrega < CURRENT_DATE;

-- 5.2) Pedidos pendentes cotação
SELECT COUNT(*) as pedidos_sem_cotacao
FROM pedidos
WHERE frete_cotado IS NULL OR frete_cotado = 0;

-- 5.3) Embarques ativos
SELECT COUNT(*) as embarques_ativos
FROM embarques
WHERE status = 'ativo';

-- 6. CONSULTAS COMPLEXAS
-- 6.1) Faturamento Assai SP últimos 30 dias
SELECT COALESCE(SUM(rfi.valor_total), 0) as faturamento_assai_sp_30d
FROM relatorio_faturamento_importado rfi
JOIN entregas_monitoradas em ON rfi.numero_nf = em.numero_nf
WHERE UPPER(rfi.nome_cliente) LIKE '%ASSAI%'
  AND em.uf_destino = 'SP'
  AND rfi.data_fatura >= CURRENT_DATE - INTERVAL '30 days';

-- 6.4) Transportadoras freteiros
SELECT COUNT(*) as total_freteiros
FROM transportadoras
WHERE freteiro = true;

-- 8. AGREGAÇÕES
-- 8.1) Ticket médio hoje
SELECT 
    CASE 
        WHEN COUNT(*) > 0 THEN ROUND(AVG(valor_total)::numeric, 2)
        ELSE 0
    END as ticket_medio_hoje
FROM relatorio_faturamento_importado
WHERE DATE(data_fatura) = CURRENT_DATE;

-- 8.4) Prazo médio de entrega
SELECT 
    ROUND(AVG(
        EXTRACT(EPOCH FROM (data_entrega_realizada - data_embarque)) / 86400
    )::numeric, 1) as prazo_medio_dias
FROM entregas_monitoradas
WHERE entregue = true
  AND data_embarque IS NOT NULL
  AND data_entrega_realizada IS NOT NULL;

-- 9. OPERACIONAL
-- 9.1) Embarques na portaria
SELECT COUNT(*) as embarques_portaria
FROM embarques
WHERE data_embarque IS NULL
  AND status = 'ativo';

-- 9.2) Veículos no pátio
SELECT COUNT(*) as veiculos_patio
FROM controle_portaria
WHERE status = 'DENTRO';

-- VALIDAÇÃO DE CLIENTES INEXISTENTES
-- Verificar se Magazine Luiza ou Renner existem
SELECT nome_cliente
FROM relatorio_faturamento_importado
WHERE UPPER(nome_cliente) LIKE '%MAGAZINE%LUIZA%'
   OR UPPER(nome_cliente) LIKE '%RENNER%'
GROUP BY nome_cliente; 