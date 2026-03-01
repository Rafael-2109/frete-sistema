-- Migration: Criar tabelas do modulo de Seguranca
-- Executar no Render Shell (SQL idempotente)

-- 1. seguranca_varreduras
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seguranca_varreduras') THEN
        CREATE TABLE seguranca_varreduras (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'EM_EXECUCAO',
            iniciado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TIMESTAMP,
            total_verificados INTEGER DEFAULT 0,
            total_vulnerabilidades INTEGER DEFAULT 0,
            detalhes JSONB,
            disparado_por VARCHAR(120)
        );
        RAISE NOTICE 'Tabela seguranca_varreduras criada';
    ELSE
        RAISE NOTICE 'Tabela seguranca_varreduras ja existe';
    END IF;
END $$;

-- 2. seguranca_vulnerabilidades
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seguranca_vulnerabilidades') THEN
        CREATE TABLE seguranca_vulnerabilidades (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES usuarios(id),
            varredura_id INTEGER REFERENCES seguranca_varreduras(id),
            categoria VARCHAR(30) NOT NULL,
            severidade VARCHAR(10) NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            descricao TEXT,
            dados JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
            notificado BOOLEAN DEFAULT FALSE,
            notificado_em TIMESTAMP,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_seguranca_vuln_user_cat_titulo
                UNIQUE (user_id, categoria, titulo)
        );

        CREATE INDEX IF NOT EXISTS ix_seguranca_vuln_user_status
            ON seguranca_vulnerabilidades (user_id, status);
        CREATE INDEX IF NOT EXISTS ix_seguranca_vuln_cat_sev
            ON seguranca_vulnerabilidades (categoria, severidade);

        RAISE NOTICE 'Tabela seguranca_vulnerabilidades criada';
    ELSE
        RAISE NOTICE 'Tabela seguranca_vulnerabilidades ja existe';
    END IF;
END $$;

-- 3. seguranca_scores
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seguranca_scores') THEN
        CREATE TABLE seguranca_scores (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES usuarios(id),
            score INTEGER NOT NULL,
            componentes JSONB,
            vulnerabilidades_abertas INTEGER DEFAULT 0,
            vulnerabilidades_criticas INTEGER DEFAULT 0,
            calculado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_seguranca_score_user_calc
            ON seguranca_scores (user_id, calculado_em);

        RAISE NOTICE 'Tabela seguranca_scores criada';
    ELSE
        RAISE NOTICE 'Tabela seguranca_scores ja existe';
    END IF;
END $$;

-- 4. seguranca_config
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'seguranca_config') THEN
        CREATE TABLE seguranca_config (
            id SERIAL PRIMARY KEY,
            chave VARCHAR(100) UNIQUE NOT NULL,
            valor TEXT,
            descricao VARCHAR(300),
            atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_por VARCHAR(120)
        );

        INSERT INTO seguranca_config (chave, valor, descricao) VALUES
        ('hibp_api_key', '', 'API Key do HaveIBeenPwned (opcional, email breaches)'),
        ('scan_interval_hours', '24', 'Intervalo entre varreduras automaticas (horas)'),
        ('password_min_entropy', '3', 'Score minimo de senha (0-4, zxcvbn)'),
        ('domains_to_monitor', '', 'Dominios adicionais para monitorar (separados por virgula)'),
        ('auto_scan_enabled', 'true', 'Habilitar varredura automatica');

        RAISE NOTICE 'Tabela seguranca_config criada com defaults';
    ELSE
        RAISE NOTICE 'Tabela seguranca_config ja existe';
    END IF;
END $$;
