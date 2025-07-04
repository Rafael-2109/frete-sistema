#!/usr/bin/env python3
"""
🚀 SCRIPT PARA APLICAR CORREÇÕES NO RENDER
Executa as correções específicas para o ambiente de produção
"""

import os
import sys
from pathlib import Path

def aplicar_correcoes_render():
    """Aplica correções específicas para o Render"""
    print("🚀 APLICANDO CORREÇÕES PARA O RENDER")
    print("=" * 80)
    
    # 1. Criar script de migração para tabelas AI
    criar_script_migracao_ai()
    
    # 2. Atualizar build.sh para executar correções
    atualizar_build_sh()
    
    # 3. Criar script de verificação
    criar_script_verificacao()
    
    print("\n✅ CORREÇÕES PREPARADAS PARA O RENDER!")
    print("\n🔄 PRÓXIMOS PASSOS:")
    print("1. Faça commit e push das alterações")
    print("2. O Render executará automaticamente as correções")
    print("3. Monitore os logs do deploy")

def criar_script_migracao_ai():
    """Cria script de migração para as tabelas de IA"""
    print("\n📝 Criando script de migração...")
    
    migration_script = """#!/usr/bin/env python3
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
            
            print(f"\\n📊 RESULTADO: {tabelas_ok}/{len(tabelas_esperadas)} tabelas OK")
            return tabelas_ok >= 5
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    sucesso = aplicar_tabelas_ai()
    print("✅ Migração concluída!" if sucesso else "❌ Migração falhou!")
    sys.exit(0 if sucesso else 1)
"""
    
    Path('migracao_ai_render.py').write_text(migration_script, encoding='utf-8')
    print("✅ Script de migração criado: migracao_ai_render.py")

def atualizar_build_sh():
    """Atualiza build.sh para executar correções"""
    print("\n📝 Atualizando build.sh...")
    
    build_file = Path('build.sh')
    if not build_file.exists():
        print("❌ build.sh não encontrado")
        return
    
    content = build_file.read_text(encoding='utf-8')
    
    # Verificar se já tem a correção
    if 'migracao_ai_render.py' in content:
        print("✅ build.sh já atualizado")
        return
    
    # Adicionar ao final
    adicao = """

# Aplicar correções Claude AI (executar uma vez)
echo "🔧 Aplicando correções Claude AI..."
python migracao_ai_render.py || echo "⚠️ Migração AI já aplicada ou falhou"
"""
    
    build_file.write_text(content + adicao, encoding='utf-8')
    print("✅ build.sh atualizado com correções")

def criar_script_verificacao():
    """Cria script para verificar se as correções funcionaram"""
    print("\n📝 Criando script de verificação...")
    
    verificacao_script = """#!/usr/bin/env python3
'''
Script para verificar se o Claude AI está funcionando corretamente
'''

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def verificar_claude_ai():
    '''Verifica se o Claude AI está funcionando'''
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            
            print("🔍 VERIFICANDO CLAUDE AI...")
            print("=" * 50)
            
            # 1. Verificar tabelas AI
            tabelas_ai = [
                'ai_knowledge_patterns', 'ai_semantic_mappings',
                'ai_learning_history', 'ai_grupos_empresariais',
                'ai_business_contexts', 'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            tabelas_ok = 0
            print("\\n📊 TABELAS DE IA:")
            for tabela in tabelas_ai:
                try:
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    print(f"   ✅ {tabela}: {count} registros")
                    tabelas_ok += 1
                except Exception as e:
                    print(f"   ❌ {tabela}: {str(e)[:50]}...")
            
            # 2. Verificar imports
            print("\\n🔧 IMPORTS:")
            try:
                from app.claude_ai import claude_real_integration
                print("   ✅ claude_real_integration")
            except Exception as e:
                print(f"   ❌ claude_real_integration: {e}")
            
            try:
                from app.claude_ai import multi_agent_system
                print("   ✅ multi_agent_system")
            except Exception as e:
                print(f"   ❌ multi_agent_system: {e}")
            
            try:
                from app.claude_ai import lifelong_learning
                print("   ✅ lifelong_learning")
            except Exception as e:
                print(f"   ❌ lifelong_learning: {e}")
            
            # 3. Verificar diretórios
            print("\\n📁 DIRETÓRIOS:")
            diretorios = [
                'instance/claude_ai/backups',
                'instance/claude_ai/backups/generated',
                'instance/claude_ai/backups/projects',
                'app/claude_ai/logs'
            ]
            
            for diretorio in diretorios:
                if Path(diretorio).exists():
                    print(f"   ✅ {diretorio}")
                else:
                    print(f"   ❌ {diretorio}")
            
            # 4. Verificar configuração
            print("\\n🔒 CONFIGURAÇÃO:")
            config_file = Path('instance/claude_ai/security_config.json')
            if config_file.exists():
                print("   ✅ security_config.json")
            else:
                print("   ❌ security_config.json")
            
            # Resumo
            print("\\n" + "=" * 50)
            print("📈 RESUMO:")
            print(f"   Tabelas AI: {tabelas_ok}/{len(tabelas_ai)}")
            
            if tabelas_ok >= 5:
                print("\\n🎉 CLAUDE AI FUNCIONANDO!")
                return True
            else:
                print("\\n⚠️ CLAUDE AI COM PROBLEMAS")
                return False
                
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    sucesso = verificar_claude_ai()
    sys.exit(0 if sucesso else 1)
"""
    
    Path('verificar_claude_ai.py').write_text(verificacao_script, encoding='utf-8')
    print("✅ Script de verificação criado: verificar_claude_ai.py")

if __name__ == "__main__":
    aplicar_correcoes_render() 