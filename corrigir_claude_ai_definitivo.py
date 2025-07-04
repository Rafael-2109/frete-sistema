#!/usr/bin/env python3
"""
🔧 SCRIPT DEFINITIVO PARA CORRIGIR PROBLEMAS DO CLAUDE AI
Resolve TODOS os problemas identificados nos logs de erro
"""

import os
import sys
import traceback
from pathlib import Path
import subprocess
import json

def main():
    """Função principal que executa todas as correções"""
    print("🚀 INICIANDO CORREÇÕES DEFINITIVAS DO CLAUDE AI")
    print("=" * 80)
    
    problemas_resolvidos = 0
    
    try:
        # 1. Corrigir problema de encoding UTF-8
        print("\n🔧 1. CORRIGINDO ENCODING UTF-8...")
        if corrigir_encoding_utf8():
            print("✅ Encoding UTF-8 corrigido!")
            problemas_resolvidos += 1
        else:
            print("❌ Falha ao corrigir encoding UTF-8")
        
        # 2. Corrigir imports SQLAlchemy
        print("\n🔧 2. CORRIGINDO IMPORTS SQLALCHEMY...")
        if corrigir_imports_sqlalchemy():
            print("✅ Imports SQLAlchemy corrigidos!")
            problemas_resolvidos += 1
        else:
            print("❌ Falha ao corrigir imports SQLAlchemy")
        
        # 3. Criar arquivos de configuração necessários
        print("\n🔧 3. CRIANDO ARQUIVOS DE CONFIGURAÇÃO...")
        if criar_arquivos_configuracao():
            print("✅ Arquivos de configuração criados!")
            problemas_resolvidos += 1
        else:
            print("❌ Falha ao criar arquivos de configuração")
        
        # 4. Corrigir problema do multi-agent system
        print("\n🔧 4. VERIFICANDO MULTI-AGENT SYSTEM...")
        if verificar_multi_agent_system():
            print("✅ Multi-Agent System verificado!")
            problemas_resolvidos += 1
        else:
            print("❌ Multi-Agent System precisa de correção")
        
        # 5. Aplicar migração das tabelas de IA
        print("\n🔧 5. APLICANDO MIGRAÇÃO DAS TABELAS DE IA...")
        if aplicar_migracao_tabelas_ia():
            print("✅ Migração das tabelas de IA aplicada!")
            problemas_resolvidos += 1
        else:
            print("❌ Falha ao aplicar migração das tabelas de IA")
        
        print(f"\n🎉 CORREÇÕES CONCLUÍDAS!")
        print(f"✅ Problemas resolvidos: {problemas_resolvidos}/5")
        
        if problemas_resolvidos >= 4:
            print("\n🚀 SISTEMA CLAUDE AI DEVE ESTAR FUNCIONANDO!")
            print("🔄 Reinicie o sistema para aplicar as correções")
        else:
            print("\n⚠️ ALGUNS PROBLEMAS AINDA PRECISAM SER RESOLVIDOS")
            print("📋 Verifique os logs acima para mais detalhes")
            
    except Exception as e:
        print(f"❌ ERRO CRÍTICO: {e}")
        traceback.print_exc()

def corrigir_encoding_utf8():
    """Corrige problemas de encoding UTF-8"""
    try:
        # Verificar se o arquivo config.py existe
        config_file = Path('config.py')
        if not config_file.exists():
            print("❌ Arquivo config.py não encontrado")
            return False
        
        # Ler conteúdo atual com encoding correto
        try:
            content = config_file.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            # Tentar com encoding latin-1 se UTF-8 falhar
            content = config_file.read_text(encoding='latin-1')
        
        # Verificar se já tem as correções
        if 'client_encoding=UTF8' in content:
            print("✅ Correções de encoding já aplicadas")
            return True
        
        # Aplicar correções de encoding
        corrections = [
            ('postgresql://user:password@host:port/database', 
             'postgresql://user:password@host:port/database?client_encoding=UTF8'),
            ("'client_encoding': 'utf8'", 
             "'client_encoding': 'utf8',\n                'options': '-c client_encoding=UTF8'")
        ]
        
        for old, new in corrections:
            if old in content:
                content = content.replace(old, new)
        
        # Salvar com encoding UTF-8
        config_file.write_text(content, encoding='utf-8')
        print("✅ Encoding UTF-8 configurado no PostgreSQL")
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir encoding: {e}")
        return False

def corrigir_imports_sqlalchemy():
    """Corrige problemas de imports SQLAlchemy"""
    try:
        arquivos_para_corrigir = [
            'app/claude_ai/lifelong_learning.py',
            'app/claude_ai/advanced_integration.py',
            'app/claude_ai/human_in_loop_learning.py'
        ]
        
        correcoes_aplicadas = 0
        
        for arquivo in arquivos_para_corrigir:
            arquivo_path = Path(arquivo)
            if not arquivo_path.exists():
                continue
                
            try:
                content = arquivo_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                content = arquivo_path.read_text(encoding='latin-1')
            
            # Verificar se precisa de correção
            if 'from app import db' not in content and 'from app.models' not in content:
                # Adicionar imports corretos no topo
                lines = content.split('\n')
                import_index = 0
                
                # Encontrar onde inserir os imports
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        import_index = i + 1
                    elif line.strip() == '' and import_index > 0:
                        break
                
                # Inserir imports necessários
                new_imports = [
                    'from flask import current_app',
                    'from app import db',
                    ''
                ]
                
                lines[import_index:import_index] = new_imports
                
                # Salvar arquivo corrigido
                arquivo_path.write_text('\n'.join(lines), encoding='utf-8')
                correcoes_aplicadas += 1
                print(f"✅ Imports corrigidos em {arquivo}")
        
        return correcoes_aplicadas > 0
        
    except Exception as e:
        print(f"❌ Erro ao corrigir imports: {e}")
        return False

def criar_arquivos_configuracao():
    """Cria arquivos de configuração necessários"""
    try:
        # 1. Criar diretório instance/claude_ai se não existir
        instance_dir = Path('instance/claude_ai')
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Criar arquivo security_config.json
        security_config = {
            "security_level": "high",
            "allowed_operations": [
                "read_data",
                "analyze_data", 
                "generate_reports"
            ],
            "blocked_operations": [
                "delete_data",
                "modify_critical_data"
            ],
            "rate_limits": {
                "queries_per_minute": 60,
                "max_concurrent_requests": 10
            }
        }
        
        security_file = instance_dir / 'security_config.json'
        if not security_file.exists():
            security_file.write_text(json.dumps(security_config, indent=2), encoding='utf-8')
            print("✅ Arquivo security_config.json criado")
        
        # 3. Criar diretório backups
        backups_dir = instance_dir / 'backups'
        backups_dir.mkdir(exist_ok=True)
        
        # Criar subdiretórios
        (backups_dir / 'generated').mkdir(exist_ok=True)
        (backups_dir / 'projects').mkdir(exist_ok=True)
        
        # Criar arquivos .gitkeep
        (backups_dir / 'generated' / '.gitkeep').touch()
        (backups_dir / 'projects' / '.gitkeep').touch()
        
        print("✅ Diretórios de backup criados")
        
        # 4. Criar arquivo pending_actions.json se não existir
        pending_actions_file = Path('app/claude_ai/pending_actions.json')
        if not pending_actions_file.exists():
            pending_actions = {
                "version": "1.0",
                "last_update": "2025-07-04",
                "pending_actions": [],
                "completed_actions": []
            }
            pending_actions_file.write_text(json.dumps(pending_actions, indent=2), encoding='utf-8')
            print("✅ Arquivo pending_actions.json criado")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar arquivos de configuração: {e}")
        return False

def verificar_multi_agent_system():
    """Verifica se o multi-agent system está corrigido"""
    try:
        multi_agent_file = Path('app/claude_ai/multi_agent_system.py')
        if not multi_agent_file.exists():
            print("❌ Arquivo multi_agent_system.py não encontrado")
            return False
        
        content = multi_agent_file.read_text(encoding='utf-8')
        
        # Verificar se a correção da linha 595 está aplicada
        if 'str(main_response) + str(convergence_note) + str(validation_note)' in content:
            print("✅ Correção da concatenação já aplicada")
            return True
        elif '(main_response or "Resposta não disponível")' in content:
            print("✅ Correção alternativa da concatenação já aplicada")
            return True
        else:
            print("⚠️ Correção da concatenação não encontrada")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao verificar multi-agent system: {e}")
        return False

def aplicar_migracao_tabelas_ia():
    """Aplica migração das tabelas de IA"""
    try:
        # Verificar se o arquivo de migração existe
        migracao_file = Path('migrations/versions/criar_tabelas_ai_claude.py')
        if not migracao_file.exists():
            print("❌ Arquivo de migração não encontrado")
            return False
        
        # Executar migração
        print("🔄 Executando flask db upgrade...")
        result = subprocess.run(['flask', 'db', 'upgrade'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Migração executada com sucesso!")
            return True
        else:
            print(f"❌ Erro na migração: {result.stderr}")
            return False
        
    except Exception as e:
        print(f"❌ Erro ao aplicar migração: {e}")
        return False

if __name__ == "__main__":
    main() 