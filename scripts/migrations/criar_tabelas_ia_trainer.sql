-- Script SQL para criar tabelas do IA Trainer
-- Para executar no Shell do Render
-- Criado em: 23/11/2025

-- ===========================================
-- 1. ATUALIZA TABELA DE PERGUNTAS NAO RESPONDIDAS
-- ===========================================

ALTER TABLE claude_perguntas_nao_respondidas
ADD COLUMN IF NOT EXISTS solucao_criada BOOLEAN DEFAULT FALSE;

-- ===========================================
-- 2. TABELA: sessao_ensino_ia
-- ===========================================

CREATE TABLE IF NOT EXISTS sessao_ensino_ia (
    id SERIAL PRIMARY KEY,

    -- Origem
    pergunta_origem_id INTEGER REFERENCES claude_perguntas_nao_respondidas(id),
    pergunta_original TEXT NOT NULL,

    -- Decomposicao (JSON com partes explicadas)
    decomposicao JSONB,

    -- Debate com Claude (historico de mensagens)
    historico_debate JSONB,

    -- Codigo gerado (referencia para codigo_sistema_gerado)
    codigo_gerado_id INTEGER,

    -- Status da sessao
    -- Valores: 'iniciada', 'decomposta', 'codigo_gerado', 'em_debate',
    --          'testando', 'validada', 'ativada', 'cancelada'
    status VARCHAR(30) DEFAULT 'iniciada' NOT NULL,

    -- Resultado final
    solucao_criada BOOLEAN DEFAULT FALSE NOT NULL,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finalizado_em TIMESTAMP
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_sessao_ensino_pergunta
ON sessao_ensino_ia(pergunta_origem_id);

CREATE INDEX IF NOT EXISTS idx_sessao_ensino_status
ON sessao_ensino_ia(status);

-- ===========================================
-- 3. TABELA: codigo_sistema_gerado
-- ===========================================

CREATE TABLE IF NOT EXISTS codigo_sistema_gerado (
    id SERIAL PRIMARY KEY,

    -- Identificacao
    nome VARCHAR(100) NOT NULL UNIQUE,
    tipo_codigo VARCHAR(30) NOT NULL,
    -- Valores: 'prompt', 'filtro', 'entidade', 'conceito', 'loader', 'capability'
    dominio VARCHAR(50),
    -- Ex: 'carteira', 'estoque', 'fretes'

    -- Gatilhos (palavras que ativam este codigo)
    gatilhos JSONB NOT NULL,
    -- Ex: ["item parcial pendente", "parcial pendente"]
    composicao VARCHAR(200),
    -- Ex: "parcial_pendente + {cliente}"

    -- Definicao tecnica
    definicao_tecnica TEXT NOT NULL,
    -- Para filtro: "CarteiraPrincipal.qtd_saldo > 0 AND qtd_produto > qtd_saldo"
    -- Para loader: codigo Python completo
    models_referenciados JSONB,
    -- Ex: ["CarteiraPrincipal", "Separacao"]
    campos_referenciados JSONB,
    -- Ex: ["qtd_saldo_produto_pedido", "qtd_produto_pedido"]

    -- Documentacao para o Claude
    descricao_claude TEXT NOT NULL,
    exemplos_uso JSONB,
    variacoes TEXT,

    -- Controle de estado
    ativo BOOLEAN DEFAULT FALSE NOT NULL,
    validado BOOLEAN DEFAULT FALSE NOT NULL,
    data_validacao TIMESTAMP,
    validado_por VARCHAR(100),

    -- Resultado do ultimo teste
    ultimo_teste_sucesso BOOLEAN,
    ultimo_teste_erro TEXT,
    ultimo_teste_em TIMESTAMP,

    -- Permissoes
    permite_acao BOOLEAN DEFAULT FALSE NOT NULL,
    apenas_admin BOOLEAN DEFAULT FALSE NOT NULL,

    -- Rastreabilidade
    versao_atual INTEGER DEFAULT 1 NOT NULL,
    pergunta_origem_id INTEGER REFERENCES claude_perguntas_nao_respondidas(id),
    sessao_ensino_id INTEGER REFERENCES sessao_ensino_ia(id),

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_por VARCHAR(100)
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_codigo_nome ON codigo_sistema_gerado(nome);
CREATE INDEX IF NOT EXISTS idx_codigo_tipo_ativo ON codigo_sistema_gerado(tipo_codigo, ativo);
CREATE INDEX IF NOT EXISTS idx_codigo_dominio ON codigo_sistema_gerado(dominio, ativo);
CREATE INDEX IF NOT EXISTS idx_codigo_pergunta ON codigo_sistema_gerado(pergunta_origem_id);

-- Adiciona FK circular em sessao_ensino_ia
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_sessao_codigo_gerado'
    ) THEN
        ALTER TABLE sessao_ensino_ia
        ADD CONSTRAINT fk_sessao_codigo_gerado
        FOREIGN KEY (codigo_gerado_id) REFERENCES codigo_sistema_gerado(id);
    END IF;
END $$;

-- ===========================================
-- 4. TABELA: versao_codigo_gerado
-- ===========================================

CREATE TABLE IF NOT EXISTS versao_codigo_gerado (
    id SERIAL PRIMARY KEY,

    -- Referencia ao codigo
    codigo_id INTEGER NOT NULL REFERENCES codigo_sistema_gerado(id),
    versao INTEGER NOT NULL,

    -- Snapshot desta versao
    tipo_codigo VARCHAR(30) NOT NULL,
    gatilhos JSONB NOT NULL,
    definicao_tecnica TEXT NOT NULL,
    descricao_claude TEXT NOT NULL,

    -- Motivo da alteracao
    motivo_alteracao TEXT,

    -- Resultado de teste desta versao
    teste_sucesso BOOLEAN,
    teste_erro TEXT,

    -- Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,

    -- Constraint unica (codigo + versao)
    CONSTRAINT uk_codigo_versao UNIQUE (codigo_id, versao)
);

-- Indice
CREATE INDEX IF NOT EXISTS idx_versao_codigo ON versao_codigo_gerado(codigo_id);

-- ===========================================
-- 5. COMENTARIOS
-- ===========================================

COMMENT ON TABLE sessao_ensino_ia IS 'Sessoes de ensino do IA Trainer - do problema a solucao';
COMMENT ON TABLE codigo_sistema_gerado IS 'Codigo gerado pelo Claude atraves do sistema de ensino';
COMMENT ON TABLE versao_codigo_gerado IS 'Historico de versoes de cada codigo gerado';

COMMENT ON COLUMN codigo_sistema_gerado.tipo_codigo IS 'prompt, filtro, entidade, conceito, loader, capability';
COMMENT ON COLUMN codigo_sistema_gerado.gatilhos IS 'Palavras/frases que ativam este codigo';
COMMENT ON COLUMN codigo_sistema_gerado.definicao_tecnica IS 'Codigo ou expressao tecnica';
COMMENT ON COLUMN sessao_ensino_ia.status IS 'iniciada, decomposta, codigo_gerado, em_debate, testando, validada, ativada, cancelada';

-- ===========================================
-- VERIFICACAO
-- ===========================================

SELECT 'Tabelas do IA Trainer criadas com sucesso!' AS resultado;
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('sessao_ensino_ia', 'codigo_sistema_gerado', 'versao_codigo_gerado');
