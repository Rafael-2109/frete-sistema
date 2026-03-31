-- Migration: Converter origens por cliente em origens globais
-- Uso: Executar no Render Shell (psql)
-- IMPORTANTE: Executar em ordem (1, 2, 3)

-- 1. Re-apontar cotacoes para origens globais existentes (quando ha duplicata)
UPDATE carvia_cotacoes c
SET endereco_origem_id = g.id
FROM carvia_cliente_enderecos old
JOIN carvia_cliente_enderecos g
  ON g.cnpj = old.cnpj
  AND g.tipo = 'ORIGEM'
  AND g.cliente_id IS NULL
WHERE c.endereco_origem_id = old.id
  AND old.tipo = 'ORIGEM'
  AND old.cliente_id IS NOT NULL;

-- 2. Deletar origens por cliente que tinham equivalente global (agora orfas)
DELETE FROM carvia_cliente_enderecos old
USING carvia_cliente_enderecos g
WHERE old.tipo = 'ORIGEM'
  AND old.cliente_id IS NOT NULL
  AND g.tipo = 'ORIGEM'
  AND g.cliente_id IS NULL
  AND g.cnpj = old.cnpj
  AND NOT EXISTS (
    SELECT 1 FROM carvia_cotacoes c WHERE c.endereco_origem_id = old.id
  );

-- 3. Converter restantes (sem duplicata global) para globais
UPDATE carvia_cliente_enderecos
SET cliente_id = NULL
WHERE tipo = 'ORIGEM'
  AND cliente_id IS NOT NULL;

-- Verificacao
SELECT
    COUNT(*) FILTER (WHERE cliente_id IS NOT NULL AND tipo = 'ORIGEM') AS origens_cliente_restantes,
    COUNT(*) FILTER (WHERE cliente_id IS NULL AND tipo = 'ORIGEM') AS origens_globais
FROM carvia_cliente_enderecos;
