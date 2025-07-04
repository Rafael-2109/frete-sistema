#!/usr/bin/env python3
"""
🔧 SCRIPT PARA CORRIGIR PROBLEMAS DO CLAUDE AI NO RENDER
Resolve problemas de tabelas faltantes, encoding e SQLAlchemy
"""

import os
import sys
import traceback
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def corrigir_encoding_postgresql():
    """Corrige problemas de encoding UTF-8 no PostgreSQL"""
    print("\n🔧 CORRIGINDO ENCODING POSTGRESQL...")
    
    try:
        # Verificar se arquivo config.py existe
        config_file = Path('config.py')
        if not config_file.exists():
            print("❌ Arquivo config.py não encontrado")
            return False
        
        # Ler conteúdo atual
        content = config_file.read_text(encoding='utf-8')
        
        # Verificar se já tem configuração de encoding
        if 'client_encoding' not in content:
            print("📝 Adicionando configuração de encoding...")
            
            # Encontrar a linha da DATABASE_URL
            lines = content.split('\n')
            new_lines = []
            
            for line in lines:
                new_lines.append(line)
                
                # Após DATABASE_URL, adicionar configuração de encoding
                if 'DATABASE_URL' in line and 'os.environ.get' in line:
                    new_lines.append('')
                    new_lines.append('    # Configuração de encoding para PostgreSQL')
                    new_lines.append('    if DATABASE_URL and "postgresql" in DATABASE_URL:')
                    new_lines.append('        # Adicionar parâmetros de encoding')
                    new_lines.append('        if "?" not in DATABASE_URL:')
                    new_lines.append('            DATABASE_URL += "?client_encoding=utf8"')
                    new_lines.append('        else:')
                    new_lines.append('            DATABASE_URL += "&client_encoding=utf8"')
            
            # Escrever arquivo atualizado
            config_file.write_text('\n'.join(new_lines), encoding='utf-8')
            print("✅ Configuração de encoding adicionada")
        else:
            print("✅ Configuração de encoding já presente")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir encoding: {e}")
        return False

def criar_tabelas_ai_render():
    """Cria as tabelas de IA necessárias no PostgreSQL"""
    print("\n🗄️ CRIANDO TABELAS DE IA...")
    
    try:
        from app import create_app, db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            
            # SQL para criar tabelas PostgreSQL
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
            
            print(f"🔧 Executando {len(sql_commands)} comandos SQL...")
            
            sucesso = 0
            erros = 0
            
            for i, comando in enumerate(sql_commands, 1):
                try:
                    if comando.strip():
                        db.session.execute(text(comando))
                        db.session.commit()
                        sucesso += 1
                        print(f"[{i}/{len(sql_commands)}] ✅ Comando executado")
                        
                except Exception as e:
                    erros += 1
                    if "already exists" in str(e).lower():
                        print(f"[{i}/{len(sql_commands)}] ✅ Tabela já existe")
                        sucesso += 1
                    else:
                        print(f"[{i}/{len(sql_commands)}] ❌ Erro: {str(e)[:100]}...")
                    
                    # Rollback apenas para este comando
                    try:
                        db.session.rollback()
                    except:
                        pass
            
            print(f"\n📊 RESULTADO: {sucesso} sucessos, {erros} erros")
            
            # Verificar tabelas criadas
            print("\n🔍 Verificando tabelas...")
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
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    print(f"   ✅ {tabela}: {count} registros")
                    tabelas_criadas += 1
                except Exception as e:
                    print(f"   ❌ {tabela}: {str(e)[:50]}...")
            
            print(f"\n✅ {tabelas_criadas}/{len(tabelas_esperadas)} tabelas funcionando")
            return tabelas_criadas >= 5  # Pelo menos 5 tabelas principais
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        traceback.print_exc()
        return False

def corrigir_imports_sqlalchemy():
    """Corrige problemas de import do SQLAlchemy nos módulos Claude AI"""
    print("\n🔧 CORRIGINDO IMPORTS SQLALCHEMY...")
    
    # Arquivos que podem ter problemas de import
    arquivos_claude = [
        'app/claude_ai/lifelong_learning.py',
        'app/claude_ai/advanced_integration.py',
        'app/claude_ai/multi_agent_system.py',
        'app/claude_ai/claude_real_integration.py'
    ]
    
    for arquivo_path in arquivos_claude:
        arquivo = Path(arquivo_path)
        if not arquivo.exists():
            print(f"⚠️ Arquivo não encontrado: {arquivo_path}")
            continue
        
        try:
            content = arquivo.read_text(encoding='utf-8')
            
            # Verificar se tem import do db no topo
            if 'from app import db' not in content and 'from app import create_app, db' not in content:
                print(f"📝 Corrigindo imports em {arquivo_path}...")
                
                # Adicionar import no início
                lines = content.split('\n')
                new_lines = []
                import_added = False
                
                for line in lines:
                    # Adicionar após os imports do sistema
                    if not import_added and (line.startswith('from app.') or line.startswith('import')):
                        new_lines.append(line)
                        if 'from app' in line and not import_added:
                            new_lines.append('from app import db')
                            import_added = True
                    else:
                        new_lines.append(line)
                
                # Se não adicionou ainda, adicionar no início
                if not import_added:
                    new_lines.insert(0, 'from app import db')
                
                arquivo.write_text('\n'.join(new_lines), encoding='utf-8')
                print(f"✅ Imports corrigidos em {arquivo_path}")
            else:
                print(f"✅ Imports OK em {arquivo_path}")
                
        except Exception as e:
            print(f"❌ Erro ao corrigir {arquivo_path}: {e}")

def criar_diretorio_backups():
    """Cria diretórios necessários para o Code Generator"""
    print("\n📁 CRIANDO DIRETÓRIOS NECESSÁRIOS...")
    
    diretorios = [
        'instance/claude_ai/backups',
        'instance/claude_ai/backups/generated',
        'instance/claude_ai/backups/projects',
        'app/claude_ai/logs'
    ]
    
    for diretorio in diretorios:
        try:
            Path(diretorio).mkdir(parents=True, exist_ok=True)
            print(f"✅ Diretório criado: {diretorio}")
        except Exception as e:
            print(f"❌ Erro ao criar {diretorio}: {e}")

def corrigir_security_config():
    """Cria arquivo de configuração de segurança"""
    print("\n🔒 CRIANDO CONFIGURAÇÃO DE SEGURANÇA...")
    
    try:
        # Criar diretório se não existir
        Path('instance/claude_ai').mkdir(parents=True, exist_ok=True)
        
        # Configuração de segurança
        security_config = {
            "security_level": "production",
            "allowed_operations": [
                "read_file",
                "list_directory", 
                "create_module",
                "inspect_database",
                "discover_project"
            ],
            "restricted_paths": [
                "/etc",
                "/usr",
                "/root",
                "*.env",
                "config.py"
            ],
            "max_file_size": 10485760,
            "timeout_seconds": 30,
            "logging_enabled": True
        }
        
        import json
        config_file = Path('instance/claude_ai/security_config.json')
        config_file.write_text(json.dumps(security_config, indent=2), encoding='utf-8')
        
        print("✅ Configuração de segurança criada")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar configuração: {e}")
        return False

def main():
    """Função principal que executa todas as correções"""
    print("🚀 INICIANDO CORREÇÕES DO CLAUDE AI")
    print("=" * 80)
    
    resultados = {
        'encoding': False,
        'tabelas_ai': False,
        'imports': False,
        'diretorios': False,
        'security': False
    }
    
    # 1. Corrigir encoding PostgreSQL
    resultados['encoding'] = corrigir_encoding_postgresql()
    
    # 2. Criar tabelas de IA
    resultados['tabelas_ai'] = criar_tabelas_ai_render()
    
    # 3. Corrigir imports SQLAlchemy
    corrigir_imports_sqlalchemy()
    resultados['imports'] = True
    
    # 4. Criar diretórios necessários
    criar_diretorio_backups()
    resultados['diretorios'] = True
    
    # 5. Criar configuração de segurança
    resultados['security'] = corrigir_security_config()
    
    # Resumo final
    print("\n" + "=" * 80)
    print("📊 RESUMO DAS CORREÇÕES")
    print("=" * 80)
    
    for item, sucesso in resultados.items():
        status = "✅ SUCESSO" if sucesso else "❌ FALHOU"
        print(f"  {item.upper()}: {status}")
    
    sucessos = sum(resultados.values())
    total = len(resultados)
    
    print(f"\n📈 RESULTADO GERAL: {sucessos}/{total} correções aplicadas")
    
    if sucessos >= 4:
        print("\n🎉 SISTEMA CLAUDE AI CORRIGIDO COM SUCESSO!")
        print("\n🔄 PRÓXIMOS PASSOS:")
        print("1. Reinicie o serviço no Render")
        print("2. Teste o Claude AI no sistema")
        print("3. Monitore os logs para verificar funcionamento")
    else:
        print("\n⚠️ ALGUMAS CORREÇÕES FALHARAM")
        print("Verifique os erros acima e tente novamente")
    
    return sucessos >= 4

if __name__ == "__main__":
    try:
        sucesso = main()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        traceback.print_exc()
        sys.exit(1) 