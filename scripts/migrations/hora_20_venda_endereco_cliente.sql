-- Migration HORA 20: campos de endereco do cliente em hora_venda + origem_criacao.
--
-- Suporta o novo fluxo "Pedido de Vendas" (criado pelo operador no menu
-- Faturamento), que registra venda com endereco completo do destinatario para
-- emissao de NFe via TagPlus. Vendas legacy (criadas via DANFE upload) ficam
-- com esses campos em NULL — fluxo retro-compativel.
--
-- Idempotente: ADD COLUMN IF NOT EXISTS em todos os campos novos.

-- ============================================================
-- 1. hora_venda — campos de endereco do destinatario (cliente)
-- ============================================================
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS cep                   VARCHAR(9)   NULL,
    ADD COLUMN IF NOT EXISTS endereco_logradouro   VARCHAR(255) NULL,
    ADD COLUMN IF NOT EXISTS endereco_numero       VARCHAR(20)  NULL,
    ADD COLUMN IF NOT EXISTS endereco_complemento  VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS endereco_bairro       VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS endereco_cidade       VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS endereco_uf           VARCHAR(2)   NULL;

-- ============================================================
-- 2. hora_venda — origem_criacao (DANFE legacy vs MANUAL novo fluxo)
-- ============================================================
-- Marca como a venda entrou no sistema:
--   'DANFE'  - import de NF de saida via PDF (fluxo original)
--   'MANUAL' - criada via tela /hora/tagplus/pedido-venda/novo (novo fluxo)
-- Default 'DANFE' para preservar semantica das linhas existentes.
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS origem_criacao VARCHAR(20) NULL DEFAULT 'DANFE';

-- Backfill defensivo: garante que linhas pre-existentes recebam 'DANFE'
-- (DEFAULT so se aplica a INSERTs futuros; UPDATE explicito cobre o backlog).
UPDATE hora_venda
   SET origem_criacao = 'DANFE'
 WHERE origem_criacao IS NULL;

-- ============================================================
-- 3. Indice utilitario para filtragem futura por origem
-- ============================================================
CREATE INDEX IF NOT EXISTS ix_hora_venda_origem_criacao
    ON hora_venda(origem_criacao);
