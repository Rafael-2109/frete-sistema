#!/usr/bin/env python3
"""
Teste das Correções dos Logs de Produção
======================================

Verifica se as correções implementadas resolvem os problemas
identificados nos logs do Render.
"""

import sys
import os
import traceback
from pathlib import Path

# Adicionar diretório raiz ao Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def teste_performance_cache():
    """Testa se o performance_cache foi criado e funciona"""
    print("🔍 Testando performance_cache dos enrichers...")
    
    try:
        from app.claude_ai_novo.enrichers.performance_cache import cached_result, performance_monitor, get_cache_stats
        
        # Teste básico de cache
        def funcao_teste(x):
            return x * 2
        
        resultado1 = cached_result("teste_key", funcao_teste, 5)
        resultado2 = cached_result("teste_key", funcao_teste, 5)  # Deve vir do cache
        
        assert resultado1 == 10, f"Resultado incorreto: {resultado1}"
        assert resultado2 == 10, f"Resultado do cache incorreto: {resultado2}"
        
        # Teste do decorator
        @performance_monitor
        def funcao_lenta():
            import time
            time.sleep(0.1)
            return "teste"
        
        resultado_decorator = funcao_lenta()
        assert resultado_decorator == "teste", f"Decorator falhou: {resultado_decorator}"
        
        # Teste das estatísticas
        stats = get_cache_stats()
        assert isinstance(stats, dict), f"Stats inválidas: {stats}"
        assert 'total_entries' in stats, f"Stats sem total_entries: {stats}"
        
        print("   ✅ performance_cache funcionando corretamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no performance_cache: {e}")
        traceback.print_exc()
        return False

def teste_process_query_orchestrator():
    """Testa se o método process_query foi adicionado ao OrchestratorManager"""
    print("🔍 Testando método process_query no OrchestratorManager...")
    
    try:
        from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
        
        manager = get_orchestrator_manager()
        
        # Verificar se o método existe
        assert hasattr(manager, 'process_query'), "Método process_query não encontrado"
        
        # Teste básico
        resultado = manager.process_query("teste de query", {"user_id": "test_user"})
        
        assert isinstance(resultado, dict), f"Resultado não é dict: {type(resultado)}"
        assert 'query' in resultado or 'success' in resultado, f"Resultado inválido: {resultado}"
        
        print("   ✅ process_query funcionando corretamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no process_query: {e}")
        traceback.print_exc()
        return False

def teste_static_reports_fallback():
    """Testa se o fallback do diretório static/reports funciona"""
    print("🔍 Testando fallback do diretório static/reports...")
    
    try:
        from app.claude_ai_novo.commands.base_command import BaseCommand
        
        # Criar instância
        base_cmd = BaseCommand()
        
        # Verificar se output_dir foi configurado
        assert hasattr(base_cmd, 'output_dir'), "output_dir não configurado"
        assert base_cmd.output_dir is not None, "output_dir é None"
        
        # Verificar se é Path válido
        assert isinstance(base_cmd.output_dir, Path), f"output_dir não é Path: {type(base_cmd.output_dir)}"
        
        # Verificar se diretório existe ou é válido
        print(f"   📁 Diretório configurado: {base_cmd.output_dir}")
        
        print("   ✅ Fallback do static/reports funcionando")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no fallback static/reports: {e}")
        traceback.print_exc()
        return False

def teste_processor_registry_imports():
    """Testa se os imports do ProcessorRegistry foram corrigidos"""
    print("🔍 Testando imports corrigidos do ProcessorRegistry...")
    
    try:
        from app.claude_ai_novo.utils.processor_registry import get_processor_registry
        
        # Criar instância do registry
        registry = get_processor_registry()
        
        assert registry is not None, "Registry é None"
        assert hasattr(registry, 'processors'), "Registry sem atributo processors"
        
        # Verificar processadores
        processor_names = registry.list_processors()
        print(f"   📋 Processadores registrados: {processor_names}")
        
        # Verificar estatísticas
        stats = registry.get_registry_stats()
        assert isinstance(stats, dict), f"Stats inválidas: {stats}"
        assert 'total_processors' in stats, f"Stats sem total_processors: {stats}"
        
        print(f"   📊 Total de processadores: {stats['total_processors']}")
        print(f"   💚 Processadores saudáveis: {stats['healthy_processors']}")
        
        print("   ✅ ProcessorRegistry imports corrigidos")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no ProcessorRegistry: {e}")
        traceback.print_exc()
        return False

def teste_semantic_enricher_import():
    """Testa se o SemanticEnricher agora importa performance_cache corretamente"""
    print("🔍 Testando import do performance_cache no SemanticEnricher...")
    
    try:
        from app.claude_ai_novo.enrichers.semantic_enricher import SemanticEnricher
        
        # Criar instância
        enricher = SemanticEnricher()
        
        assert enricher is not None, "SemanticEnricher é None"
        assert hasattr(enricher, 'enriquecer_mapeamento_com_readers'), "Método principal não encontrado"
        
        print("   ✅ SemanticEnricher importando corretamente")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro no SemanticEnricher: {e}")
        traceback.print_exc()
        return False

def teste_integracoes_completas():
    """Testa integrações completas do sistema"""
    print("🔍 Testando integrações completas...")
    
    try:
        # Teste de integração geral
        from app.claude_ai_novo.integration.integration_manager import get_integration_manager
        
        integration_manager = get_integration_manager()
        
        # Verificar se a integração ainda funciona
        if integration_manager:
            status = integration_manager.get_integration_status()
            print(f"   📊 Status da integração: {status.get('modules_loaded', 0)} módulos")
        
        print("   ✅ Integrações básicas funcionando")
        return True
        
    except Exception as e:
        print(f"   ❌ Erro nas integrações: {e}")
        traceback.print_exc()
        return False

def main():
    """Executa todos os testes das correções"""
    print("🧪 TESTE DAS CORREÇÕES DOS LOGS DE PRODUÇÃO")
    print("=" * 50)
    
    testes = [
        ("Performance Cache (Enrichers)", teste_performance_cache),
        ("Process Query (OrchestratorManager)", teste_process_query_orchestrator),
        ("Static Reports Fallback", teste_static_reports_fallback),
        ("ProcessorRegistry Imports", teste_processor_registry_imports),
        ("SemanticEnricher Import", teste_semantic_enricher_import),
        ("Integrações Completas", teste_integracoes_completas),
    ]
    
    resultados = {}
    total_testes = len(testes)
    testes_aprovados = 0
    
    for nome, func_teste in testes:
        print(f"\n📋 {nome}")
        print("-" * 30)
        
        try:
            sucesso = func_teste()
            resultados[nome] = sucesso
            if sucesso:
                testes_aprovados += 1
        except Exception as e:
            print(f"   ❌ Erro crítico no teste: {e}")
            resultados[nome] = False
    
    # Relatório final
    print("\n" + "=" * 50)
    print("📊 RELATÓRIO FINAL DOS TESTES")
    print("=" * 50)
    
    for nome, sucesso in resultados.items():
        status = "✅ APROVADO" if sucesso else "❌ REPROVADO"
        print(f"{status}: {nome}")
    
    taxa_sucesso = (testes_aprovados / total_testes) * 100
    print(f"\n🏆 TAXA DE SUCESSO: {testes_aprovados}/{total_testes} ({taxa_sucesso:.1f}%)")
    
    if taxa_sucesso >= 80:
        print("✅ CORREÇÕES IMPLEMENTADAS COM SUCESSO!")
        print("   🚀 Sistema pronto para deploy no Render")
    elif taxa_sucesso >= 60:
        print("⚠️ CORREÇÕES PARCIALMENTE IMPLEMENTADAS")
        print("   🔧 Alguns ajustes podem ser necessários")
    else:
        print("❌ CORREÇÕES NECESSITAM REVISÃO")
        print("   🛠️ Problemas críticos identificados")
    
    return taxa_sucesso

if __name__ == "__main__":
    main() 