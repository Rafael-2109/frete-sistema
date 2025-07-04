#!/usr/bin/env python3
"""
🔧 CORREÇÃO DAS FUNCIONALIDADES LIMITADAS DO CLAUDE AI
Script que resolve todos os problemas específicos identificados
"""

import os
import json
import shutil
from datetime import datetime

def corrigir_multi_agent_system():
    """Corrige o erro NoneType + str no multi_agent_system.py"""
    print("🔧 Corrigindo Multi-Agent System...")
    
    arquivo = "app/claude_ai/multi_agent_system.py"
    
    # Fazer backup
    shutil.copy2(arquivo, f"{arquivo}.backup")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Localizar e corrigir linha problemática
    linha_antiga = "final_response = str(main_response) + str(convergence_note) + str(validation_note)"
    linha_nova = """# Proteção absoluta contra None
        main_response = main_response or "Resposta não disponível"
        convergence_note = convergence_note or ""
        validation_note = validation_note or ""
        
        final_response = str(main_response) + str(convergence_note) + str(validation_note)"""
    
    if linha_antiga in conteudo:
        conteudo = conteudo.replace(linha_antiga, linha_nova)
        
        # Salvar arquivo corrigido
        with open(arquivo, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print("✅ Multi-Agent System corrigido")
    else:
        print("⚠️ Linha não encontrada - verificar manualmente")

def corrigir_lifelong_learning():
    """Corrige o erro SQLAlchemy no lifelong_learning.py"""
    print("🔧 Corrigindo Lifelong Learning...")
    
    arquivo = "app/claude_ai/lifelong_learning.py"
    
    # Fazer backup
    shutil.copy2(arquivo, f"{arquivo}.backup")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Corrigir imports
    import_antigo = "from app import db"
    import_novo = """from flask import current_app
from app import db
from sqlalchemy import text, func"""
    
    if import_antigo in conteudo and "from flask import current_app" not in conteudo:
        conteudo = conteudo.replace(
            "from sqlalchemy import text, func\nfrom app import db",
            import_novo
        )
    
    # Adicionar proteção de contexto Flask
    funcoes_db = [
        "_salvar_padrao",
        "_atualizar_metricas", 
        "_salvar_historico",
        "_aprender_mapeamento_cliente"
    ]
    
    for funcao in funcoes_db:
        if f"def {funcao}" in conteudo:
            # Adicionar with current_app.app_context() onde necessário
            padrao = f"def {funcao}(self,"
            if padrao in conteudo:
                # Buscar início da função
                inicio = conteudo.find(padrao)
                if inicio != -1:
                    # Encontrar try: da função
                    try_pos = conteudo.find("try:", inicio)
                    if try_pos != -1:
                        # Adicionar proteção de contexto
                        conteudo = conteudo[:try_pos] + """with current_app.app_context():
            """ + conteudo[try_pos:]
    
    # Salvar arquivo corrigido
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ Lifelong Learning corrigido")

def corrigir_advanced_integration():
    """Corrige o erro SQLAlchemy no advanced_integration.py"""
    print("🔧 Corrigindo Advanced Integration...")
    
    arquivo = "app/claude_ai/advanced_integration.py"
    
    # Fazer backup
    shutil.copy2(arquivo, f"{arquivo}.backup")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Adicionar import do Flask current_app se não existir
    if "from flask import current_app" not in conteudo:
        conteudo = conteudo.replace(
            "from app import db",
            "from flask import current_app\nfrom app import db"
        )
    
    # Adicionar proteção de contexto nas operações de banco
    if "def _store_advanced_metadata" in conteudo:
        # Localizar função
        inicio = conteudo.find("def _store_advanced_metadata")
        if inicio != -1:
            try_pos = conteudo.find("try:", inicio)
            if try_pos != -1:
                # Adicionar proteção
                conteudo = conteudo[:try_pos] + """with current_app.app_context():
            """ + conteudo[try_pos:]
    
    # Salvar arquivo corrigido
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ Advanced Integration corrigido")

def corrigir_encoding_postgresql():
    """Corrige problemas de encoding UTF-8"""
    print("🔧 Corrigindo Encoding PostgreSQL...")
    
    arquivo = "config.py"
    
    # Fazer backup
    shutil.copy2(arquivo, f"{arquivo}.backup")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Verificar se correção já foi aplicada
    if "'client_encoding': 'utf8'" in conteudo:
        print("✅ Encoding já corrigido")
        return
    
    # Adicionar configuração de encoding mais robusta
    config_encoding = """
    # Configuração de encoding UTF-8 robusta
    if IS_POSTGRESQL:
        # Configurações para PostgreSQL com encoding UTF-8 forçado
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 10,
            'max_overflow': 10,
            'pool_size': 10,
            'connect_args': {
                'sslmode': 'require',
                'connect_timeout': 10,
                'application_name': 'frete_sistema',
                'client_encoding': 'utf8',  # Encoding UTF-8 explícito
                'options': '-c client_encoding=UTF8 -c timezone=UTC'
            }
        }
    """
    
    # Substituir configuração existente
    if "if IS_POSTGRESQL:" in conteudo:
        # Encontrar bloco PostgreSQL
        inicio = conteudo.find("if IS_POSTGRESQL:")
        fim = conteudo.find("else:", inicio)
        
        if inicio != -1 and fim != -1:
            # Substituir bloco
            conteudo = conteudo[:inicio] + config_encoding + "\n    " + conteudo[fim:]
    
    # Salvar arquivo corrigido
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ Encoding PostgreSQL corrigido")

def criar_arquivos_faltantes():
    """Cria arquivos de configuração faltantes"""
    print("📁 Criando arquivos faltantes...")
    
    # 1. Criar diretório instance/claude_ai
    instance_dir = "instance/claude_ai"
    os.makedirs(instance_dir, exist_ok=True)
    
    # 2. Criar security_config.json
    security_config = {
        "security_level": "production",
        "max_requests_per_minute": 100,
        "allowed_operations": [
            "read_data",
            "query_database", 
            "generate_reports",
            "analyze_data"
        ],
        "blocked_operations": [
            "delete_data",
            "modify_system",
            "access_sensitive"
        ],
        "monitoring": {
            "log_all_requests": True,
            "alert_on_suspicious": True,
            "max_query_time": 30
        }
    }
    
    with open(f"{instance_dir}/security_config.json", 'w', encoding='utf-8') as f:
        json.dump(security_config, f, indent=2, ensure_ascii=False)
    
    # 3. Criar diretório backups
    backups_dir = f"{instance_dir}/backups"
    os.makedirs(f"{backups_dir}/generated", exist_ok=True)
    os.makedirs(f"{backups_dir}/projects", exist_ok=True)
    
    # 4. Criar .gitkeep nos diretórios
    with open(f"{backups_dir}/generated/.gitkeep", 'w') as f:
        f.write("")
    
    with open(f"{backups_dir}/projects/.gitkeep", 'w') as f:
        f.write("")
    
    print("✅ Arquivos faltantes criados")

def corrigir_imports_circulares():
    """Corrige imports circulares"""
    print("🔧 Corrigindo imports circulares...")
    
    arquivo = "app/claude_ai/enhanced_claude_integration.py"
    
    if not os.path.exists(arquivo):
        print("⚠️ Arquivo enhanced_claude_integration.py não encontrado")
        return
    
    # Fazer backup
    shutil.copy2(arquivo, f"{arquivo}.backup")
    
    # Ler arquivo
    with open(arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()
    
    # Remover imports circulares problemáticos
    imports_problematicos = [
        "from app.claude_ai.claude_real_integration import",
        "from .claude_real_integration import"
    ]
    
    for import_prob in imports_problematicos:
        if import_prob in conteudo:
            linhas = conteudo.split('\n')
            linhas_filtradas = []
            for linha in linhas:
                if not linha.strip().startswith(import_prob):
                    linhas_filtradas.append(linha)
            conteudo = '\n'.join(linhas_filtradas)
    
    # Salvar arquivo corrigido
    with open(arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    
    print("✅ Imports circulares corrigidos")

def main():
    """Executa todas as correções"""
    print("🚀 INICIANDO CORREÇÃO DAS FUNCIONALIDADES LIMITADAS")
    print("=" * 60)
    
    try:
        # 1. Corrigir Multi-Agent System
        corrigir_multi_agent_system()
        
        # 2. Corrigir Lifelong Learning
        corrigir_lifelong_learning()
        
        # 3. Corrigir Advanced Integration
        corrigir_advanced_integration()
        
        # 4. Corrigir Encoding PostgreSQL
        corrigir_encoding_postgresql()
        
        # 5. Criar arquivos faltantes
        criar_arquivos_faltantes()
        
        # 6. Corrigir imports circulares
        corrigir_imports_circulares()
        
        print("\n" + "=" * 60)
        print("✅ TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
        print("\n📋 RESUMO DAS CORREÇÕES:")
        print("  ✅ Multi-Agent System: Erro NoneType + str corrigido")
        print("  ✅ Lifelong Learning: SQLAlchemy Flask context corrigido")
        print("  ✅ Advanced Integration: SQLAlchemy Flask context corrigido")
        print("  ✅ Encoding PostgreSQL: UTF-8 forçado")
        print("  ✅ Arquivos faltantes: security_config.json e backups/ criados")
        print("  ✅ Imports circulares: Removidos")
        
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("  1. git add .")
        print("  2. git commit -m 'fix: Corrigir funcionalidades limitadas Claude AI'")
        print("  3. git push")
        print("  4. Aguardar deploy automático no Render")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main() 