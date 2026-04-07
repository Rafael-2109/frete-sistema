-- Migration: Materialized view mv_pedidos
-- Objetivo: Eliminar custo de ~500ms/scan da VIEW pedidos (UNION ALL com subqueries correlacionadas)
-- A VIEW regular `pedidos` permanece intacta (rollback seguro)
-- Refresh via scheduler (CONCURRENTLY, ~30 min)
-- Data: 2026-04-07

-- ============================================================
-- 1. Criar Materialized View (corpo identico a VIEW pedidos)
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_pedidos;

CREATE MATERIALIZED VIEW mv_pedidos AS

-- Parte 1: Pedidos normais Nacom (Separacao)
SELECT
    abs((('x'::text || substr(md5(s.separacao_lote_id::text), 1, 8)))::bit(32)::integer) AS id,
    s.separacao_lote_id,
    min(s.num_pedido::text) AS num_pedido,
    min(s.data_pedido) AS data_pedido,
    min(s.cnpj_cpf::text) AS cnpj_cpf,
    min(s.raz_social_red::text) AS raz_social_red,
    min(s.nome_cidade::text) AS nome_cidade,
    min(s.cod_uf::text) AS cod_uf,
    min(s.cidade_normalizada::text) AS cidade_normalizada,
    min(s.uf_normalizada::text) AS uf_normalizada,
    min(s.codigo_ibge::text) AS codigo_ibge,
    COALESCE(sum(s.valor_saldo), 0::double precision) AS valor_saldo_total,
    COALESCE(sum(s.pallet), 0::double precision) AS pallet_total,
    COALESCE(sum(s.peso), 0::double precision) AS peso_total,
    min(s.rota::text) AS rota,
    min(s.sub_rota::text) AS sub_rota,
    min(s.observ_ped_1::text) AS observ_ped_1,
    min(s.roteirizacao::text) AS roteirizacao,
    min(s.expedicao) AS expedicao,
    min(s.agendamento) AS agendamento,
    min(s.protocolo::text) AS protocolo,
    bool_or(s.agendamento_confirmado) AS agendamento_confirmado,
    NULL::character varying(100) AS transportadora,
    NULL::double precision AS valor_frete,
    NULL::double precision AS valor_por_kg,
    NULL::character varying(100) AS nome_tabela,
    NULL::character varying(50) AS modalidade,
    NULL::character varying(100) AS melhor_opcao,
    NULL::double precision AS valor_melhor_opcao,
    NULL::integer AS lead_time,
    min(s.data_embarque) AS data_embarque,
    min(s.numero_nf::text) AS nf,
    min(s.status::text) AS status,
    bool_or(s.nf_cd) AS nf_cd,
    min(s.pedido_cliente::text) AS pedido_cliente,
    bool_or(s.separacao_impressa) AS separacao_impressa,
    min(s.separacao_impressa_em) AS separacao_impressa_em,
    min(s.separacao_impressa_por::text) AS separacao_impressa_por,
    min(s.cotacao_id) AS cotacao_id,
    NULL::integer AS usuario_id,
    min(s.criado_em) AS criado_em,
    min(cp.equipe_vendas::text) AS equipe_vendas,
    min(s.tags_pedido::text) AS tags_pedido
FROM separacao s
LEFT JOIN carteira_principal cp
    ON s.num_pedido = cp.num_pedido
    AND s.cod_produto = cp.cod_produto
WHERE s.separacao_lote_id IS NOT NULL
    AND s.status::text <> 'PREVISAO'::text
GROUP BY s.separacao_lote_id

UNION ALL

-- Parte 2A: Cotacoes CarVia APROVADAS (saldo/provisorio)
SELECT
    -(cot.id * 1000) AS id,
    ('CARVIA-' || cot.id::text) AS separacao_lote_id,
    cot.numero_cotacao AS num_pedido,
    cot.data_cotacao::date AS data_pedido,
    dest.cnpj AS cnpj_cpf,
    dest.razao_social AS raz_social_red,
    dest.fisico_cidade AS nome_cidade,
    dest.fisico_uf AS cod_uf,
    dest.fisico_cidade AS cidade_normalizada,
    dest.fisico_uf AS uf_normalizada,
    NULL::text AS codigo_ibge,
    GREATEST(
        COALESCE(cot.valor_mercadoria::double precision, 0) - COALESCE((
            SELECT SUM(pi.valor_total)
            FROM carvia_pedidos p
            JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
            WHERE p.cotacao_id = cot.id
              AND p.status != 'CANCELADO'
              AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
        )::double precision, 0),
    0) AS valor_saldo_total,
    0::double precision AS pallet_total,
    GREATEST(
        COALESCE(
            CASE WHEN cot.tipo_material = 'MOTO' THEN (
                SELECT COALESCE(SUM(m.peso_cubado_total), 0)
                FROM carvia_cotacao_motos m WHERE m.cotacao_id = cot.id
            )
            ELSE COALESCE(cot.peso_cubado, cot.peso)
            END::double precision, 0
        ) * GREATEST(
            1.0 - COALESCE((
                SELECT SUM(pi.valor_total)
                FROM carvia_pedidos p
                JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
                WHERE p.cotacao_id = cot.id
                  AND p.status != 'CANCELADO'
                  AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
            )::double precision, 0) / NULLIF(cot.valor_mercadoria::double precision, 0),
        0),
    0) AS peso_total,
    cr.rota::text AS rota,
    csr.sub_rota::text AS sub_rota,
    cot.observacoes AS observ_ped_1,
    NULL::text AS roteirizacao,
    cot.data_expedicao AS expedicao,
    cot.data_agenda AS agendamento,
    NULL::text AS protocolo,
    FALSE AS agendamento_confirmado,
    NULL::character varying(100) AS transportadora,
    cot.valor_final_aprovado::double precision AS valor_frete,
    NULL::double precision AS valor_por_kg,
    NULL::character varying(100) AS nome_tabela,
    NULL::character varying(50) AS modalidade,
    NULL::character varying(100) AS melhor_opcao,
    NULL::double precision AS valor_melhor_opcao,
    NULL::integer AS lead_time,
    NULL::date AS data_embarque,
    NULL::text AS nf,
    cot.status AS status,
    FALSE AS nf_cd,
    NULL::text AS pedido_cliente,
    FALSE AS separacao_impressa,
    NULL::timestamp without time zone AS separacao_impressa_em,
    NULL::text AS separacao_impressa_por,
    NULL::integer AS cotacao_id,
    NULL::integer AS usuario_id,
    cot.criado_em AS criado_em,
    NULL::text AS equipe_vendas,
    NULL::text AS tags_pedido
FROM carvia_cotacoes cot
JOIN carvia_cliente_enderecos dest ON dest.id = cot.endereco_destino_id
LEFT JOIN cadastro_rota cr ON cr.cod_uf = dest.fisico_uf AND cr.ativa = TRUE
LEFT JOIN cadastro_sub_rota csr ON csr.cod_uf = dest.fisico_uf
    AND UPPER(dest.fisico_cidade) LIKE '%' || UPPER(csr.nome_cidade) || '%'
    AND csr.ativa = TRUE
WHERE cot.status = 'APROVADO'
  AND (
    COALESCE(cot.valor_mercadoria::double precision, 0) - COALESCE((
        SELECT SUM(pi.valor_total)
        FROM carvia_pedidos p
        JOIN carvia_pedido_itens pi ON pi.pedido_id = p.id
        WHERE p.cotacao_id = cot.id
          AND p.status != 'CANCELADO'
          AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
    )::double precision, 0)
  ) > 0.01

UNION ALL

-- Parte 2B: Pedidos CarVia individuais
SELECT
    -(ped.id * 1000 + 500000) AS id,
    ('CARVIA-PED-' || ped.id::text) AS separacao_lote_id,
    ped.numero_pedido AS num_pedido,
    cot.data_cotacao::date AS data_pedido,
    dest.cnpj AS cnpj_cpf,
    dest.razao_social AS raz_social_red,
    dest.fisico_cidade AS nome_cidade,
    dest.fisico_uf AS cod_uf,
    dest.fisico_cidade AS cidade_normalizada,
    dest.fisico_uf AS uf_normalizada,
    NULL::text AS codigo_ibge,
    COALESCE((
        SELECT SUM(pi.valor_total)
        FROM carvia_pedido_itens pi
        WHERE pi.pedido_id = ped.id
    )::double precision, 0) AS valor_saldo_total,
    0::double precision AS pallet_total,
    COALESCE(
        CASE WHEN cot.tipo_material = 'MOTO' THEN (
            SELECT COALESCE(SUM(m.peso_cubado_total), 0)
            FROM carvia_cotacao_motos m WHERE m.cotacao_id = cot.id
        )
        ELSE COALESCE(cot.peso_cubado, cot.peso)
        END::double precision, 0
    ) * COALESCE((
        SELECT SUM(pi.valor_total)
        FROM carvia_pedido_itens pi
        WHERE pi.pedido_id = ped.id
    )::double precision, 0) / NULLIF(cot.valor_mercadoria::double precision, 0) AS peso_total,
    cr.rota::text AS rota,
    csr.sub_rota::text AS sub_rota,
    cot.observacoes AS observ_ped_1,
    NULL::text AS roteirizacao,
    cot.data_expedicao AS expedicao,
    cot.data_agenda AS agendamento,
    NULL::text AS protocolo,
    FALSE AS agendamento_confirmado,
    NULL::character varying(100) AS transportadora,
    cot.valor_final_aprovado::double precision AS valor_frete,
    NULL::double precision AS valor_por_kg,
    NULL::character varying(100) AS nome_tabela,
    NULL::character varying(50) AS modalidade,
    NULL::character varying(100) AS melhor_opcao,
    NULL::double precision AS valor_melhor_opcao,
    NULL::integer AS lead_time,
    NULL::date AS data_embarque,
    (SELECT string_agg(DISTINCT pi.numero_nf, ', ')
     FROM carvia_pedido_itens pi
     WHERE pi.pedido_id = ped.id AND pi.numero_nf IS NOT NULL AND pi.numero_nf != ''
    )::text AS nf,
    ped.status AS status,
    FALSE AS nf_cd,
    NULL::text AS pedido_cliente,
    FALSE AS separacao_impressa,
    NULL::timestamp without time zone AS separacao_impressa_em,
    NULL::text AS separacao_impressa_por,
    NULL::integer AS cotacao_id,
    NULL::integer AS usuario_id,
    ped.criado_em AS criado_em,
    NULL::text AS equipe_vendas,
    NULL::text AS tags_pedido
FROM carvia_pedidos ped
JOIN carvia_cotacoes cot ON ped.cotacao_id = cot.id
JOIN carvia_cliente_enderecos dest ON dest.id = cot.endereco_destino_id
LEFT JOIN cadastro_rota cr ON cr.cod_uf = dest.fisico_uf AND cr.ativa = TRUE
LEFT JOIN cadastro_sub_rota csr ON csr.cod_uf = dest.fisico_uf
    AND UPPER(dest.fisico_cidade) LIKE '%' || UPPER(csr.nome_cidade) || '%'
    AND csr.ativa = TRUE
WHERE ped.status NOT IN ('CANCELADO')
  AND cot.status = 'APROVADO';

-- ============================================================
-- 2. Indices (obrigatorio: unique para REFRESH CONCURRENTLY)
-- ============================================================
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pedidos_lote
    ON mv_pedidos (separacao_lote_id);

-- Indices para counter queries (filtros mais frequentes)
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_expedicao
    ON mv_pedidos (expedicao);
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_status
    ON mv_pedidos (status);
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_nf_cd
    ON mv_pedidos (nf_cd) WHERE nf_cd = true;

-- Rota/sub_rota para DISTINCT e filtros
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_rota
    ON mv_pedidos (rota) WHERE rota IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_sub_rota
    ON mv_pedidos (sub_rota) WHERE sub_rota IS NOT NULL;

-- Composto para ordenacao padrao da lista
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_ordering
    ON mv_pedidos (rota, sub_rota, cnpj_cpf, expedicao);

-- CNPJ para filtros de texto
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_cnpj
    ON mv_pedidos (cnpj_cpf);

-- Filtro "sem NF + sem CD" (padrao mais usado nos contadores)
CREATE INDEX IF NOT EXISTS idx_mv_pedidos_nf_null
    ON mv_pedidos (nf, nf_cd, data_embarque)
    WHERE (nf IS NULL OR nf = '') AND nf_cd = false;
