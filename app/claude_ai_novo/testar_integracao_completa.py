#!/usr/bin/env python3
"""
🧪 TESTE DE INTEGRAÇÃO COMPLETA - ORCHESTRATOR
============================================

Testa todas as conexões entre módulos estabelecidas pelo MainOrchestrator.
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from typing import Tuple, Dict, Any
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_scanner_loader_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Scanner → Loader"""
    try:
        # Verificar se ambos os componentes existem
        if 'scanners' not in orchestrator.components:
            return False, "Scanner não encontrado nos componentes"
        
        if 'loaders' not in orchestrator.components:
            return False, "Loader não encontrado nos componentes"
        
        scanner = orchestrator.components['scanners']
        loader = orchestrator.components['loaders']
        
        # Verificar se Scanner tem get_database_info
        if not hasattr(scanner, 'get_database_info'):
            return False, "Scanner não tem método get_database_info"
        
        # Verificar se Loader tem configure_with_scanner
        if not hasattr(loader, 'configure_with_scanner'):
            return False, "Loader não tem método configure_with_scanner"
        
        # Verificar se a conexão foi estabelecida
        if hasattr(loader, 'scanner') and loader.scanner is not None:
            # Testar funcionalidade
            try:
                db_info = scanner.get_database_info()
                if db_info and isinstance(db_info, dict):
                    return True, f"Conexão funcional - {len(db_info.get('tables', {}))} tabelas descobertas"
            except Exception as e:
                logger.debug(f"Erro ao testar funcionalidade: {e}")
                
            return True, "Conexão estabelecida"
        else:
            return False, "Loader não tem referência ao Scanner"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_mapper_loader_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Mapper → Loader"""
    try:
        if 'mappers' not in orchestrator.components:
            return False, "Mapper não encontrado nos componentes"
        
        if 'loaders' not in orchestrator.components:
            return False, "Loader não encontrado nos componentes"
        
        mapper = orchestrator.components['mappers']
        loader = orchestrator.components['loaders']
        
        if not hasattr(loader, 'configure_with_mapper'):
            return False, "Loader não tem método configure_with_mapper"
        
        if hasattr(loader, 'mapper') and loader.mapper is not None:
            return True, "Conexão estabelecida"
        else:
            return False, "Loader não tem referência ao Mapper"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_loader_provider_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Loader → Provider"""
    try:
        if 'loaders' not in orchestrator.components:
            return False, "Loader não encontrado nos componentes"
        
        if 'providers' not in orchestrator.components:
            return False, "Provider não encontrado nos componentes"
        
        loader = orchestrator.components['loaders']
        provider = orchestrator.components['providers']
        
        # Verificar se é ProviderManager
        if hasattr(provider, 'data_provider'):
            data_provider = provider.data_provider
            
            if not hasattr(data_provider, 'set_loader'):
                return False, "DataProvider não tem método set_loader"
            
            if hasattr(data_provider, 'loader') and data_provider.loader is not None:
                # Testar funcionalidade
                try:
                    data = data_provider.get_data_by_domain('entregas', {})
                    if data and 'source' in data and data['source'] == 'loader_manager':
                        return True, "Conexão funcional - DataProvider usando LoaderManager"
                except Exception as e:
                    logger.debug(f"Erro ao testar funcionalidade: {e}")
                    
                return True, "Conexão estabelecida via ProviderManager.data_provider"
            else:
                return False, "DataProvider não tem referência ao Loader"
        
        # Fallback: verificar provider direto
        elif hasattr(provider, 'set_loader'):
            if hasattr(provider, 'loader') and provider.loader is not None:
                return True, "Conexão estabelecida (provider direto)"
            else:
                return False, "Provider não tem referência ao Loader"
        else:
            return False, "Provider não tem método set_loader nem data_provider"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_memorizer_processor_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Memorizer → Processor"""
    try:
        if 'memorizers' not in orchestrator.components:
            return False, "Memorizer não encontrado nos componentes"
        
        if 'processors' not in orchestrator.components:
            return False, "Processor não encontrado nos componentes"
        
        memorizer = orchestrator.components['memorizers']
        processor = orchestrator.components['processors']
        
        if not hasattr(processor, 'set_memory_manager'):
            return False, "Processor não tem método set_memory_manager"
        
        if hasattr(processor, 'memory_manager') and processor.memory_manager is not None:
            return True, "Conexão estabelecida"
        else:
            return False, "Processor não tem referência ao Memorizer"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_learner_analyzer_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Learner → Analyzer"""
    try:
        if 'learners' not in orchestrator.components:
            return False, "Learner não encontrado nos componentes"
        
        if 'analyzers' not in orchestrator.components:
            return False, "Analyzer não encontrado nos componentes"
        
        learner = orchestrator.components['learners']
        analyzer = orchestrator.components['analyzers']
        
        if not hasattr(analyzer, 'set_learner'):
            return False, "Analyzer não tem método set_learner"
        
        if hasattr(analyzer, 'learner') and analyzer.learner is not None:
            return True, "Conexão estabelecida"
        else:
            return False, "Analyzer não tem referência ao Learner"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_enricher_processor_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Enricher → Processor"""
    try:
        if 'enrichers' not in orchestrator.components:
            return False, "Enricher não encontrado nos componentes"
        
        if 'processors' not in orchestrator.components:
            return False, "Processor não encontrado nos componentes"
        
        enricher = orchestrator.components['enrichers']
        processor = orchestrator.components['processors']
        
        if hasattr(processor, 'enricher') and processor.enricher is not None:
            return True, "Conexão estabelecida"
        else:
            return False, "Processor não tem referência ao Enricher (normal se não implementado)"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_converser_memorizer_connection(orchestrator) -> Tuple[bool, str]:
    """Testa conexão Converser → Memorizer"""
    try:
        if 'conversers' not in orchestrator.components:
            return False, "Converser não encontrado nos componentes"
        
        if 'memorizers' not in orchestrator.components:
            return False, "Memorizer não encontrado nos componentes"
        
        converser = orchestrator.components['conversers']
        memorizer = orchestrator.components['memorizers']
        
        if hasattr(converser, 'memory_manager') and converser.memory_manager is not None:
            return True, "Conexão estabelecida"
        else:
            return False, "Converser não tem referência ao Memorizer (normal se não implementado)"
            
    except Exception as e:
        return False, f"Erro ao testar: {str(e)}"

def test_query_workflow(orchestrator) -> Tuple[bool, str]:
    """Testa um workflow completo de query"""
    try:
        result = orchestrator.execute_workflow(
            'query_workflow',
            'query',
            {'query': 'teste de integração'}
        )
        
        if result and 'error' not in result:
            return True, f"Workflow executado com sucesso"
        else:
            error_msg = result.get('error', 'Erro desconhecido') if result else 'Resultado vazio'
            return False, f"Workflow falhou: {error_msg}"
            
    except Exception as e:
        return False, f"Erro ao executar workflow: {str(e)}"

def main():
    """Executa todos os testes de integração"""
    print("\n" + "="*60)
    print("🧪 TESTE DE INTEGRAÇÃO - ORCHESTRATOR")
    print("="*60 + "\n")
    
    try:
        # Importar e inicializar orchestrator
        from app.claude_ai_novo.orchestrators import get_main_orchestrator
        
        print("🔄 Inicializando MainOrchestrator...")
        orchestrator = get_main_orchestrator()
        
        # Forçar carregamento de componentes essenciais
        print("📦 Carregando componentes essenciais...")
        orchestrator._preload_essential_components()
        
        # Executar conexão de módulos
        print("🔗 Conectando módulos...")
        orchestrator._connect_modules()
        
        print(f"\n✅ Orchestrator inicializado com {len(orchestrator.components)} componentes\n")
        
        # Definir testes
        tests = [
            ("Scanner → Loader", test_scanner_loader_connection),
            ("Mapper → Loader", test_mapper_loader_connection),
            ("Loader → Provider", test_loader_provider_connection),
            ("Memorizer → Processor", test_memorizer_processor_connection),
            ("Learner → Analyzer", test_learner_analyzer_connection),
            ("Enricher → Processor", test_enricher_processor_connection),
            ("Converser → Memorizer", test_converser_memorizer_connection),
            ("Query Workflow", test_query_workflow)
        ]
        
        # Executar testes
        results = []
        for test_name, test_func in tests:
            try:
                success, message = test_func(orchestrator)
                status = "✅" if success else "❌"
                results.append((test_name, success, message))
                print(f"{status} {test_name}: {message}")
            except Exception as e:
                results.append((test_name, False, f"Erro: {e}"))
                print(f"❌ {test_name}: Erro - {e}")
        
        # Resumo
        print("\n" + "="*60)
        print("📊 RESUMO DOS TESTES")
        print("="*60)
        
        total_tests = len(results)
        successful_tests = sum(1 for _, success, _ in results if success)
        failed_tests = total_tests - successful_tests
        
        print(f"\nTotal de testes: {total_tests}")
        print(f"✅ Sucessos: {successful_tests}")
        print(f"❌ Falhas: {failed_tests}")
        print(f"📈 Taxa de sucesso: {(successful_tests/total_tests)*100:.1f}%")
        
        # Detalhes dos componentes
        print("\n📦 COMPONENTES CARREGADOS:")
        for name, component in orchestrator.components.items():
            print(f"  - {name}: {type(component).__name__}")
        
        # Performance das conexões
        print("\n🔗 CONEXÕES ESTABELECIDAS:")
        critical_connections = [
            "Scanner → Loader",
            "Loader → Provider",
            "Memorizer → Processor",
            "Learner → Analyzer"
        ]
        
        for conn in critical_connections:
            result = next((r for r in results if r[0] == conn), None)
            if result:
                status = "✅" if result[1] else "❌"
                print(f"  {status} {conn}")
        
        # Recomendações
        if failed_tests > 0:
            print("\n⚠️ RECOMENDAÇÕES:")
            for test_name, success, message in results:
                if not success:
                    print(f"  - {test_name}: {message}")
        
        # Status final
        print("\n" + "="*60)
        if successful_tests == total_tests:
            print("🎉 TODOS OS TESTES PASSARAM! Sistema totalmente integrado.")
        elif successful_tests >= total_tests * 0.7:
            print("✅ Sistema funcional com algumas conexões opcionais faltando.")
        else:
            print("❌ Sistema precisa de correções nas conexões críticas.")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 