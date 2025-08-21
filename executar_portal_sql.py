#!/usr/bin/env python
"""
Script para executar SQL de criação das tabelas do portal
"""

import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, db
from sqlalchemy import text

def main():
    app = create_app()
    
    with app.app_context():
        try:
            print("🚀 Executando script SQL do portal...")
            
            # Ler arquivo SQL
            sql_file = Path(__file__).parent / 'app' / 'portal' / 'sql' / '001_criar_tabelas_portal.sql'
            
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # Executar diretamente como uma transação única
            db.session.execute(text(sql_content))
            db.session.commit()
            
            # Verificar tabelas criadas
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name LIKE 'portal_%'
                ORDER BY table_name
            """))
            
            tabelas = [row[0] for row in result]
            
            print("\n✅ Script SQL executado com sucesso!")
            print(f"\n📋 Tabelas do portal criadas ({len(tabelas)}):")
            for tabela in tabelas:
                print(f"   - {tabela}")
            
            # Verificar colunas adicionadas em tabelas existentes
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'separacao' 
                AND column_name = 'agendamento_portal_solicitado'
            """))
            
            if result.rowcount > 0:
                print("\n✅ Coluna agendamento_portal_solicitado adicionada em separacao")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            db.session.rollback()
            
            # Tentar executar comando por comando
            print("\n🔄 Tentando executar comando por comando...")
            
            # Simplificar: executar apenas as tabelas principais
            tabelas_sql = [
                """
                CREATE TABLE IF NOT EXISTS portal_integracoes (
                    id SERIAL PRIMARY KEY,
                    portal VARCHAR(50) NOT NULL,
                    lote_id VARCHAR(50) NOT NULL,
                    tipo_lote VARCHAR(20) NOT NULL,
                    protocolo VARCHAR(100) UNIQUE,
                    status VARCHAR(50) DEFAULT 'aguardando',
                    data_solicitacao TIMESTAMP,
                    data_confirmacao TIMESTAMP,
                    data_agendamento DATE,
                    hora_agendamento TIME,
                    usuario_solicitante VARCHAR(100),
                    navegador_sessao_id VARCHAR(100),
                    tentativas INTEGER DEFAULT 0,
                    ultimo_erro TEXT,
                    dados_enviados JSONB,
                    resposta_portal JSONB,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portal_configuracoes (
                    id SERIAL PRIMARY KEY,
                    portal VARCHAR(50) NOT NULL,
                    cnpj_cliente VARCHAR(20),
                    url_portal VARCHAR(255),
                    url_login VARCHAR(255),
                    usuario VARCHAR(100),
                    senha_criptografada VARCHAR(255),
                    totp_secret VARCHAR(100),
                    instrucoes_acesso TEXT,
                    seletores_css JSONB,
                    login_indicators JSONB,
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portal_logs (
                    id SERIAL PRIMARY KEY,
                    integracao_id INTEGER REFERENCES portal_integracoes(id) ON DELETE CASCADE,
                    acao VARCHAR(100),
                    sucesso BOOLEAN,
                    mensagem TEXT,
                    screenshot_path VARCHAR(500),
                    dados_contexto JSONB,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portal_sessoes (
                    id SERIAL PRIMARY KEY,
                    portal VARCHAR(50) NOT NULL,
                    usuario VARCHAR(100),
                    cookies_criptografados TEXT,
                    storage_state JSONB,
                    valido_ate TIMESTAMP,
                    ultima_utilizacao TIMESTAMP,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS portal_atacadao_produto_depara (
                    id SERIAL PRIMARY KEY,
                    codigo_nosso VARCHAR(50) NOT NULL,
                    descricao_nosso VARCHAR(255),
                    codigo_atacadao VARCHAR(50) NOT NULL,
                    descricao_atacadao VARCHAR(255),
                    cnpj_cliente VARCHAR(20),
                    fator_conversao NUMERIC(10, 4) DEFAULT 1.0,
                    observacoes TEXT,
                    ativo BOOLEAN DEFAULT TRUE,
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100)
                )
                """
            ]
            
            for i, sql in enumerate(tabelas_sql, 1):
                try:
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"✅ Tabela {i}/5 criada")
                except Exception as e2:
                    if 'already exists' not in str(e2).lower():
                        print(f"⚠️ Erro na tabela {i}: {str(e2)[:100]}")
                    db.session.rollback()
            
            return False

if __name__ == '__main__':
    sys.exit(0 if main() else 1)