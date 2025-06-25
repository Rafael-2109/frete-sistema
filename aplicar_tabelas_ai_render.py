#!/usr/bin/env python3
"""
🚀 APLICAR TABELAS DE APRENDIZADO NO RENDER (PostgreSQL)
Script para criar as tabelas de IA diretamente no banco de produção
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from config import Config

def aplicar_tabelas_render():
    """Aplica as tabelas de aprendizado no PostgreSQL do Render"""
    print("\n" + "="*80)
    print("🚀 APLICANDO TABELAS DE APRENDIZADO NO RENDER")
    print("="*80 + "\n")
    
    # Verificar se está em produção
    is_production = os.getenv('RENDER', 'false').lower() == 'true'
    is_postgresql = 'postgresql' in Config.SQLALCHEMY_DATABASE_URI.lower()
    
    print(f"🗄️ Banco de dados: {'PostgreSQL' if is_postgresql else 'SQLite'}")
    print(f"🌍 Ambiente: {'Produção (Render)' if is_production else 'Desenvolvimento'}")
    
    if not is_postgresql:
        print("\n⚠️ ATENÇÃO: Este script é para PostgreSQL!")
        print("Para aplicar no Render, execute diretamente no console do Render:")
        print("  python aplicar_tabelas_ai_render.py")
        return False
    
    app = create_app()
    
    with app.app_context():
        try:
            # SQL para PostgreSQL
            sql_commands = [
                # 1. PADRÕES DE CONSULTA APRENDIDOS
                """
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
                """,
                
                # 2. MAPEAMENTOS SEMÂNTICOS APRENDIDOS
                """
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
                """,
                
                # 3. CORREÇÕES E FEEDBACK HISTÓRICO
                """
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
                """,
                
                # 4. GRUPOS EMPRESARIAIS APRENDIDOS
                """
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
                """,
                
                # 5. CONTEXTOS DE NEGÓCIO APRENDIDOS
                """
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
                """,
                
                # 6. RESPOSTAS MODELO (TEMPLATES APRENDIDOS)
                """
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
                """,
                
                # 7. MÉTRICAS DE APRENDIZADO
                """
                CREATE TABLE IF NOT EXISTS ai_learning_metrics (
                    id SERIAL PRIMARY KEY,
                    metrica_tipo VARCHAR(50) NOT NULL,
                    metrica_valor FLOAT NOT NULL,
                    contexto JSONB,
                    periodo_inicio TIMESTAMP NOT NULL,
                    periodo_fim TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """,
                
                # ÍNDICES PARA PERFORMANCE
                "CREATE INDEX IF NOT EXISTS idx_patterns_type ON ai_knowledge_patterns(pattern_type)",
                "CREATE INDEX IF NOT EXISTS idx_patterns_confidence ON ai_knowledge_patterns(confidence DESC)",
                "CREATE INDEX IF NOT EXISTS idx_semantic_termo ON ai_semantic_mappings(termo_usuario)",
                "CREATE INDEX IF NOT EXISTS idx_semantic_campo ON ai_semantic_mappings(campo_sistema)",
                "CREATE INDEX IF NOT EXISTS idx_learning_created ON ai_learning_history(created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_learning_usuario ON ai_learning_history(usuario_id)",
                "CREATE INDEX IF NOT EXISTS idx_grupos_nome ON ai_grupos_empresariais(nome_grupo)",
                "CREATE INDEX IF NOT EXISTS idx_grupos_ativo ON ai_grupos_empresariais(ativo)",
                "CREATE INDEX IF NOT EXISTS idx_contexts_ativo ON ai_business_contexts(ativo)",
                "CREATE INDEX IF NOT EXISTS idx_templates_tipo ON ai_response_templates(tipo_consulta)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_tipo ON ai_learning_metrics(metrica_tipo)",
                "CREATE INDEX IF NOT EXISTS idx_metrics_periodo ON ai_learning_metrics(periodo_inicio, periodo_fim)"
            ]
            
            # Executar comandos
            print(f"🔧 Aplicando {len(sql_commands)} comandos SQL...")
            
            sucesso = 0
            erros = 0
            
            for i, comando in enumerate(sql_commands, 1):
                try:
                    db.session.execute(text(comando))
                    db.session.commit()
                    sucesso += 1
                    if i <= 7:  # Apenas para tabelas principais
                        print(f"✅ Tabela {i}/7 criada")
                except Exception as e:
                    erros += 1
                    if "already exists" in str(e).lower():
                        print(f"ℹ️ Tabela/índice {i} já existe (OK)")
                        sucesso += 1
                    else:
                        print(f"❌ Erro no comando {i}: {str(e)[:80]}...")
                    db.session.rollback()
            
            print(f"\n📊 RESUMO: {sucesso} comandos executados, {erros} erros")
            
            # Inserir grupos empresariais iniciais
            print("\n📝 Inserindo grupos empresariais conhecidos...")
            
            grupos = [
                {
                    'nome': 'Assai',
                    'tipo': 'Atacarejo',
                    'cnpjs': ['06.057.223/'],
                    'palavras': ['assai', 'assaí'],
                    'filtro': '%assai%'
                },
                {
                    'nome': 'Atacadão',
                    'tipo': 'Atacarejo',
                    'cnpjs': ['75.315.333/', '00.063.960/', '93.209.765/'],
                    'palavras': ['atacadao', 'atacadão'],
                    'filtro': '%atacad%'
                },
                {
                    'nome': 'Carrefour',
                    'tipo': 'Varejo',
                    'cnpjs': ['45.543.915/'],
                    'palavras': ['carrefour'],
                    'filtro': '%carrefour%'
                },
                {
                    'nome': 'Tenda',
                    'tipo': 'Atacarejo',
                    'cnpjs': ['01.157.555/'],
                    'palavras': ['tenda'],
                    'filtro': '%tenda%'
                },
                {
                    'nome': 'Mateus',
                    'tipo': 'Varejo Regional',
                    'cnpjs': ['12.545.228/', '58.217.678/', '23.583.231/'],
                    'palavras': ['mateus', 'grupo mateus'],
                    'filtro': '%mateus%'
                },
                {
                    'nome': 'Fort',
                    'tipo': 'Atacarejo',
                    'cnpjs': ['13.481.309/'],
                    'palavras': ['fort', 'fort atacadista'],
                    'filtro': '%fort%'
                }
            ]
            
            for grupo in grupos:
                try:
                    # Verificar se já existe
                    existe = db.session.execute(
                        text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE nome_grupo = :nome"),
                        {"nome": grupo['nome']}
                    ).scalar()
                    
                    if existe == 0:
                        # PostgreSQL usa arrays reais
                        db.session.execute(
                            text("""
                                INSERT INTO ai_grupos_empresariais 
                                (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, filtro_sql)
                                VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro)
                            """),
                            {
                                "nome": grupo['nome'],
                                "tipo": grupo['tipo'],
                                "cnpjs": grupo['cnpjs'],  # PostgreSQL aceita arrays Python
                                "palavras": grupo['palavras'],
                                "filtro": grupo['filtro']
                            }
                        )
                        print(f"   ✅ {grupo['nome']}")
                    else:
                        print(f"   ℹ️ {grupo['nome']} já existe")
                except Exception as e:
                    print(f"   ❌ Erro ao inserir {grupo['nome']}: {e}")
            
            db.session.commit()
            
            # Verificar tabelas criadas
            print("\n📊 Verificando tabelas criadas...")
            
            tabelas_verificar = [
                'ai_knowledge_patterns',
                'ai_semantic_mappings', 
                'ai_learning_history',
                'ai_grupos_empresariais',
                'ai_business_contexts',
                'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            for tabela in tabelas_verificar:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    print(f"   ✅ {tabela}: {count} registros")
                except:
                    print(f"   ❌ {tabela}: Não encontrada")
            
            print("\n✅ TABELAS DE APRENDIZADO APLICADAS COM SUCESSO!")
            print("\n🚀 PRÓXIMOS PASSOS:")
            print("1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente do Render")
            print("2. O sistema começará a aprender automaticamente")
            print("3. Monitore os logs para ver o aprendizado em ação")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    sucesso = aplicar_tabelas_render()
    
    print(f"\n🕐 Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if not sucesso:
        print("\n❌ Houve erros na aplicação. Verifique os logs acima.")
    
    print("\n" + "="*80) 