#!/usr/bin/env python3
"""
Script de Migração: Criar tabela tagplus_oauth_token

Cria tabela para armazenar tokens OAuth2 do TagPlus de forma PERSISTENTE
Resolve problema de perda de tokens após deploy

Data: 2025-11-06
"""

import sys
import os

# Adiciona path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

def criar_tabela_tagplus_oauth_token():
    """Cria tabela tagplus_oauth_token no PostgreSQL"""

    app = create_app()

    with app.app_context():
        try:
            print("=" * 70)
            print("🔧 CRIANDO TABELA: tagplus_oauth_token")
            print("=" * 70)

            # SQL para criar a tabela
            sql = """
            CREATE TABLE IF NOT EXISTS tagplus_oauth_token (
                id SERIAL PRIMARY KEY,

                -- Tipo de API (único)
                api_type VARCHAR(50) NOT NULL UNIQUE,

                -- Tokens OAuth2
                access_token TEXT NOT NULL,
                refresh_token TEXT,

                -- Controle de expiração
                expires_at TIMESTAMP,

                -- Metadados OAuth
                token_type VARCHAR(20) DEFAULT 'Bearer',
                scope VARCHAR(255),

                -- Auditoria e estatísticas
                criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ultimo_refresh TIMESTAMP,
                total_refreshes INTEGER DEFAULT 0,
                ultima_requisicao TIMESTAMP,

                -- Status
                ativo BOOLEAN DEFAULT TRUE NOT NULL
            );

            -- Índices
            CREATE INDEX IF NOT EXISTS idx_tagplus_oauth_api_type
                ON tagplus_oauth_token(api_type);

            CREATE INDEX IF NOT EXISTS idx_tagplus_oauth_ativo
                ON tagplus_oauth_token(ativo);

            -- Comentários
            COMMENT ON TABLE tagplus_oauth_token IS
                'Armazena tokens OAuth2 do TagPlus de forma persistente (sobrevive deploys)';

            COMMENT ON COLUMN tagplus_oauth_token.api_type IS
                'Tipo da API: clientes, notas, produtos';

            COMMENT ON COLUMN tagplus_oauth_token.access_token IS
                'Token de acesso (expira em 24h)';

            COMMENT ON COLUMN tagplus_oauth_token.refresh_token IS
                'Token de renovação (dura 30-90 dias)';

            COMMENT ON COLUMN tagplus_oauth_token.expires_at IS
                'Timestamp de expiração do access_token';

            COMMENT ON COLUMN tagplus_oauth_token.total_refreshes IS
                'Contador de quantas vezes o token foi renovado';
            """

            # Executa SQL
            db.session.execute(text(sql))
            db.session.commit()

            print("\n✅ Tabela criada com sucesso!")
            print("\n📊 Estrutura criada:")
            print("   - Tabela: tagplus_oauth_token")
            print("   - Índices: idx_tagplus_oauth_api_type, idx_tagplus_oauth_ativo")
            print("   - Campos principais: access_token, refresh_token, expires_at")
            print("\n" + "=" * 70)

        except Exception as e:
            print(f"\n❌ ERRO ao criar tabela: {e}")
            db.session.rollback()
            raise


if __name__ == "__main__":
    criar_tabela_tagplus_oauth_token()
    print("\n🎉 Migração concluída!")
