-- Adiciona campos extras em nf_pendente_tagplus (executar no Render)
ALTER TABLE nf_pendente_tagplus ADD COLUMN IF NOT EXISTS nome_cidade VARCHAR(120);
ALTER TABLE nf_pendente_tagplus ADD COLUMN IF NOT EXISTS cod_uf VARCHAR(5);
ALTER TABLE nf_pendente_tagplus ADD COLUMN IF NOT EXISTS pedido_preenchido_em TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE nf_pendente_tagplus ADD COLUMN IF NOT EXISTS pedido_preenchido_por VARCHAR(100);
