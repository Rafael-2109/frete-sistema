#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar tabelas de notificações no banco de dados.

TABELAS CRIADAS:
- alerta_notificacoes: Armazena alertas e notificações do sistema
- webhook_configs: Configurações de webhooks externos

USO LOCAL:
    python scripts/criar_tabelas_notificacoes.py

USO NO RENDER (Shell):
    -- Copie e execute o SQL abaixo no Shell do Render --
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


# SQL para criar tabelas (para uso no Render Shell)
SQL_CREATE_TABLES = """
-- ============================================
-- TABELA: alerta_notificacoes
-- Armazena alertas e notificações do sistema
-- ============================================
CREATE TABLE IF NOT EXISTS alerta_notificacoes (
    id SERIAL PRIMARY KEY,

    -- Identificação do alerta
    tipo VARCHAR(100) NOT NULL,
    nivel VARCHAR(20) NOT NULL DEFAULT 'INFO',

    -- Conteúdo
    titulo VARCHAR(255) NOT NULL,
    mensagem TEXT NOT NULL,
    dados JSONB,

    -- Destinatário (opcional)
    user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,

    -- Canais de entrega
    canais JSONB NOT NULL DEFAULT '["in_app"]',

    -- Status de envio
    status_envio VARCHAR(20) NOT NULL DEFAULT 'pendente',
    status_email VARCHAR(20),
    status_webhook VARCHAR(20),

    -- Detalhes de entrega
    email_destinatario VARCHAR(255),
    webhook_url VARCHAR(500),
    webhook_response JSONB,

    -- Metadados
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    enviado_em TIMESTAMP WITH TIME ZONE,
    lido_em TIMESTAMP WITH TIME ZONE,

    -- Auditoria
    origem VARCHAR(100),
    referencia_id VARCHAR(100),
    referencia_tipo VARCHAR(50),

    -- Tentativas de reenvio
    tentativas_envio INTEGER DEFAULT 0,
    ultimo_erro TEXT
);

-- Índices para consultas frequentes
CREATE INDEX IF NOT EXISTS idx_notif_tipo ON alerta_notificacoes(tipo);
CREATE INDEX IF NOT EXISTS idx_notif_nivel ON alerta_notificacoes(nivel);
CREATE INDEX IF NOT EXISTS idx_notif_tipo_nivel ON alerta_notificacoes(tipo, nivel);
CREATE INDEX IF NOT EXISTS idx_notif_status_criado ON alerta_notificacoes(status_envio, criado_em);
CREATE INDEX IF NOT EXISTS idx_notif_user_status ON alerta_notificacoes(user_id, status_envio);
CREATE INDEX IF NOT EXISTS idx_notif_user_id ON alerta_notificacoes(user_id);

-- ============================================
-- TABELA: webhook_configs
-- Configurações de webhooks externos
-- ============================================
CREATE TABLE IF NOT EXISTS webhook_configs (
    id SERIAL PRIMARY KEY,

    -- Identificação
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,

    -- Configuração do endpoint
    url VARCHAR(500) NOT NULL,
    metodo VARCHAR(10) DEFAULT 'POST',
    headers JSONB,

    -- Autenticação (opcional)
    auth_type VARCHAR(20),
    auth_token VARCHAR(500),

    -- Filtros
    tipos_alerta JSONB,
    niveis_alerta JSONB,

    -- Status
    ativo BOOLEAN DEFAULT TRUE,

    -- Metadados
    criado_em TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    atualizado_em TIMESTAMP WITH TIME ZONE,

    -- Estatísticas
    total_envios INTEGER DEFAULT 0,
    total_falhas INTEGER DEFAULT 0,
    ultimo_envio TIMESTAMP WITH TIME ZONE,
    ultimo_erro TEXT
);

-- Índice para buscar webhooks ativos
CREATE INDEX IF NOT EXISTS idx_webhook_ativo ON webhook_configs(ativo);

-- Comentários nas tabelas
COMMENT ON TABLE alerta_notificacoes IS 'Sistema de alertas e notificações - email, webhook, in_app';
COMMENT ON TABLE webhook_configs IS 'Configurações de webhooks externos para notificações';
"""


def criar_tabelas():
    """Cria as tabelas de notificações no banco de dados."""
    app = create_app()
    with app.app_context():
        try:
            # Executa o SQL
            for statement in SQL_CREATE_TABLES.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    db.session.execute(text(statement))

            db.session.commit()
            print("✅ Tabelas de notificações criadas com sucesso!")
            print("   - alerta_notificacoes")
            print("   - webhook_configs")
            print()
            print("Índices criados:")
            print("   - idx_notif_tipo")
            print("   - idx_notif_nivel")
            print("   - idx_notif_tipo_nivel")
            print("   - idx_notif_status_criado")
            print("   - idx_notif_user_status")
            print("   - idx_notif_user_id")
            print("   - idx_webhook_ativo")

        except Exception as e:
            print(f"❌ Erro ao criar tabelas: {e}")
            db.session.rollback()
            raise


def verificar_tabelas():
    """Verifica se as tabelas foram criadas corretamente."""
    app = create_app()
    with app.app_context():
        try:
            # Verificar alerta_notificacoes
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'alerta_notificacoes'
            """))
            count = result.scalar()
            if count > 0:
                print("✅ Tabela alerta_notificacoes existe")
            else:
                print("❌ Tabela alerta_notificacoes NÃO existe")

            # Verificar webhook_configs
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'webhook_configs'
            """))
            count = result.scalar()
            if count > 0:
                print("✅ Tabela webhook_configs existe")
            else:
                print("❌ Tabela webhook_configs NÃO existe")

            # Contar registros
            result = db.session.execute(text("SELECT COUNT(*) FROM alerta_notificacoes"))
            count_notif = result.scalar()
            print(f"   Total de notificações: {count_notif}")

            result = db.session.execute(text("SELECT COUNT(*) FROM webhook_configs"))
            count_wh = result.scalar()
            print(f"   Total de webhooks configurados: {count_wh}")

        except Exception as e:
            print(f"❌ Erro ao verificar tabelas: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("CRIAÇÃO DE TABELAS DE NOTIFICAÇÕES")
    print("=" * 60)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == '--verificar':
        verificar_tabelas()
    else:
        criar_tabelas()
        print()
        print("Para verificar as tabelas, execute:")
        print("  python scripts/criar_tabelas_notificacoes.py --verificar")
        print()
        print("=" * 60)
        print("SQL PARA RENDER SHELL:")
        print("=" * 60)
        print(SQL_CREATE_TABLES)
