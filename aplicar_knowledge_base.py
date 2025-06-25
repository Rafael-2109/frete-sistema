#!/usr/bin/env python3
"""
🧠 APLICAR BANCO DE CONHECIMENTO VITALÍCIO
Script para criar as tabelas de aprendizado permanente no banco de dados
Funciona tanto em produção (PostgreSQL) quanto local (SQLite)
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from config import Config

def aplicar_knowledge_base():
    """Aplica o banco de conhecimento vitalício"""
    print("\n" + "="*80)
    print("🧠 APLICANDO BANCO DE CONHECIMENTO VITALÍCIO")
    print("="*80 + "\n")
    
    app = create_app()
    
    # Detectar tipo de banco
    is_postgresql = 'postgresql' in Config.SQLALCHEMY_DATABASE_URI.lower()
    is_production = os.getenv('RENDER', 'false').lower() == 'true' or is_postgresql
    
    print(f"🗄️ Banco de dados: {'PostgreSQL (Produção)' if is_postgresql else 'SQLite (Local)'}")
    print(f"🌍 Ambiente: {'Produção (Render)' if is_production else 'Desenvolvimento'}")
    
    with app.app_context():
        try:
            # SQLite precisa de sintaxe diferente
            if not is_postgresql:
                print("\n⚠️ SQLite detectado - usando sintaxe simplificada")
                
                # Criar tabelas básicas para SQLite
                sql_sqlite = """
-- 1. PADRÕES DE CONSULTA APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_knowledge_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type VARCHAR(50) NOT NULL,
    pattern_text TEXT NOT NULL,
    interpretation TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    usage_count INTEGER DEFAULT 1,
    success_rate FLOAT DEFAULT 0.5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    UNIQUE(pattern_type, pattern_text)
);

-- 2. MAPEAMENTOS SEMÂNTICOS APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_semantic_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    termo_usuario TEXT NOT NULL,
    campo_sistema VARCHAR(100) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    contexto TEXT,
    frequencia INTEGER DEFAULT 1,
    ultima_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validado INTEGER DEFAULT 0,
    validado_por VARCHAR(100),
    validado_em TIMESTAMP,
    UNIQUE(termo_usuario, campo_sistema, modelo)
);

-- 3. CORREÇÕES E FEEDBACK HISTÓRICO
CREATE TABLE IF NOT EXISTS ai_learning_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consulta_original TEXT NOT NULL,
    interpretacao_inicial TEXT NOT NULL,
    resposta_inicial TEXT,
    feedback_usuario TEXT,
    interpretacao_corrigida TEXT,
    resposta_corrigida TEXT,
    tipo_correcao VARCHAR(50),
    aprendizado_extraido TEXT,
    usuario_id INTEGER,
    sessao_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. GRUPOS EMPRESARIAIS APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_grupos_empresariais (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_grupo VARCHAR(200) NOT NULL UNIQUE,
    tipo_negocio VARCHAR(100),
    cnpj_prefixos TEXT,
    palavras_chave TEXT,
    filtro_sql TEXT NOT NULL,
    regras_deteccao TEXT,
    estatisticas TEXT,
    ativo INTEGER DEFAULT 1,
    aprendido_automaticamente INTEGER DEFAULT 0,
    confirmado_por VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. CONTEXTOS DE NEGÓCIO APRENDIDOS
CREATE TABLE IF NOT EXISTS ai_business_contexts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contexto_nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    regras TEXT NOT NULL,
    exemplos TEXT,
    restricoes TEXT,
    prioridade INTEGER DEFAULT 50,
    ativo INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. RESPOSTAS MODELO (TEMPLATES APRENDIDOS)
CREATE TABLE IF NOT EXISTS ai_response_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_consulta VARCHAR(100) NOT NULL,
    contexto VARCHAR(100),
    template_resposta TEXT NOT NULL,
    variaveis_necessarias TEXT,
    exemplo_uso TEXT,
    taxa_satisfacao FLOAT DEFAULT 0.5,
    uso_count INTEGER DEFAULT 0,
    ativo INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. MÉTRICAS DE APRENDIZADO
CREATE TABLE IF NOT EXISTS ai_learning_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metrica_tipo VARCHAR(50) NOT NULL,
    metrica_valor FLOAT NOT NULL,
    contexto TEXT,
    periodo_inicio TIMESTAMP NOT NULL,
    periodo_fim TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ÍNDICES BÁSICOS PARA SQLITE
CREATE INDEX IF NOT EXISTS idx_patterns_type ON ai_knowledge_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_semantic_termo ON ai_semantic_mappings(termo_usuario);
CREATE INDEX IF NOT EXISTS idx_learning_created ON ai_learning_history(created_at);
CREATE INDEX IF NOT EXISTS idx_grupos_nome ON ai_grupos_empresariais(nome_grupo);
"""
                
                # Executar comandos SQLite
                comandos = [cmd.strip() for cmd in sql_sqlite.split(';') if cmd.strip()]
                
            else:
                # PostgreSQL - usar arquivo original
                sql_file = os.path.join(os.path.dirname(__file__), 'app', 'claude_ai', 'knowledge_base.sql')
                
                if not os.path.exists(sql_file):
                    print(f"❌ Arquivo não encontrado: {sql_file}")
                    return False
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                print("📄 Arquivo SQL PostgreSQL lido com sucesso")
                comandos = [cmd.strip() for cmd in sql_content.split(';') if cmd.strip()]
            
            # Executar comandos
            print(f"\n🔧 Aplicando {len(comandos)} comandos SQL...")
            
            sucesso = 0
            erros = 0
            
            for i, comando in enumerate(comandos, 1):
                try:
                    if comando and not comando.startswith('--'):
                        # Pular comandos específicos do PostgreSQL no SQLite
                        if not is_postgresql and any(x in comando.upper() for x in [
                            'JSONB', 'SERIAL', 'TEXT[]', '::jsonb', 'USING GIN', 
                            'OR REPLACE', 'COMMENT ON', '$$ LANGUAGE', 'TRIGGER'
                        ]):
                            print(f"[{i}/{len(comandos)}] Pulando comando PostgreSQL...")
                            continue
                        
                        db.session.execute(text(comando))
                        db.session.commit()
                        sucesso += 1
                        
                except Exception as e:
                    erros += 1
                    if "already exists" in str(e).lower():
                        print(f"[{i}/{len(comandos)}] Tabela/índice já existe (OK)")
                        sucesso += 1
                    else:
                        print(f"[{i}/{len(comandos)}] ⚠️ Erro: {str(e)[:80]}...")
                    db.session.rollback()
            
            print(f"\n📊 RESUMO: {sucesso} comandos executados, {erros} erros")
            
            # Verificar tabelas criadas
            print("\n🔍 Verificando tabelas criadas...")
            
            tabelas_esperadas = [
                'ai_knowledge_patterns',
                'ai_semantic_mappings',
                'ai_learning_history',
                'ai_grupos_empresariais',
                'ai_business_contexts',
                'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            tabelas_criadas = 0
            for tabela in tabelas_esperadas:
                try:
                    result = db.session.execute(
                        text(f"SELECT COUNT(*) FROM {tabela}")
                    ).scalar()
                    print(f"   ✅ {tabela}: {result} registros")
                    tabelas_criadas += 1
                except Exception as e:
                    print(f"   ❌ {tabela}: Não encontrada")
            
            if tabelas_criadas == 0:
                print("\n❌ ERRO: Nenhuma tabela foi criada!")
                return False
            
            # Inserir dados iniciais
            print("\n📝 Inserindo dados iniciais...")
            
            try:
                # Verificar se já existem grupos
                grupos_existentes = db.session.execute(
                    text("SELECT COUNT(*) FROM ai_grupos_empresariais")
                ).scalar()
                
                if grupos_existentes == 0:
                    print("   Inserindo grupos empresariais conhecidos...")
                    
                    grupos_iniciais = [
                        {
                            'nome': 'Assai',
                            'tipo': 'Atacarejo',
                            'cnpjs': '["06.057.223/"]',
                            'palavras': '["assai", "assaí"]',
                            'filtro': '%assai%'
                        },
                        {
                            'nome': 'Atacadão',
                            'tipo': 'Atacarejo',
                            'cnpjs': '["75.315.333/", "00.063.960/", "93.209.765/"]',
                            'palavras': '["atacadao", "atacadão"]',
                            'filtro': '%atacad%'
                        },
                        {
                            'nome': 'Carrefour',
                            'tipo': 'Varejo',
                            'cnpjs': '["45.543.915/"]',
                            'palavras': '["carrefour"]',
                            'filtro': '%carrefour%'
                        },
                        {
                            'nome': 'Tenda',
                            'tipo': 'Atacarejo',
                            'cnpjs': '["01.157.555/"]',
                            'palavras': '["tenda"]',
                            'filtro': '%tenda%'
                        },
                        {
                            'nome': 'Mateus',
                            'tipo': 'Varejo Regional',
                            'cnpjs': '["12.545.228/", "58.217.678/", "23.583.231/"]',
                            'palavras': '["mateus", "grupo mateus"]',
                            'filtro': '%mateus%'
                        }
                    ]
                    
                    for grupo in grupos_iniciais:
                        try:
                            # SQLite usa 0/1 para boolean
                            ativo_val = 1 if not is_postgresql else 'TRUE'
                            auto_val = 0 if not is_postgresql else 'FALSE'
                            
                            db.session.execute(
                                text("""
                                    INSERT INTO ai_grupos_empresariais 
                                    (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, 
                                     filtro_sql, ativo, aprendido_automaticamente)
                                    VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro, :ativo, :auto)
                                """),
                                {
                                    'nome': grupo['nome'],
                                    'tipo': grupo['tipo'],
                                    'cnpjs': grupo['cnpjs'],
                                    'palavras': grupo['palavras'],
                                    'filtro': grupo['filtro'],
                                    'ativo': ativo_val,
                                    'auto': auto_val
                                }
                            )
                            print(f"      ✅ {grupo['nome']} inserido")
                        except Exception as e:
                            print(f"      ⚠️ Erro ao inserir {grupo['nome']}: {str(e)[:50]}...")
                    
                    db.session.commit()
                    print(f"   ✅ Grupos empresariais inseridos")
                else:
                    print(f"   ℹ️ Já existem {grupos_existentes} grupos cadastrados")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao inserir dados iniciais: {e}")
                db.session.rollback()
            
            print("\n✅ BANCO DE CONHECIMENTO APLICADO!")
            
            # Mostrar estatísticas
            print("\n📊 ESTATÍSTICAS DO SISTEMA DE APRENDIZADO:")
            
            try:
                from app.claude_ai.lifelong_learning import get_lifelong_learning
                lifelong = get_lifelong_learning()
                stats = lifelong.obter_estatisticas_aprendizado()
                
                print(f"   • Padrões aprendidos: {stats.get('total_padroes', 0)}")
                print(f"   • Padrões confiáveis: {stats.get('padroes_confiaveis', 0)}")
                print(f"   • Taxa de confiança: {stats.get('taxa_confianca', 0):.1f}%")
                print(f"   • Grupos empresariais: {stats.get('total_grupos', 0)}")
                print(f"   • Mapeamentos semânticos: {stats.get('total_mapeamentos', 0)}")
                print(f"   • Aprendizado semanal: {stats.get('aprendizado_semanal', 0)}")
                print(f"   • Status: {stats.get('status', 'inativo')}")
                
            except Exception as e:
                print(f"   ⚠️ Não foi possível obter estatísticas: {e}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    sucesso = aplicar_knowledge_base()
    
    print(f"\n🕐 Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if sucesso:
        print("\n🎉 SUCESSO! O sistema de aprendizado vitalício está pronto!")
        print("\n💡 PRÓXIMOS PASSOS:")
        print("   1. Configure a ANTHROPIC_API_KEY no ambiente")
        print("   2. O sistema começará a aprender automaticamente")
        print("   3. Quanto mais usar, mais inteligente fica!")
        print("\n🚀 PARA PRODUÇÃO (RENDER):")
        print("   - Faça commit e push das alterações")
        print("   - O Render executará automaticamente")
        print("   - Configure ANTHROPIC_API_KEY nas variáveis de ambiente")
    else:
        print("\n❌ Houve erros na aplicação. Verifique os logs acima.")
    
    print("\n" + "="*80)
    
 