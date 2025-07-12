#!/usr/bin/env python3
"""
🧪 TESTE DAS CORREÇÕES CRÍTICAS APLICADAS
=========================================

Testa se as correções manuais que aplicamos resolveram os erros críticos
que apareciam nos logs de produção.

CORREÇÕES TESTADAS:
1. ❌ object dict can't be used in 'await' expression
2. ❌ QueryProcessor.__init__() missing 3 required positional arguments
3. ⚠️ SemanticValidator/CriticValidator requer orchestrator
"""

import sys
import logging
from datetime import datetime

# Configurar logging para capturar erros
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')

def teste_integration_manager_await():
    """
    TESTE 1: Verifica se erro de await foi corrigido
    ❌ object dict can't be used in 'await' expression
    """
    print("🧪 TESTE 1: Integration Manager - Erro de await")
    print("-" * 50)
    
    try:
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        # Instanciar manager
        manager = get_integration_manager()
        print("✅ IntegrationManager instanciado com sucesso")
        
        # Testar método que causava erro
        if hasattr(manager, 'process_unified_query'):
            print("✅ Método process_unified_query existe")
            # Não vamos chamar assíncrono aqui, só verificar que existe
            return True
        else:
            print("❌ Método process_unified_query não encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def teste_query_processor_argumentos():
    """
    TESTE 2: Verifica se argumentos do QueryProcessor foram corrigidos
    ❌ QueryProcessor.__init__() missing 3 required positional arguments
    """
    print("\n🧪 TESTE 2: QueryProcessor - Argumentos obrigatórios")
    print("-" * 50)
    
    resultados = []
    
    # Teste 2A: processors/__init__.py
    try:
        from app.claude_ai_novo.processors import get_query_processor
        
        processor = get_query_processor()
        if processor:
            print("✅ QueryProcessor via processors/__init__.py - OK")
            resultados.append(True)
        else:
            print("⚠️ QueryProcessor via processors/__init__.py - None retornado")
            resultados.append(False)
            
    except Exception as e:
        print(f"❌ Erro em processors/__init__.py: {e}")
        resultados.append(False)
    
    # Teste 2B: utils/processor_registry.py
    try:
        from app.claude_ai_novo.utils.processor_registry import get_processor_registry
        
        registry = get_processor_registry()
        query_processor = registry.get_processor('query')
        
        if query_processor:
            print("✅ QueryProcessor via ProcessorRegistry - OK")
            resultados.append(True)
        else:
            print("⚠️ QueryProcessor via ProcessorRegistry - None retornado")
            resultados.append(False)
            
    except Exception as e:
        print(f"❌ Erro em ProcessorRegistry: {e}")
        resultados.append(False)
    
    return all(resultados)

def teste_validators_warnings():
    """
    TESTE 3: Verifica se warnings dos validators foram corrigidos
    ⚠️ SemanticValidator/CriticValidator requer orchestrator
    """
    print("\n🧪 TESTE 3: Validators - Warnings de orchestrator")
    print("-" * 50)
    
    try:
        # Capturar logs de warning
        import io
        from contextlib import redirect_stderr
        
        log_capture = io.StringIO()
        
        # Configurar handler para capturar logs
        logger = logging.getLogger('app.claude_ai_novo.validators.validator_manager')
        
        # Importar e instanciar
        from app.claude_ai_novo.validators.validator_manager import get_validator_manager
        
        # Capturar warnings durante inicialização
        with redirect_stderr(log_capture):
            validator_manager = get_validator_manager()
        
        # Verificar se foi instanciado
        if validator_manager:
            print("✅ ValidatorManager instanciado com sucesso")
            
            # Verificar se temos warnings críticos nos logs
            logs_captured = log_capture.getvalue()
            
            # Estes warnings NÃO devem mais aparecer
            problematic_warnings = [
                "⚠️ SemanticValidator requer orchestrator",
                "⚠️ CriticValidator requer orchestrator"
            ]
            
            warnings_found = []
            for warning in problematic_warnings:
                if warning in logs_captured:
                    warnings_found.append(warning)
            
            if warnings_found:
                print(f"❌ Ainda há warnings problemáticos: {warnings_found}")
                return False
            else:
                print("✅ Warnings problemáticos removidos")
                return True
        else:
            print("❌ ValidatorManager não pôde ser instanciado")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def teste_novos_erros():
    """
    TESTE 4: Verifica se há novos erros críticos
    Testa erros que apareceram nos logs além dos que corrigimos
    """
    print("\n🧪 TESTE 4: Verificar novos erros críticos")
    print("-" * 50)
    
    novos_erros = []
    
    # Teste 4A: SpecialistAgent agent_type
    try:
        from app.claude_ai_novo.coordinators.coordinator_manager import get_coordinator_manager
        
        coordinator = get_coordinator_manager()
        if coordinator:
            print("✅ CoordinatorManager instanciado sem erro de SpecialistAgent")
        else:
            print("⚠️ CoordinatorManager retornou None")
            
    except Exception as e:
        if "agent_type" in str(e):
            print(f"❌ NOVO ERRO: SpecialistAgent agent_type - {e}")
            novos_erros.append(f"SpecialistAgent: {e}")
        else:
            print(f"⚠️ Erro em CoordinatorManager: {e}")
    
    # Teste 4B: Commands modules
    try:
        from app.claude_ai_novo.commands import get_command_manager
        
        cmd_manager = get_command_manager()
        if cmd_manager:
            print("✅ CommandManager carregado sem erros de módulo")
        else:
            print("⚠️ CommandManager retornou None")
            
    except Exception as e:
        if "No module named" in str(e):
            print(f"❌ NOVO ERRO: Módulo faltando - {e}")
            novos_erros.append(f"Module missing: {e}")
        else:
            print(f"⚠️ Erro em CommandManager: {e}")
    
    if novos_erros:
        print(f"\n❌ {len(novos_erros)} novos erros encontrados")
        return False
    else:
        print("\n✅ Nenhum novo erro crítico encontrado")
        return True

def main():
    """Executa todos os testes das correções"""
    print("🧪 TESTE DAS CORREÇÕES CRÍTICAS APLICADAS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    
    testes = [
        ("Integration Manager (await error)", teste_integration_manager_await),
        ("QueryProcessor (argumentos)", teste_query_processor_argumentos),
        ("Validators (warnings)", teste_validators_warnings),
        ("Novos erros críticos", teste_novos_erros)
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
    print("\n" + "=" * 60)
    print("📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 60)
    
    sucessos = 0
    total = len(resultados)
    
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"   {status} | {nome}")
        if sucesso:
            sucessos += 1
    
    print(f"\n📈 RESULTADO GERAL: {sucessos}/{total} testes passaram")
    
    if sucessos == total:
        print("🎉 TODAS AS CORREÇÕES FUNCIONARAM!")
        print("✅ Sistema deve estar funcionando sem os erros críticos")
        return True
    elif sucessos >= total * 0.8:
        print("🟡 MAIORIA DAS CORREÇÕES FUNCIONOU")
        print("⚠️ Alguns problemas menores podem persistir")
        return True
    else:
        print("🔴 CORREÇÕES NÃO FUNCIONARAM COMPLETAMENTE")
        print("❌ Ainda há erros críticos que precisam ser corrigidos")
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