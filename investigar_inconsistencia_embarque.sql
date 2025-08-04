-- Script para investigar inconsistências entre tabela e transportadora em embarques
-- Execute estas queries no banco de dados para identificar o problema

-- 1. Buscar embarques onde a tabela não pertence à transportadora
SELECT 
    e.id as embarque_id,
    e.numero as embarque_numero,
    e.transportadora_id,
    t.razao_social as transportadora_embarque,
    e.tabela_nome_tabela,
    e.tipo_carga,
    e.criado_em,
    e.criado_por,
    e.cotacao_id,
    tf.transportadora_id as transportadora_tabela_id,
    t2.razao_social as transportadora_tabela
FROM embarques e
JOIN transportadoras t ON e.transportadora_id = t.id
LEFT JOIN tabelas_frete tf ON e.tabela_nome_tabela = tf.nome_tabela 
    AND e.tipo_carga = tf.tipo_carga
LEFT JOIN transportadoras t2 ON tf.transportadora_id = t2.id
WHERE e.status = 'ativo'
    AND e.tabela_nome_tabela IS NOT NULL
    AND (tf.transportadora_id != e.transportadora_id OR tf.transportadora_id IS NULL)
ORDER BY e.criado_em DESC;

-- 2. Ver histórico de alterações se houver tabela de auditoria
-- (ajuste conforme sua estrutura de auditoria)
SELECT * FROM audit_log 
WHERE table_name = 'embarques' 
    AND record_id = [ID_DO_EMBARQUE_PROBLEMÁTICO]
ORDER BY created_at DESC;

-- 3. Verificar a cotação associada
SELECT 
    c.id as cotacao_id,
    c.transportadora_id as cotacao_transportadora_id,
    c.nome_tabela as cotacao_nome_tabela,
    c.data_criacao,
    c.data_fechamento,
    t.razao_social as transportadora_cotacao
FROM cotacoes c
JOIN transportadoras t ON c.transportadora_id = t.id
WHERE c.id IN (
    SELECT cotacao_id FROM embarques 
    WHERE tabela_nome_tabela IS NOT NULL 
    AND id = [ID_DO_EMBARQUE_PROBLEMÁTICO]
);

-- 4. Contar quantos embarques têm esse problema
SELECT 
    COUNT(*) as total_inconsistentes,
    COUNT(DISTINCT e.transportadora_id) as transportadoras_afetadas,
    COUNT(DISTINCT e.tabela_nome_tabela) as tabelas_afetadas
FROM embarques e
LEFT JOIN tabelas_frete tf ON e.tabela_nome_tabela = tf.nome_tabela 
    AND e.tipo_carga = tf.tipo_carga
    AND tf.transportadora_id = e.transportadora_id
WHERE e.status = 'ativo'
    AND e.tabela_nome_tabela IS NOT NULL
    AND tf.id IS NULL;

-- 5. Listar todas as tabelas disponíveis para a transportadora do embarque
SELECT 
    tf.nome_tabela,
    tf.modalidade,
    tf.tipo_carga,
    tf.uf_origem,
    tf.uf_destino,
    tf.valor_kg,
    tf.percentual_valor
FROM tabelas_frete tf
WHERE tf.transportadora_id = [TRANSPORTADORA_ID_DO_EMBARQUE]
    AND tf.tipo_carga = [TIPO_CARGA_DO_EMBARQUE]
ORDER BY tf.nome_tabela;

-- 6. Verificar se houve mudança de transportadora_id mantendo a tabela antiga
SELECT 
    e.id,
    e.numero,
    e.criado_em,
    e.transportadora_id,
    e.tabela_nome_tabela,
    c.transportadora_id as cotacao_transportadora_id,
    c.nome_tabela as cotacao_nome_tabela
FROM embarques e
LEFT JOIN cotacoes c ON e.cotacao_id = c.id
WHERE e.transportadora_id != c.transportadora_id
    AND e.status = 'ativo'
    AND e.cotacao_id IS NOT NULL;