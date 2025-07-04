#!/usr/bin/env python3
'''
Migração para criar tabelas de IA no PostgreSQL do Render
'''

import os
import sys
from pathlib import Path

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent))

def aplicar_tabelas_ai():
    '''Aplica tabelas de IA no PostgreSQL'''
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            
            # Verificar se é PostgreSQL
            engine_url = str(db.engine.url)
            if 'postgresql' not in engine_url:
                print("⚠️ Não é PostgreSQL, pulando...")
                return True
            
            print("🔧 Criando tabelas de IA no PostgreSQL...")
            
            # SQL para PostgreSQL
            sql_commands = [
                '''
                CREATE TABLE IF NOT EXISTS ai_knowledge_patterns (
                    id SERIAL PRIMARY KEY,
                    pattern_type VARCHAR(50) NOT NULL,
                    pattern_text TEXT NOT NULL,
                    interpretation JSONB NOT NULL,
                    confidence FLOAT DEFAULT 0.5,
                    usage_count INTEGER DEFAULT 1,
                    success_rate FLOAT DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(100),
                    UNIQUE(pattern_type, pattern_text)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_semantic_mappings (
                    id SERIAL PRIMARY KEY,
                    termo_usuario TEXT NOT NULL,
                    campo_sistema VARCHAR(100) NOT NULL,
                    modelo VARCHAR(50) NOT NULL,
                    contexto JSONB,
                    frequencia INTEGER DEFAULT 1,
                    ultima_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validado BOOLEAN DEFAULT FALSE,
                    validado_por VARCHAR(100),
                    validado_em TIMESTAMP,
                    UNIQUE(termo_usuario, campo_sistema, modelo)
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_learning_history (
                    id SERIAL PRIMARY KEY,
                    consulta_original TEXT NOT NULL,
                    interpretacao_inicial JSONB NOT NULL,
                    resposta_inicial TEXT,
                    feedback_usuario TEXT,
                    interpretacao_corrigida JSONB,
                    resposta_corrigida TEXT,
                    tipo_correcao VARCHAR(50),
                    aprendizado_extraido JSONB,
                    usuario_id INTEGER,
                    sessao_id VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_grupos_empresariais (
                    id SERIAL PRIMARY KEY,
                    nome_grupo VARCHAR(200) NOT NULL UNIQUE,
                    tipo_negocio VARCHAR(100),
                    cnpj_prefixos TEXT[],
                    palavras_chave TEXT[],
                    filtro_sql TEXT NOT NULL,
                    regras_deteccao JSONB,
                    estatisticas JSONB,
                    ativo BOOLEAN DEFAULT TRUE,
                    aprendido_automaticamente BOOLEAN DEFAULT FALSE,
                    confirmado_por VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_business_contexts (
                    id SERIAL PRIMARY KEY,
                    contexto_nome VARCHAR(100) NOT NULL UNIQUE,
                    descricao TEXT,
                    regras JSONB NOT NULL,
                    exemplos JSONB,
                    restricoes JSONB,
                    prioridade INTEGER DEFAULT 50,
                    ativo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_response_templates (
                    id SERIAL PRIMARY KEY,
                    tipo_consulta VARCHAR(100) NOT NULL,
                    contexto VARCHAR(100),
                    template_resposta TEXT NOT NULL,
                    variaveis_necessarias JSONB,
                    exemplo_uso TEXT,
                    taxa_satisfacao FLOAT DEFAULT 0.5,
                    uso_count INTEGER DEFAULT 0,
                    ativo BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                '''
                CREATE TABLE IF NOT EXISTS ai_learning_metrics (
                    id SERIAL PRIMARY KEY,
                    metrica_tipo VARCHAR(50) NOT NULL,
                    metrica_valor FLOAT NOT NULL,
                    contexto JSONB,
                    periodo_inicio TIMESTAMP NOT NULL,
                    periodo_fim TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                ''',
                # Índices
                'CREATE INDEX IF NOT EXISTS idx_patterns_type ON ai_knowledge_patterns(pattern_type)',
                'CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON ai_knowledge_patterns(confidence DESC)',
                'CREATE INDEX IF NOT EXISTS idx_semantic_termo ON ai_semantic_mappings(termo_usuario)',
                'CREATE INDEX IF NOT EXISTS idx_learning_created ON ai_learning_history(created_at DESC)',
                'CREATE INDEX IF NOT EXISTS idx_grupos_nome ON ai_grupos_empresariais(nome_grupo)',
                'CREATE INDEX IF NOT EXISTS idx_contexts_ativo ON ai_business_contexts(ativo)',
                'CREATE INDEX IF NOT EXISTS idx_templates_tipo ON ai_response_templates(tipo_consulta)',
                'CREATE INDEX IF NOT EXISTS idx_metrics_tipo ON ai_learning_metrics(metrica_tipo)'
            ]
            
            sucesso = 0
            for i, comando in enumerate(sql_commands, 1):
                try:
                    if comando.strip():
                        db.session.execute(text(comando))
                        db.session.commit()
                        sucesso += 1
                        print(f"[{i}/{len(sql_commands)}] ✅")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        sucesso += 1
                        print(f"[{i}/{len(sql_commands)}] ✅ (já existe)")
                    else:
                        print(f"[{i}/{len(sql_commands)}] ❌ {str(e)[:50]}...")
                    try:
                        db.session.rollback()
                    except:
                        pass
            
            # Verificar tabelas criadas
            tabelas_esperadas = [
                'ai_knowledge_patterns', 'ai_semantic_mappings', 
                'ai_learning_history', 'ai_grupos_empresariais',
                'ai_business_contexts', 'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            tabelas_ok = 0
            for tabela in tabelas_esperadas:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    print(f"✅ {tabela}: {count} registros")
                    tabelas_ok += 1
                except:
                    print(f"❌ {tabela}: erro")
            
            print(f"\n📊 RESULTADO: {tabelas_ok}/{len(tabelas_esperadas)} tabelas OK")
            return tabelas_ok >= 5
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = aplicar_tabelas_ai()
    print("✅ Migração concluída!" if sucesso else "❌ Migração falhou!")
    sys.exit(0 if sucesso else 1)
