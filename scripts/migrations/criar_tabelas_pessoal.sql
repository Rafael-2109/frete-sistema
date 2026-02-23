-- ==============================================
-- SCRIPT SQL PARA CRIAR TABELAS DO MODULO PESSOAL
-- Executar no Shell do Render
-- ==============================================

-- Tabela 1: pessoal_membros
-- Membros da familia para atribuicao de despesas
CREATE TABLE IF NOT EXISTS pessoal_membros (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    nome_completo VARCHAR(200),
    papel VARCHAR(50),
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Tabela 2: pessoal_contas
-- Contas bancarias e cartoes de credito
CREATE TABLE IF NOT EXISTS pessoal_contas (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    banco VARCHAR(50) NOT NULL DEFAULT 'bradesco',
    agencia VARCHAR(20),
    numero_conta VARCHAR(30),
    ultimos_digitos_cartao VARCHAR(10),
    membro_id INTEGER REFERENCES pessoal_membros(id),
    ativa BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Tabela 3: pessoal_categorias
-- Categorias de despesas e receitas
CREATE TABLE IF NOT EXISTS pessoal_categorias (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL UNIQUE,
    grupo VARCHAR(100) NOT NULL,
    icone VARCHAR(50),
    ordem_exibicao INTEGER DEFAULT 0,
    ativa BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW()
);

-- Tabela 4: pessoal_regras_categorizacao
-- Regras para categorizacao automatica de transacoes
CREATE TABLE IF NOT EXISTS pessoal_regras_categorizacao (
    id SERIAL PRIMARY KEY,
    padrao_historico VARCHAR(300) NOT NULL,
    tipo_regra VARCHAR(20) NOT NULL,
    categoria_id INTEGER REFERENCES pessoal_categorias(id),
    membro_id INTEGER REFERENCES pessoal_membros(id),
    categorias_restritas_ids TEXT,
    vezes_usado INTEGER DEFAULT 0,
    confianca NUMERIC(5,2) DEFAULT 100,
    origem VARCHAR(30) DEFAULT 'semente',
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW()
);

-- Tabela 5: pessoal_exclusoes_empresa
-- Padroes de transacoes empresariais a excluir
CREATE TABLE IF NOT EXISTS pessoal_exclusoes_empresa (
    id SERIAL PRIMARY KEY,
    padrao VARCHAR(200) NOT NULL,
    descricao VARCHAR(200),
    ativo BOOLEAN DEFAULT TRUE
);

-- Tabela 6: pessoal_importacoes
-- Registro de importacoes de extratos/faturas
CREATE TABLE IF NOT EXISTS pessoal_importacoes (
    id SERIAL PRIMARY KEY,
    conta_id INTEGER NOT NULL REFERENCES pessoal_contas(id),
    nome_arquivo VARCHAR(255),
    tipo_arquivo VARCHAR(30),
    periodo_inicio DATE,
    periodo_fim DATE,
    situacao_fatura VARCHAR(30),
    total_linhas INTEGER DEFAULT 0,
    linhas_importadas INTEGER DEFAULT 0,
    linhas_duplicadas INTEGER DEFAULT 0,
    linhas_empresa_filtradas INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'IMPORTADO',
    criado_em TIMESTAMP DEFAULT NOW(),
    criado_por VARCHAR(100)
);

-- Tabela 7: pessoal_transacoes
-- Transacoes financeiras pessoais importadas
CREATE TABLE IF NOT EXISTS pessoal_transacoes (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES pessoal_importacoes(id),
    conta_id INTEGER NOT NULL REFERENCES pessoal_contas(id),
    data DATE NOT NULL,
    historico VARCHAR(500) NOT NULL,
    descricao VARCHAR(500),
    historico_completo VARCHAR(1000),
    documento VARCHAR(50),
    valor NUMERIC(15,2) NOT NULL,
    tipo VARCHAR(10) NOT NULL,
    saldo NUMERIC(15,2),
    valor_dolar NUMERIC(15,4),
    parcela_atual INTEGER,
    parcela_total INTEGER,
    identificador_parcela VARCHAR(100),
    categoria_id INTEGER REFERENCES pessoal_categorias(id),
    regra_id INTEGER REFERENCES pessoal_regras_categorizacao(id),
    categorizacao_auto BOOLEAN DEFAULT FALSE,
    categorizacao_confianca NUMERIC(5,2),
    membro_id INTEGER REFERENCES pessoal_membros(id),
    membro_auto BOOLEAN DEFAULT FALSE,
    excluir_relatorio BOOLEAN DEFAULT FALSE,
    eh_pagamento_cartao BOOLEAN DEFAULT FALSE,
    eh_transferencia_propria BOOLEAN DEFAULT FALSE,
    observacao TEXT,
    status VARCHAR(20) DEFAULT 'PENDENTE',
    hash_transacao VARCHAR(64) NOT NULL UNIQUE,
    criado_em TIMESTAMP DEFAULT NOW(),
    atualizado_em TIMESTAMP DEFAULT NOW(),
    categorizado_em TIMESTAMP,
    categorizado_por VARCHAR(100)
);

-- Indices para pessoal_transacoes
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_data ON pessoal_transacoes(data);
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_conta ON pessoal_transacoes(conta_id);
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_categoria ON pessoal_transacoes(categoria_id);
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_membro ON pessoal_transacoes(membro_id);
CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_status ON pessoal_transacoes(status);

-- Verificar criacao
SELECT table_name
FROM information_schema.tables
WHERE table_name LIKE 'pessoal_%'
ORDER BY table_name;
