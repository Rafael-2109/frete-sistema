-- Migration: Remover extensao unaccent para viabilizar upgrade PG 16 -> 18
-- Data: 2026-02-18
-- Descricao: Substitui f_unaccent() (wrapper da extensao unaccent) por funcao pura
--            baseada em translate(), eliminando dependencia da extensao.
--            O modulo comercial/diretoria continua chamando f_unaccent() normalmente.
-- ============================================================================

-- 1. Dropar TODOS os indices que dependem de f_unaccent
DROP INDEX IF EXISTS idx_carteira_raz_social_red_unaccent;
DROP INDEX IF EXISTS idx_carteira_raz_social_unaccent;
DROP INDEX IF EXISTS idx_carteira_pedido_cliente_unaccent;
DROP INDEX IF EXISTS idx_carteira_num_pedido_unaccent;

-- 2. Dropar funcao wrapper antiga (depende da extensao)
DROP FUNCTION IF EXISTS f_unaccent(text);

-- 3. Criar funcao substituta PURA (sem extensao)
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text AS $$
  SELECT translate(
    $1,
    'áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇñÑ',
    'aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUCnN'
  );
$$ LANGUAGE sql IMMUTABLE STRICT;

-- 4. Dropar extensao unaccent
DROP EXTENSION IF EXISTS unaccent;

-- Verificacao pos-execucao:
-- SELECT f_unaccent('São Paulo');        -- Esperado: 'Sao Paulo'
-- SELECT f_unaccent('INDÚSTRIA');        -- Esperado: 'INDUSTRIA'
-- SELECT f_unaccent('café');             -- Esperado: 'cafe'
-- SELECT * FROM pg_extension WHERE extname = 'unaccent';  -- Esperado: 0 rows
