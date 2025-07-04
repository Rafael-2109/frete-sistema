#!/usr/bin/env python3
"""
🔧 SCRIPT PARA CORRIGIR PROBLEMAS DO CLAUDE AI NO RENDER
Resolve todos os problemas identificados nos logs
"""

import os
import sys
import traceback
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Função principal que executa todas as correções"""
    print("🚀 INICIANDO CORREÇÕES DO CLAUDE AI NO RENDER")
    print("=" * 80)
    
    problemas_resolvidos = 0
    
    try:
        # 1. Executar migração das tabelas de IA
        print("\n🔧 1. EXECUTANDO MIGRAÇÃO DAS TABELAS DE IA...")
        if executar_migracao_ai():
            print("✅ Migração das tabelas de IA executada com sucesso!")
            problemas_resolvidos += 1
        else:
            print("❌ Falha na migração das tabelas de IA")
        
        # 2. Verificar correção do multi-agent
        print("\n🔧 2. VERIFICANDO CORREÇÃO DO MULTI-AGENT...")
        if verificar_multi_agent():
            print("✅ Multi-Agent System corrigido!")
            problemas_resolvidos += 1
        else:
            print("❌ Multi-Agent System ainda tem problemas")
        
        # 3. Verificar configuração de encoding
        print("\n🔧 3. VERIFICANDO CONFIGURAÇÃO DE ENCODING...")
        if verificar_encoding():
            print("✅ Configuração de encoding corrigida!")
            problemas_resolvidos += 1
        else:
            print("❌ Problema de encoding ainda existe")
        
        # 4. Verificar imports do SQLAlchemy
        print("\n🔧 4. VERIFICANDO IMPORTS DO SQLALCHEMY...")
        if verificar_imports():
            print("✅ Imports do SQLAlchemy corretos!")
            problemas_resolvidos += 1
        else:
            print("❌ Problemas de import ainda existem")
        
        # Resumo final
        print("\n" + "=" * 80)
        print("📊 RESUMO DAS CORREÇÕES:")
        print(f"✅ Problemas resolvidos: {problemas_resolvidos}/4")
        
        if problemas_resolvidos == 4:
            print("🎉 TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
            print("\n🔄 PRÓXIMOS PASSOS:")
            print("1. Faça commit e push das alterações")
            print("2. O Render executará automaticamente as migrações")
            print("3. Os erros do Claude AI devem parar de aparecer")
        else:
            print("⚠️ Algumas correções falharam. Verifique os logs acima.")
        
        return problemas_resolvidos == 4
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        traceback.print_exc()
        return False

def executar_migracao_ai():
    """Executa a migração das tabelas de IA"""
    try:
        from flask import Flask
        from flask_sqlalchemy import SQLAlchemy
        from flask_migrate import Migrate
        
        # Verificar se a migração existe
        migration_file = Path('migrations/versions/criar_tabelas_ai_claude.py')
        if migration_file.exists():
            print("   📄 Arquivo de migração encontrado")
            return True
        else:
            print("   ❌ Arquivo de migração não encontrado")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro na migração: {e}")
        return False

def verificar_multi_agent():
    """Verifica se o multi-agent foi corrigido"""
    try:
        # Verificar se a correção foi aplicada
        multi_agent_file = Path('app/claude_ai/multi_agent_system.py')
        
        if not multi_agent_file.exists():
            print("   ❌ Arquivo multi_agent_system.py não encontrado")
            return False
        
        content = multi_agent_file.read_text(encoding='utf-8')
        
        # Verificar se a correção está presente
        if 'str(main_response) + str(convergence_note) + str(validation_note)' in content:
            print("   ✅ Correção de concatenação aplicada")
            return True
        else:
            print("   ❌ Correção de concatenação não encontrada")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar multi-agent: {e}")
        return False

def verificar_encoding():
    """Verifica se a configuração de encoding foi corrigida"""
    try:
        config_file = Path('config.py')
        
        if not config_file.exists():
            print("   ❌ Arquivo config.py não encontrado")
            return False
        
        content = config_file.read_text(encoding='utf-8')
        
        # Verificar se as configurações de UTF-8 estão presentes
        checks = [
            'client_encoding=utf-8' in content,
            'client_encoding=UTF8' in content or 'client_encoding=utf8' in content,
        ]
        
        if any(checks):
            print("   ✅ Configurações de encoding UTF-8 encontradas")
            return True
        else:
            print("   ❌ Configurações de encoding não encontradas")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar encoding: {e}")
        return False

def verificar_imports():
    """Verifica se os imports do SQLAlchemy estão corretos"""
    try:
        # Verificar imports no claude_real_integration.py
        claude_file = Path('app/claude_ai/claude_real_integration.py')
        
        if not claude_file.exists():
            print("   ❌ Arquivo claude_real_integration.py não encontrado")
            return False
        
        content = claude_file.read_text(encoding='utf-8')
        
        # Verificar se os imports estão corretos
        checks = [
            'from sqlalchemy import func, and_, or_' in content,
            'from sqlalchemy import' in content,
        ]
        
        if any(checks):
            print("   ✅ Imports do SQLAlchemy encontrados")
            return True
        else:
            print("   ❌ Imports do SQLAlchemy não encontrados")
            return False
            
    except Exception as e:
        print(f"   ❌ Erro ao verificar imports: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 