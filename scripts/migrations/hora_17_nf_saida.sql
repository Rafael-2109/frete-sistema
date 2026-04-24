-- Migration HORA 17: NF de Saida (venda) + divergencias.
--
-- Extende hora_venda para suportar import de DANFE emitida pela loja HORA:
--   - arquivo_pdf_s3_key, parser_usado, parseada_em, cnpj_emitente
--   - loja_id afrouxado para NULL (quando CNPJ emitente nao bate com loja cadastrada)
--   - forma_pagamento ganha DEFAULT 'NAO_INFORMADO'
-- Cria hora_venda_divergencia para registrar problemas no import
-- (chassi indisponivel, chassi fora da loja, CNPJ emitente desconhecido, etc).
-- Idempotente: IF NOT EXISTS em tudo que e criado; ALTER ... IF EXISTS onde aplicavel.

-- ============================================================
-- 1. hora_venda — novos campos
-- ============================================================
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS arquivo_pdf_s3_key VARCHAR(500) NULL,
    ADD COLUMN IF NOT EXISTS parser_usado VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS parseada_em TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS cnpj_emitente VARCHAR(20) NULL;

-- Indice util para auditoria "esta NF ja foi importada?" via chave_44 ja e UNIQUE.
-- Adicionamos indice em cnpj_emitente para listagens filtradas por loja emitente.
CREATE INDEX IF NOT EXISTS ix_hora_venda_cnpj_emitente
    ON hora_venda(cnpj_emitente);

-- ============================================================
-- 2. hora_venda.loja_id — afrouxa para NULL (fluxo permissivo)
-- ============================================================
-- Quando o CNPJ emitente da NF nao bate com nenhuma HoraLoja ativa, a venda
-- e criada com loja_id=NULL + divergencia CNPJ_DESCONHECIDO. Operador corrige
-- via tela de detalhe (`/hora/vendas/<id>/definir-loja`).
ALTER TABLE hora_venda ALTER COLUMN loja_id DROP NOT NULL;

-- ============================================================
-- 3. hora_venda.forma_pagamento — default 'NAO_INFORMADO'
-- ============================================================
-- Import via DANFE nao extrai forma_pagamento (parser CarVia nao trata o
-- grupo <pag><detPag>). Default preserva NOT NULL e cobre fluxos futuros.
ALTER TABLE hora_venda ALTER COLUMN forma_pagamento SET DEFAULT 'NAO_INFORMADO';

-- ============================================================
-- 4. hora_venda_divergencia — novas divergencias derivadas no import
-- ============================================================
-- Tipos (ver enum TIPOS_DIVERGENCIA_VENDA em venda_service.py):
--   CHASSI_NAO_CADASTRADO  — chassi nunca entrou na HORA (get_or_create_moto criou)
--   CHASSI_INDISPONIVEL    — ultimo evento NAO em EVENTOS_EM_ESTOQUE (ja vendido?)
--   LOJA_DIVERGENTE        — chassi em outra loja (transferencia pendente?)
--   CNPJ_DESCONHECIDO      — emitente nao bate com nenhuma HoraLoja ativa
--   TABELA_PRECO_AUSENTE   — sem HoraTabelaPreco vigente; preco_tabela_ref=preco_final
--   PRECO_ACIMA_TABELA     — preco_final > tabela (acrescimo); item gravado sem desconto
CREATE TABLE IF NOT EXISTS hora_venda_divergencia (
    id BIGSERIAL PRIMARY KEY,
    venda_id INTEGER NOT NULL REFERENCES hora_venda(id) ON DELETE CASCADE,
    numero_chassi VARCHAR(30) NULL REFERENCES hora_moto(numero_chassi),
    tipo VARCHAR(30) NOT NULL,
    detalhe TEXT NULL,
    valor_esperado VARCHAR(200) NULL,
    valor_conferido VARCHAR(200) NULL,
    resolvida_em TIMESTAMP NULL,
    resolvida_por VARCHAR(100) NULL,
    criado_em TIMESTAMP NOT NULL,
    CONSTRAINT uq_hora_venda_divergencia_tipo_chassi
        UNIQUE (venda_id, tipo, numero_chassi)
);

CREATE INDEX IF NOT EXISTS ix_hora_venda_divergencia_venda
    ON hora_venda_divergencia(venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_divergencia_chassi
    ON hora_venda_divergencia(numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_venda_divergencia_tipo
    ON hora_venda_divergencia(tipo);
CREATE INDEX IF NOT EXISTS ix_hora_venda_divergencia_abertas
    ON hora_venda_divergencia(venda_id)
    WHERE resolvida_em IS NULL;

-- ============================================================
-- DEFAULTS para timestamp NOT NULL
-- ============================================================
ALTER TABLE hora_venda_divergencia
    ALTER COLUMN criado_em SET DEFAULT CURRENT_TIMESTAMP;
