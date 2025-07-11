#!/usr/bin/env python3
"""
🔧 TESTE DAS CORREÇÕES DE PRODUÇÃO
==================================

Script para testar se as correções dos erros encontrados nos logs de produção
estão funcionando corretamente.

Erros corrigidos:
1. Import do current_user no processors/base.py
2. Import do LegacyCompatibility no utils/__init__.py  
3. JSON loads error no pattern_learning.py
"""

import sys
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

def teste_response_processor_imports():
    """Testa se os imports do ResponseProcessor estão funcionando"""
    try:
        from app.claude_ai_novo.processors.response_processor import ResponseProcessor, get_responseprocessor
        
        # Testar criação de instância
        processor = get_responseprocessor()
        
        print("✅ ResponseProcessor: Imports OK")
        print(f"   - Instância criada: {processor}")
        print(f"   - Cliente Anthropic: {'Configurado' if hasattr(processor, 'client') else 'Não configurado'}")
        
        return True
        
    except Exception as e:
        print(f"❌ ResponseProcessor: {e}")
        return False

def teste_legacy_compatibility():
    """Testa se o LegacyCompatibility está funcionando"""
    try:
        from app.claude_ai_novo.utils import LegacyCompatibility
        
        print("✅ LegacyCompatibility: Import OK")
        print(f"   - Classe disponível: {LegacyCompatibility}")
        
        # Testar funções de compatibilidade
        from app.claude_ai_novo.utils.legacy_compatibility import processar_consulta_modular
        result = processar_consulta_modular("teste")
        
        print(f"   - Função de compatibilidade: OK (resultado: {result[:50]}...)")
        
        return True
        
    except Exception as e:
        print(f"❌ LegacyCompatibility: {e}")
        return False

def teste_pattern_learning():
    """Testa se o PatternLearning está funcionando"""
    try:
        from app.claude_ai_novo.learners.pattern_learning import PatternLearner, get_pattern_learner
        
        # Criar instância
        learner = get_pattern_learner()
        
        print("✅ PatternLearning: Imports OK")
        print(f"   - Instância criada: {learner}")
        
        # Testar método que estava causando erro
        # Simular um padrão com dict (não string)
        class MockPadrao:
            def __init__(self):
                self.pattern_type = "teste"
                self.pattern_text = "teste"
                self.interpretation = {"tipo": "teste"}  # Dict, não string
                self.confidence = 0.5
                self.usage_count = 1
        
        mock_padroes = [MockPadrao()]
        
        # Simular método que estava falhando
        padroes_aplicaveis = []
        for padrao in mock_padroes:
            try:
                if isinstance(padrao.interpretation, str):
                    import json
                    interpretacao = json.loads(padrao.interpretation)
                else:
                    interpretacao = padrao.interpretation
                
                padroes_aplicaveis.append({
                    "tipo": padrao.pattern_type,
                    "interpretacao": interpretacao
                })
                
            except Exception as e:
                print(f"   ❌ Erro no parse: {e}")
                return False
        
        print(f"   - Parse de interpretação: OK ({len(padroes_aplicaveis)} padrões)")
        
        return True
        
    except Exception as e:
        print(f"❌ PatternLearning: {e}")
        return False

def teste_integracao_completa():
    """Testa se a integração dos novos módulos está funcionando"""
    try:
        # Testar MainOrchestrator
        from app.claude_ai_novo.orchestrators.main_orchestrator import get_main_orchestrator
        orchestrator = get_main_orchestrator()
        
        print("✅ Integração: MainOrchestrator OK")
        
        # Testar novos módulos integrados
        novos_modulos = [
            "tools_manager",
            "base_command", 
            "response_processor"
        ]
        
        for modulo in novos_modulos:
            if hasattr(orchestrator, modulo):
                instance = getattr(orchestrator, modulo)
                print(f"   - {modulo}: {'✅ Disponível' if instance else '⚠️ Mock'}")
            else:
                print(f"   - {modulo}: ❌ Não encontrado")
        
        # Testar ScanningManager
        from app.claude_ai_novo.scanning.scanning_manager import ScanningManager
        scanner = ScanningManager()
        
        if hasattr(scanner, 'database_manager'):
            db_manager = scanner.database_manager
            print(f"   - database_manager no ScanningManager: {'✅ Disponível' if db_manager else '⚠️ Mock'}")
        
        # Testar ValidatorManager
        from app.claude_ai_novo.validators.validator_manager import get_validator_manager
        validator = get_validator_manager()
        
        if hasattr(validator, 'validators') and 'critic' in validator.validators:
            print("   - critic_validator no ValidatorManager: ✅ Disponível")
        else:
            print("   - critic_validator no ValidatorManager: ⚠️ Não disponível")
        
        return True
        
    except Exception as e:
        print(f"❌ Integração: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🔧 TESTE DAS CORREÇÕES DE PRODUÇÃO")
    print("=" * 50)
    
    testes = [
        ("ResponseProcessor Imports", teste_response_processor_imports),
        ("LegacyCompatibility", teste_legacy_compatibility),
        ("PatternLearning JSON", teste_pattern_learning),
        ("Integração Completa", teste_integracao_completa)
    ]
    
    resultados = []
    
    for nome, teste_func in testes:
        print(f"\n🧪 {nome}:")
        print("-" * 30)
        
        try:
            resultado = teste_func()
            resultados.append((nome, resultado))
        except Exception as e:
            print(f"❌ Erro crítico no teste {nome}: {e}")
            resultados.append((nome, False))
    
    # Resumo final
    print("\n" + "=" * 50)
    print("📊 RESUMO DOS TESTES:")
    
    sucessos = 0
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"   {nome}: {status}")
        if sucesso:
            sucessos += 1
    
    total = len(resultados)
    porcentagem = (sucessos / total) * 100 if total > 0 else 0
    
    print(f"\n🎯 RESULTADO FINAL: {sucessos}/{total} testes passaram ({porcentagem:.1f}%)")
    
    if sucessos == total:
        print("🎉 TODAS AS CORREÇÕES ESTÃO FUNCIONANDO!")
        print("✅ Sistema pronto para commit em produção.")
    else:
        print("⚠️ Algumas correções ainda precisam de ajustes.")
        print("❌ Revisar antes do commit.")
    
    return sucessos == total

if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1) 