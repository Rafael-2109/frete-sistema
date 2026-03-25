-- Migration: Criar tabela carvia_nf_veiculos + renomear numeracao

-- 1. Tabela de veiculos da NF
CREATE TABLE IF NOT EXISTS carvia_nf_veiculos (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES carvia_nfs(id) ON DELETE CASCADE,
    chassi VARCHAR(30) NOT NULL,
    modelo VARCHAR(100),
    cor VARCHAR(50),
    valor NUMERIC(15,2),
    ano VARCHAR(20),
    numero_motor VARCHAR(30),
    criado_em TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_carvia_nf_veiculos_nf_id ON carvia_nf_veiculos(nf_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_carvia_nf_veiculo_chassi ON carvia_nf_veiculos(chassi);

-- 2. Renomear cotacoes para COT-{id}
UPDATE carvia_cotacoes SET numero_cotacao = 'COT-' || id::text
WHERE numero_cotacao != 'COT-' || id::text;

-- 3. Renomear pedidos para PED-{cotacao_id}-{seq}
UPDATE carvia_pedidos SET numero_pedido = 'PED-' || cotacao_id::text || '-' ||
    (SELECT COUNT(*) FROM carvia_pedidos p2 WHERE p2.cotacao_id = carvia_pedidos.cotacao_id AND p2.id <= carvia_pedidos.id)::text
WHERE numero_pedido LIKE 'PED-CV-%';
