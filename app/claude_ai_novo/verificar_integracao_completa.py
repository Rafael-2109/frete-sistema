"""
🔍 VERIFICADOR DE INTEGRAÇÃO COMPLETA
====================================

Verifica se os 3 módulos fundamentais estão integrados:
1. Scanner (descobre estrutura)
2. Mapper (define semântica)  
3. Loader (carrega dados)
"""

import sys
import os
from pathlib import Path

# Adicionar caminho raiz ao PYTHONPATH
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

import logging
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_scanner_manager():
    """Verifica ScanningManager e suas capacidades"""
    logger.info("\n" + "="*60)
    logger.info("🔍 VERIFICANDO SCANNING MANAGER")
    logger.info("="*60)
    
    resultado = {
        'disponivel': False,
        'database_manager': False,
        'auto_mapper': False,
        'get_database_info': False,
        'metodos_descoberta': []
    }
    
    try:
        from app.claude_ai_novo.scanning import get_scanning_manager
        scanner = get_scanning_manager()
        resultado['disponivel'] = True
        logger.info("✅ ScanningManager disponível")
        
        # Verificar DatabaseManager
        if hasattr(scanner, 'database_manager') and scanner.database_manager:
            resultado['database_manager'] = True
            logger.info("✅ DatabaseManager integrado")
            
            # Verificar auto_mapper
            if hasattr(scanner.database_manager, 'auto_mapper'):
                resultado['auto_mapper'] = True
                logger.info("✅ AutoMapper disponível via DatabaseManager")
            else:
                logger.warning("❌ AutoMapper NÃO disponível no DatabaseManager")
        
        # Verificar método get_database_info
        if hasattr(scanner, 'get_database_info'):
            resultado['get_database_info'] = True
            logger.info("✅ Método get_database_info() disponível")
        else:
            logger.warning("❌ Método get_database_info() NÃO disponível")
        
        # Listar métodos de descoberta
        metodos_descoberta = [m for m in dir(scanner) if m.startswith(('discover_', 'scan_'))]
        resultado['metodos_descoberta'] = metodos_descoberta
        logger.info(f"📊 Métodos de descoberta: {len(metodos_descoberta)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar ScanningManager: {e}")
    
    return resultado


def verificar_mapper_manager():
    """Verifica MapperManager e suas capacidades"""
    logger.info("\n" + "="*60)
    logger.info("🗺️ VERIFICANDO MAPPER MANAGER")
    logger.info("="*60)
    
    resultado = {
        'disponivel': False,
        'mappers_dominio': [],
        'initialize_with_schema': False,
        'apply_auto_suggestions': False,
        'metodos_mapeamento': []
    }
    
    try:
        from app.claude_ai_novo.mappers import get_mapper_manager
        mapper = get_mapper_manager()
        resultado['disponivel'] = True
        logger.info("✅ MapperManager disponível")
        
        # Verificar mappers de domínio
        if hasattr(mapper, 'mappers'):
            resultado['mappers_dominio'] = list(mapper.mappers.keys())
            logger.info(f"✅ Mappers de domínio: {resultado['mappers_dominio']}")
        
        # Verificar métodos de integração
        if hasattr(mapper, 'initialize_with_schema'):
            resultado['initialize_with_schema'] = True
            logger.info("✅ Método initialize_with_schema() disponível")
        else:
            logger.warning("❌ Método initialize_with_schema() NÃO disponível")
            
        if hasattr(mapper, 'apply_auto_suggestions'):
            resultado['apply_auto_suggestions'] = True
            logger.info("✅ Método apply_auto_suggestions() disponível")
        else:
            logger.warning("❌ Método apply_auto_suggestions() NÃO disponível")
        
        # Listar métodos de mapeamento
        metodos_mapeamento = [m for m in dir(mapper) if m.startswith(('map_', 'get_mapping', 'analisar_'))]
        resultado['metodos_mapeamento'] = metodos_mapeamento
        logger.info(f"📊 Métodos de mapeamento: {len(metodos_mapeamento)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar MapperManager: {e}")
    
    return resultado


def verificar_loader_manager():
    """Verifica LoaderManager e suas capacidades"""
    logger.info("\n" + "="*60)
    logger.info("📦 VERIFICANDO LOADER MANAGER")
    logger.info("="*60)
    
    resultado = {
        'disponivel': False,
        'loaders_dominio': [],
        'configure_with_scanner': False,
        'configure_with_mapper': False,
        'scanner_configurado': False,
        'mapper_configurado': False,
        'metodos_carregamento': []
    }
    
    try:
        from app.claude_ai_novo.loaders import get_loader_manager
        loader = get_loader_manager()
        resultado['disponivel'] = True
        logger.info("✅ LoaderManager disponível")
        
        # Verificar loaders de domínio
        if hasattr(loader, '_loader_mapping'):
            resultado['loaders_dominio'] = list(loader._loader_mapping.keys())
            logger.info(f"✅ Loaders de domínio: {resultado['loaders_dominio']}")
        
        # Verificar métodos de configuração
        if hasattr(loader, 'configure_with_scanner'):
            resultado['configure_with_scanner'] = True
            logger.info("✅ Método configure_with_scanner() disponível")
            
            # Verificar se scanner está configurado
            if hasattr(loader, 'scanner') and loader.scanner:
                resultado['scanner_configurado'] = True
                logger.info("✅ Scanner já está configurado no LoaderManager")
            else:
                logger.warning("⚠️ Scanner NÃO está configurado no LoaderManager")
        
        if hasattr(loader, 'configure_with_mapper'):
            resultado['configure_with_mapper'] = True
            logger.info("✅ Método configure_with_mapper() disponível")
            
            # Verificar se mapper está configurado
            if hasattr(loader, 'mapper') and loader.mapper:
                resultado['mapper_configurado'] = True
                logger.info("✅ Mapper já está configurado no LoaderManager")
            else:
                logger.warning("⚠️ Mapper NÃO está configurado no LoaderManager")
        
        # Listar métodos de carregamento
        metodos_carregamento = [m for m in dir(loader) if m.startswith(('load_', 'get_best_loader'))]
        resultado['metodos_carregamento'] = metodos_carregamento
        logger.info(f"📊 Métodos de carregamento: {len(metodos_carregamento)}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar LoaderManager: {e}")
    
    return resultado


def verificar_orchestrator():
    """Verifica MainOrchestrator e conexões"""
    logger.info("\n" + "="*60)
    logger.info("🎭 VERIFICANDO MAIN ORCHESTRATOR")
    logger.info("="*60)
    
    resultado = {
        'disponivel': False,
        '_connect_modules': False,
        'componentes_registrados': [],
        'conexoes_verificadas': []
    }
    
    try:
        from app.claude_ai_novo.orchestrators import get_main_orchestrator
        orchestrator = get_main_orchestrator()
        resultado['disponivel'] = True
        logger.info("✅ MainOrchestrator disponível")
        
        # Verificar método _connect_modules
        if hasattr(orchestrator, '_connect_modules'):
            resultado['_connect_modules'] = True
            logger.info("✅ Método _connect_modules() disponível")
        else:
            logger.warning("❌ Método _connect_modules() NÃO disponível")
        
        # Verificar componentes registrados
        if hasattr(orchestrator, 'components'):
            resultado['componentes_registrados'] = list(orchestrator.components.keys())
            logger.info(f"✅ Componentes registrados: {resultado['componentes_registrados']}")
        
        # Verificar conexões específicas
        conexoes = []
        if 'scanners' in orchestrator.components and 'loaders' in orchestrator.components:
            conexoes.append("Scanner → Loader")
        if 'mappers' in orchestrator.components and 'loaders' in orchestrator.components:
            conexoes.append("Mapper → Loader")
        if 'loaders' in orchestrator.components and 'providers' in orchestrator.components:
            conexoes.append("Loader → Provider")
            
        resultado['conexoes_verificadas'] = conexoes
        logger.info(f"🔗 Conexões possíveis: {conexoes}")
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar MainOrchestrator: {e}")
    
    return resultado


def testar_integracao_funcional():
    """Testa se a integração está funcionando na prática"""
    logger.info("\n" + "="*60)
    logger.info("🧪 TESTANDO INTEGRAÇÃO FUNCIONAL")
    logger.info("="*60)
    
    resultado = {
        'scanner_loader': False,
        'mapper_loader': False,
        'auto_mapper_mapper': False,
        'fluxo_completo': False
    }
    
    try:
        # Teste 1: Scanner → Loader
        logger.info("\n🔄 Teste 1: Scanner → Loader")
        from app.claude_ai_novo.scanning import get_scanning_manager
        from app.claude_ai_novo.loaders import get_loader_manager
        
        scanner = get_scanning_manager()
        loader = get_loader_manager()
        
        # Configurar loader com scanner
        if hasattr(loader, 'configure_with_scanner'):
            loader.configure_with_scanner(scanner)
            
            # Verificar se funcionou
            if hasattr(loader, 'scanner') and loader.scanner == scanner:
                resultado['scanner_loader'] = True
                logger.info("✅ Scanner → Loader integração funcional!")
            else:
                logger.warning("❌ Scanner → Loader integração falhou")
        
        # Teste 2: Mapper → Loader
        logger.info("\n🔄 Teste 2: Mapper → Loader")
        from app.claude_ai_novo.mappers import get_mapper_manager
        
        mapper = get_mapper_manager()
        
        if hasattr(loader, 'configure_with_mapper'):
            loader.configure_with_mapper(mapper)
            
            # Verificar se funcionou
            if hasattr(loader, 'mapper') and loader.mapper == mapper:
                resultado['mapper_loader'] = True
                logger.info("✅ Mapper → Loader integração funcional!")
            else:
                logger.warning("❌ Mapper → Loader integração falhou")
        
        # Teste 3: AutoMapper → MapperManager
        logger.info("\n🔄 Teste 3: AutoMapper → MapperManager")
        if hasattr(scanner, 'database_manager') and scanner.database_manager:
            if hasattr(scanner.database_manager, 'auto_mapper'):
                auto_mapper = scanner.database_manager.auto_mapper
                
                # Tentar gerar mapeamento automático
                if hasattr(auto_mapper, 'gerar_mapeamento_automatico'):
                    try:
                        # Testar com tabela pedidos
                        auto_mapping = auto_mapper.gerar_mapeamento_automatico('pedidos')
                        if auto_mapping:
                            logger.info("✅ AutoMapper gerou mapeamento para 'pedidos'")
                            
                            # Verificar se mapper pode usar
                            if hasattr(mapper, 'apply_auto_suggestions'):
                                resultado['auto_mapper_mapper'] = True
                                logger.info("✅ MapperManager PODE receber auto_mappings (método existe)")
                            else:
                                logger.warning("❌ MapperManager NÃO pode receber auto_mappings")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao testar AutoMapper: {e}")
        
        # Teste 4: Fluxo completo
        logger.info("\n🔄 Teste 4: Fluxo completo")
        try:
            # Scanner descobre
            if hasattr(scanner, 'get_database_info'):
                db_info = scanner.get_database_info()
                logger.info(f"📊 Scanner descobriu: {len(db_info.get('tables', {}))} tabelas")
            
            # Mapper inicializa com schema
            if hasattr(mapper, 'initialize_with_schema') and db_info:
                mapper.initialize_with_schema(db_info)
                logger.info("✅ Mapper inicializado com schema do banco")
            
            # Loader usa ambos
            if loader.scanner and loader.mapper:
                resultado['fluxo_completo'] = True
                logger.info("✅ FLUXO COMPLETO: Scanner → Mapper → Loader funcionando!")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro no fluxo completo: {e}")
        
    except Exception as e:
        logger.error(f"❌ Erro nos testes funcionais: {e}")
    
    return resultado


def gerar_relatorio_completo():
    """Gera relatório completo da verificação"""
    logger.info("\n" + "="*60)
    logger.info("📄 GERANDO RELATÓRIO COMPLETO")
    logger.info("="*60)
    
    relatorio = {
        'timestamp': datetime.now().isoformat(),
        'scanner': verificar_scanner_manager(),
        'mapper': verificar_mapper_manager(),
        'loader': verificar_loader_manager(),
        'orchestrator': verificar_orchestrator(),
        'testes_funcionais': testar_integracao_funcional()
    }
    
    # Análise de problemas
    problemas = []
    recomendacoes = []
    
    # Verificar problemas no Scanner
    if not relatorio['scanner']['auto_mapper']:
        problemas.append("AutoMapper não está acessível via DatabaseManager")
        recomendacoes.append("Verificar se DatabaseManager expõe auto_mapper como propriedade pública")
    
    if not relatorio['scanner']['get_database_info']:
        problemas.append("ScanningManager não tem método get_database_info()")
        recomendacoes.append("Implementar get_database_info() no ScanningManager")
    
    # Verificar problemas no Mapper
    if not relatorio['mapper']['apply_auto_suggestions']:
        problemas.append("MapperManager não pode receber sugestões do AutoMapper")
        recomendacoes.append("Implementar apply_auto_suggestions() no MapperManager")
    
    # Verificar problemas no Loader
    if not relatorio['loader']['scanner_configurado']:
        problemas.append("LoaderManager não tem Scanner configurado")
        recomendacoes.append("Garantir que Orchestrator chame loader.configure_with_scanner()")
    
    if not relatorio['loader']['mapper_configurado']:
        problemas.append("LoaderManager não tem Mapper configurado")
        recomendacoes.append("Garantir que Orchestrator chame loader.configure_with_mapper()")
    
    # Verificar problemas no Orchestrator
    if not relatorio['orchestrator']['_connect_modules']:
        problemas.append("MainOrchestrator não tem método _connect_modules()")
        recomendacoes.append("Implementar _connect_modules() no MainOrchestrator")
    
    # Adicionar ao relatório
    relatorio['analise'] = {
        'problemas_encontrados': problemas,
        'recomendacoes': recomendacoes,
        'integracao_completa': len(problemas) == 0
    }
    
    # Salvar relatório
    with open('verificacao_integracao_completa.json', 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n📊 RESUMO:")
    logger.info(f"- Scanner: {'✅' if relatorio['scanner']['disponivel'] else '❌'}")
    logger.info(f"- Mapper: {'✅' if relatorio['mapper']['disponivel'] else '❌'}")
    logger.info(f"- Loader: {'✅' if relatorio['loader']['disponivel'] else '❌'}")
    logger.info(f"- Orchestrator: {'✅' if relatorio['orchestrator']['disponivel'] else '❌'}")
    logger.info(f"- Integração Completa: {'✅' if relatorio['analise']['integracao_completa'] else '❌'}")
    logger.info(f"\n⚠️ Problemas encontrados: {len(problemas)}")
    
    if problemas:
        logger.info("\n🔧 PROBLEMAS:")
        for p in problemas:
            logger.info(f"  - {p}")
        
        logger.info("\n💡 RECOMENDAÇÕES:")
        for r in recomendacoes:
            logger.info(f"  - {r}")
    
    return relatorio


if __name__ == "__main__":
    logger.info("🚀 Iniciando verificação de integração completa...")
    relatorio = gerar_relatorio_completo()
    logger.info("\n✅ Verificação concluída! Relatório salvo em 'verificacao_integracao_completa.json'") 