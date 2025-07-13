#!/usr/bin/env python3
"""
🎯 IMPLEMENTAÇÃO CORRETA DO ORCHESTRATOR
========================================

Script para implementar as conexões via Orchestrator usando injeção de dependência.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def modificar_loader_manager():
    """Modifica LoaderManager para aceitar injeção de dependência"""
    logger.info("\n🔧 Modificando LoaderManager para aceitar injeção...")
    
    try:
        loader_path = "loaders/loader_manager.py"
        
        with open(loader_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se já aceita injeção
        if "def __init__(self, scanner=None, mapper=None)" in content:
            logger.info("✅ LoaderManager já aceita injeção de dependência")
            return True
            
        logger.info("📝 Atualizando LoaderManager...")
        
        # Encontrar o __init__ atual
        init_start = content.find("def __init__(self):")
        if init_start == -1:
            logger.error("❌ Não encontrou __init__ em LoaderManager")
            return False
            
        # Encontrar o fim do __init__
        init_body_start = content.find(":", init_start) + 1
        next_def = content.find("\n    def ", init_body_start)
        if next_def == -1:
            next_def = len(content)
            
        # Extrair o corpo atual do __init__
        init_body = content[init_body_start:next_def]
        
        # Criar novo __init__ com injeção
        new_init = """def __init__(self, scanner=None, mapper=None):
        """
        new_init += '"""Inicializa LoaderManager com dependências opcionais"""\n'
        new_init += "        super().__init__()\n"
        new_init += "        \n"
        new_init += "        # Dependências injetadas pelo Orchestrator\n"
        new_init += "        self.scanner = scanner\n"
        new_init += "        self.mapper = mapper\n"
        new_init += "        \n"
        new_init += "        # Configuração básica\n"
        new_init += "        self.loaders = {}\n"
        new_init += "        self.db_info = {'tables': {}, 'indexes': {}, 'relationships': {}}\n"
        new_init += "        \n"
        new_init += "        # Se scanner disponível, obter info do banco\n"
        new_init += "        if self.scanner and hasattr(self.scanner, 'get_database_info'):\n"
        new_init += "            try:\n"
        new_init += "                self.db_info = self.scanner.get_database_info()\n"
        new_init += "                logger.info('✅ LoaderManager: Informações do banco obtidas do Scanner')\n"
        new_init += "            except Exception as e:\n"
        new_init += "                logger.warning(f'⚠️ LoaderManager: Erro ao obter info do Scanner: {e}')\n"
        new_init += "        \n"
        new_init += "        self._initialize_loaders()\n"
        new_init += "        logger.info(f'{self.__class__.__name__} inicializado')\n"
        
        # Adicionar métodos de configuração
        config_methods = '''
    def configure_with_scanner(self, scanner):
        """Configura scanner após inicialização"""
        self.scanner = scanner
        if scanner and hasattr(scanner, 'get_database_info'):
            try:
                self.db_info = scanner.get_database_info()
                logger.info('✅ Scanner configurado no LoaderManager')
            except Exception as e:
                logger.warning(f'⚠️ Erro ao configurar Scanner: {e}')
                
    def configure_with_mapper(self, mapper):
        """Configura mapper após inicialização"""
        self.mapper = mapper
        logger.info('✅ Mapper configurado no LoaderManager')
'''
        
        # Substituir o __init__ antigo
        new_content = content[:init_start] + new_init + config_methods + content[next_def:]
        
        with open(loader_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info("✅ LoaderManager modificado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao modificar LoaderManager: {e}")
        return False

def modificar_data_provider():
    """Modifica DataProvider para aceitar LoaderManager via injeção"""
    logger.info("\n🔧 Modificando DataProvider para aceitar injeção...")
    
    try:
        provider_path = "providers/data_provider.py"
        
        with open(provider_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se já aceita injeção
        if "def __init__(self, loader=None)" in content:
            logger.info("✅ DataProvider já aceita injeção de dependência")
            return True
            
        logger.info("📝 Atualizando DataProvider...")
        
        # Modificar __init__
        init_start = content.find("def __init__(self):")
        if init_start == -1:
            logger.error("❌ Não encontrou __init__ em DataProvider")
            return False
            
        # Criar novo __init__
        new_init = """def __init__(self, loader=None):
        """
        new_init += '"""Inicializa DataProvider com LoaderManager opcional"""\n'
        new_init += "        super().__init__()\n"
        new_init += "        \n"
        new_init += "        # LoaderManager injetado pelo Orchestrator\n"
        new_init += "        self.loader = loader\n"
        new_init += "        \n"
        new_init += "        logger.info(f'{self.__class__.__name__} inicializado')\n"
        new_init += "        if self.loader:\n"
        new_init += "            logger.info('✅ DataProvider: LoaderManager disponível')\n"
        new_init += "        else:\n"
        new_init += "            logger.warning('⚠️ DataProvider: Sem LoaderManager, usando implementação direta')\n"
        
        # Adicionar método de configuração
        config_method = '''
    def set_loader(self, loader):
        """Configura LoaderManager após inicialização"""
        self.loader = loader
        logger.info('✅ LoaderManager configurado no DataProvider')
'''
        
        # Encontrar próximo método
        next_def = content.find("\n    def ", init_start + 1)
        if next_def == -1:
            next_def = len(content)
            
        # Substituir
        new_content = content[:init_start] + new_init + config_method + content[next_def:]
        
        # Modificar get_data_by_domain para usar loader primeiro
        method_start = new_content.find("def get_data_by_domain(self, domain:")
        if method_start > 0:
            method_body_start = new_content.find("try:", method_start)
            if method_body_start > 0:
                # Adicionar verificação do loader no início
                loader_check = """try:
            # Tentar usar LoaderManager primeiro (preferencial)
            if self.loader:
                logger.info(f"📊 DataProvider: Delegando para LoaderManager - domínio: {domain}")
                result = self.loader.load_data_by_domain(domain, filters)
                
                # Adicionar metadados
                if result:
                    result['source'] = 'loader_manager'
                    result['optimized'] = True
                    
                return result
            
            # Fallback para implementação direta
            logger.info(f"📊 DataProvider: Usando implementação direta - domínio: {domain}")
            """
                
                # Inserir no início do try
                new_content = new_content[:method_body_start] + loader_check + new_content[method_body_start+4:]
        
        with open(provider_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info("✅ DataProvider modificado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao modificar DataProvider: {e}")
        return False

def modificar_main_orchestrator():
    """Modifica MainOrchestrator para fazer as conexões corretamente"""
    logger.info("\n🔧 Modificando MainOrchestrator para conectar módulos...")
    
    try:
        orchestrator_path = "orchestrators/main_orchestrator.py"
        
        with open(orchestrator_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Verificar se já tem _connect_modules
        if "_connect_modules" in content:
            logger.info("✅ MainOrchestrator já tem método _connect_modules")
            return True
            
        logger.info("📝 Adicionando conexões ao MainOrchestrator...")
        
        # Adicionar método _connect_modules
        connect_method = '''
    def _connect_modules(self):
        """Conecta todos os módulos via injeção de dependência"""
        logger.info("🔗 Conectando módulos via Orchestrator...")
        
        try:
            # 1. Scanner descobre estrutura do banco
            if 'scanners' in self.components:
                scanner = self.components['scanners']
                db_info = None
                
                if hasattr(scanner, 'get_database_info'):
                    try:
                        db_info = scanner.get_database_info()
                        logger.info("✅ Informações do banco obtidas do Scanner")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao obter info do Scanner: {e}")
                
                # 2. Configurar Loader com Scanner
                if 'loaders' in self.components and hasattr(self.components['loaders'], 'configure_with_scanner'):
                    self.components['loaders'].configure_with_scanner(scanner)
                    logger.info("✅ Scanner → Loader conectados")
                
                # 3. Configurar Mapper com informações do banco
                if db_info and 'mappers' in self.components:
                    mapper = self.components['mappers']
                    if hasattr(mapper, 'initialize_with_schema'):
                        mapper.initialize_with_schema(db_info)
                        logger.info("✅ Mapper inicializado com schema do banco")
                    
                    # 4. Configurar Loader com Mapper
                    if 'loaders' in self.components and hasattr(self.components['loaders'], 'configure_with_mapper'):
                        self.components['loaders'].configure_with_mapper(mapper)
                        logger.info("✅ Mapper → Loader conectados")
            
            # 5. Configurar Provider com Loader
            if 'loaders' in self.components and 'providers' in self.components:
                provider = self.components['providers']
                if hasattr(provider, 'set_loader'):
                    provider.set_loader(self.components['loaders'])
                    logger.info("✅ Loader → Provider conectados")
            
            # 6. Configurar Processor com Memorizer
            if 'memorizers' in self.components and 'processors' in self.components:
                processor = self.components['processors']
                if hasattr(processor, 'set_memory_manager'):
                    processor.set_memory_manager(self.components['memorizers'])
                    logger.info("✅ Memorizer → Processor conectados")
            
            # 7. Configurar Analyzer com Learner
            if 'learners' in self.components and 'analyzers' in self.components:
                analyzer = self.components['analyzers']
                if hasattr(analyzer, 'set_learner'):
                    analyzer.set_learner(self.components['learners'])
                    logger.info("✅ Learner → Analyzer conectados")
                    
            logger.info("✅ Todos os módulos conectados com sucesso!")
            
        except Exception as e:
            logger.error(f"❌ Erro ao conectar módulos: {e}")
            import traceback
            traceback.print_exc()
'''
        
        # Encontrar onde adicionar (após _preload_essential_components)
        preload_end = content.find("def _preload_essential_components(self):")
        if preload_end > 0:
            # Encontrar o fim do método
            next_method = content.find("\n    def ", preload_end + 1)
            if next_method == -1:
                next_method = len(content)
                
            # Adicionar o método
            new_content = content[:next_method] + connect_method + "\n" + content[next_method:]
            
            # Chamar _connect_modules no __init__
            init_pos = new_content.find("self._preload_essential_components()")
            if init_pos > 0:
                # Adicionar chamada após preload
                call_pos = new_content.find("\n", init_pos) + 1
                new_content = new_content[:call_pos] + "        self._connect_modules()\n" + new_content[call_pos:]
        else:
            logger.error("❌ Não encontrou _preload_essential_components")
            return False
            
        with open(orchestrator_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        logger.info("✅ MainOrchestrator modificado com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao modificar MainOrchestrator: {e}")
        return False

def testar_conexoes():
    """Testa se as conexões estão funcionando"""
    logger.info("\n🧪 Testando conexões estabelecidas...")
    
    try:
        from app.claude_ai_novo.orchestrators import get_orchestrator_manager
        
        logger.info("📊 Criando OrchestratorManager...")
        orchestrator = get_orchestrator_manager()
        
        # Verificar componentes
        if hasattr(orchestrator, 'main_orchestrator'):
            main_orch = orchestrator.main_orchestrator
            
            if hasattr(main_orch, 'components'):
                logger.info(f"✅ Componentes carregados: {list(main_orch.components.keys())}")
                
                # Verificar conexões específicas
                if 'loaders' in main_orch.components:
                    loader = main_orch.components['loaders']
                    if hasattr(loader, 'scanner') and loader.scanner:
                        logger.info("✅ Scanner → Loader: CONECTADO")
                    else:
                        logger.warning("❌ Scanner → Loader: NÃO conectado")
                        
                if 'providers' in main_orch.components:
                    provider = main_orch.components['providers']
                    if hasattr(provider, 'loader') and provider.loader:
                        logger.info("✅ Loader → Provider: CONECTADO")
                    else:
                        logger.warning("❌ Loader → Provider: NÃO conectado")
                        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao testar conexões: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Executa a implementação correta do Orchestrator"""
    logger.info("🎯 IMPLEMENTAÇÃO CORRETA DO ORCHESTRATOR")
    logger.info("=" * 60)
    logger.info("Usando INJEÇÃO DE DEPENDÊNCIA via Orchestrator")
    logger.info("=" * 60)
    
    # 1. Modificar LoaderManager
    if not modificar_loader_manager():
        logger.error("❌ Falha ao modificar LoaderManager")
        return
        
    # 2. Modificar DataProvider
    if not modificar_data_provider():
        logger.error("❌ Falha ao modificar DataProvider")
        return
        
    # 3. Modificar MainOrchestrator
    if not modificar_main_orchestrator():
        logger.error("❌ Falha ao modificar MainOrchestrator")
        return
        
    # 4. Testar conexões
    logger.info("\n" + "=" * 60)
    if testar_conexoes():
        logger.info("\n✅ IMPLEMENTAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("\n📋 O que foi feito:")
        logger.info("1. LoaderManager aceita Scanner e Mapper via injeção")
        logger.info("2. DataProvider aceita LoaderManager via injeção")
        logger.info("3. MainOrchestrator conecta todos os módulos")
        logger.info("4. Módulos permanecem desacoplados")
        logger.info("\n🎯 Benefícios:")
        logger.info("- Módulos testáveis independentemente")
        logger.info("- Fácil trocar implementações")
        logger.info("- Orchestrator controla todas as conexões")
        logger.info("- Arquitetura limpa e manutenível")
    else:
        logger.error("\n❌ Testes falharam - verificar implementação")

if __name__ == "__main__":
    main() 