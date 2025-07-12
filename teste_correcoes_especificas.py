#!/usr/bin/env python3
"""
🧪 TESTE DAS CORREÇÕES ESPECÍFICAS
==================================

Testa as correções específicas dos novos erros identificados:
1. SpecialistAgent agent_type
2. Commands modules (base, excel_orchestrator)
"""

import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

def teste_specialist_agent_corrigido():
    """
    TESTE 1: Verifica se SpecialistAgent foi corrigido
    ❌ SpecialistAgent.__new__() missing 1 required positional argument: 'agent_type'
    """
    print("🧪 TESTE 1: SpecialistAgent - Argumento agent_type")
    print("-" * 50)
    
    try:
        from app.claude_ai_novo.coordinators.coordinator_manager import get_coordinator_manager
        
        # Instanciar coordinator manager
        coordinator = get_coordinator_manager()
        
        if coordinator:
            print("✅ CoordinatorManager instanciado com sucesso")
            
            # Verificar se specialist está carregado
            if 'specialist' in coordinator.coordinators:
                print("✅ SpecialistAgent carregado sem erro de agent_type")
                return True
            else:
                print("⚠️ SpecialistAgent não está no coordinator")
                return False
        else:
            print("❌ CoordinatorManager falhou ao instanciar")
            return False
            
    except Exception as e:
        if "agent_type" in str(e):
            print(f"❌ ERRO AINDA PRESENTE: SpecialistAgent agent_type - {e}")
            return False
        else:
            print(f"⚠️ Outro erro em CoordinatorManager: {e}")
            return False

def teste_commands_modules_corrigidos():
    """
    TESTE 2: Verifica se modules commands foram corrigidos
    ❌ No module named 'app.claude_ai_novo.commands.base'
    ❌ No module named 'app.claude_ai_novo.commands.excel_orchestrator'
    """
    print("\n🧪 TESTE 2: Commands Modules - Nomes corretos")
    print("-" * 50)
    
    resultados = []
    
    # Teste 2A: Commands manager geral
    try:
        from app.claude_ai_novo.commands import get_command_manager
        
        cmd_manager = get_command_manager()
        if cmd_manager:
            print("✅ CommandManager carregado sem erros de módulo")
            resultados.append(True)
        else:
            print("⚠️ CommandManager retornou None")
            resultados.append(False)
            
    except Exception as e:
        if "No module named" in str(e):
            print(f"❌ ERRO DE MÓDULO AINDA PRESENTE: {e}")
            resultados.append(False)
        else:
            print(f"⚠️ Outro erro em CommandManager: {e}")
            resultados.append(False)
    
    # Teste 2B: Commands status
    try:
        from app.claude_ai_novo.commands import get_commands_status
        
        status = get_commands_status()
        print(f"✅ Status de commands obtido: {len(status)} módulos verificados")
        
        # Verificar se não há mais erros de módulos não encontrados
        working_modules = sum(1 for working in status.values() if working)
        total_modules = len(status)
        
        print(f"📊 Módulos funcionando: {working_modules}/{total_modules}")
        
        if working_modules >= total_modules * 0.8:  # 80% ou mais funcionando
            resultados.append(True)
        else:
            print("⚠️ Muitos módulos não funcionando")
            resultados.append(False)
            
    except Exception as e:
        print(f"❌ Erro ao obter status de commands: {e}")
        resultados.append(False)
    
    return all(resultados)

def teste_auto_discovery():
    """
    TESTE 3: Verifica se auto-discovery não gera mais warnings
    """
    print("\n🧪 TESTE 3: Commands Auto-Discovery - Sem warnings")
    print("-" * 50)
    
    try:
        # Capturar warnings durante auto-discovery
        import io
        from contextlib import redirect_stderr
        
        log_capture = io.StringIO()
        
        # Forçar re-discovery
        from app.claude_ai_novo.commands import reset_commands_cache
        
        with redirect_stderr(log_capture):
            reset_commands_cache()
        
        # Verificar warnings capturados
        logs_captured = log_capture.getvalue()
        
        # Estes warnings NÃO devem mais aparecer
        problematic_warnings = [
            "No module named 'app.claude_ai_novo.commands.base'",
            "No module named 'app.claude_ai_novo.commands.excel_orchestrator'"
        ]
        
        warnings_found = []
        for warning in problematic_warnings:
            if warning in logs_captured:
                warnings_found.append(warning)
        
        if warnings_found:
            print(f"❌ Warnings ainda presentes: {warnings_found}")
            return False
        else:
            print("✅ Auto-discovery executado sem warnings problemáticos")
            return True
            
    except Exception as e:
        print(f"❌ Erro no teste de auto-discovery: {e}")
        return False

def main():
    """Executa todos os testes das correções específicas"""
    print("🧪 TESTE DAS CORREÇÕES ESPECÍFICAS")
    print("=" * 55)
    print(f"Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 55)
    
    testes = [
        ("SpecialistAgent agent_type", teste_specialist_agent_corrigido),
        ("Commands modules", teste_commands_modules_corrigidos),
        ("Auto-discovery warnings", teste_auto_discovery)
    ]
    
    resultados = []
    
    for nome, teste_func in testes:
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"\n❌ Erro crítico no teste '{nome}': {e}")
            resultados.append((nome, False))
    
    # Relatório final
    print("\n" + "=" * 55)
    print("📊 RELATÓRIO FINAL DOS TESTES ESPECÍFICOS")
    print("=" * 55)
    
    sucessos = 0
    total = len(resultados)
    
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"   {status} | {nome}")
        if sucesso:
            sucessos += 1
    
    print(f"\n📈 RESULTADO GERAL: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODAS AS CORREÇÕES ESPECÍFICAS FUNCIONARAM!")
        print("✅ Erros de SpecialistAgent e Commands modules corrigidos")
        return True
    elif sucessos >= total * 0.7:
        print("🟡 MAIORIA DAS CORREÇÕES ESPECÍFICAS FUNCIONOU")
        print("⚠️ Alguns problemas específicos podem persistir")
        return True
    else:
        print("🔴 CORREÇÕES ESPECÍFICAS NÃO FUNCIONARAM")
        print("❌ Ainda há erros específicos que precisam ser corrigidos")
        return False

if __name__ == "__main__":
    try:
        sucesso = main()
        sys.exit(0 if sucesso else 1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 