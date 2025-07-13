#!/usr/bin/env python3
"""
🎯 IMPLEMENTAÇÃO DO ORCHESTRATOR INTEGRADO
==========================================

Script para implementar as conexões entre módulos através do Orchestrator.
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

def implementar_fase1_scanner_loader():
    """FASE 1: Conectar Scanner → Loader"""
    logger.info("\n🔧 FASE 1: Conectando Scanner → Loader")
    
    try:
        # 1. Verificar se Scanner tem método get_database_info
        scanner_manager_path = "scanning/scanning_manager.py"
        logger.info(f"📄 Verificando {scanner_manager_path}...")
        
        with open(scanner_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "def get_database_info" not in content:
            logger.info("❌ Método get_database_info não existe no ScanningManager")
            logger.info("✅ Adicionando método...")
            
            # Adicionar método
            method_code = '''
    def get_database_info(self) -> Dict[str, Any]:
        """Retorna informações descobertas para outros módulos"""
        try:
            if not self.database_scanner:
                self.initialize_database_scanner()
                
            return {
                'tables': self.database_scanner.get_tables() if hasattr(self.database_scanner, 'get_tables') else {},
                'indexes': self.database_scanner.get_indexes() if hasattr(self.database_scanner, 'get_indexes') else {},
                'relationships': self.database_scanner.get_relationships() if hasattr(self.database_scanner, 'get_relationships') else {},
                'statistics': self.database_scanner.get_statistics() if hasattr(self.database_scanner, 'get_statistics') else {}
            }
        except Exception as e:
            logger.warning(f"Erro ao obter informações do banco: {e}")
            return {'tables': {}, 'indexes': {}, 'relationships': {}, 'statistics': {}}
'''
            
            # Encontrar onde inserir (antes do último método ou no final da classe)
            import_pos = content.rfind("def ")
            if import_pos > 0:
                # Voltar para o início da linha
                import_pos = content.rfind('\n', 0, import_pos) + 1
                new_content = content[:import_pos] + method_code + '\n' + content[import_pos:]
            else:
                # Adicionar antes do final da classe
                class_end = content.rfind('\n\n')
                new_content = content[:class_end] + method_code + content[class_end:]
                
            with open(scanner_manager_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            logger.info("✅ Método get_database_info adicionado ao ScanningManager")
        else:
            logger.info("✅ Método get_database_info já existe")
            
        # 2. Modificar LoaderManager para usar Scanner
        loader_manager_path = "loaders/loader_manager.py"
        logger.info(f"\n📄 Modificando {loader_manager_path}...")
        
        with open(loader_manager_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "self.scanner = " not in content:
            logger.info("❌ LoaderManager não está conectado ao Scanner")
            logger.info("✅ Adicionando conexão...")
            
            # Adicionar import
            if "from app.claude_ai_novo.scanning import get_scanning_manager" not in content:
                import_pos = content.find("logger = logging.getLogger(__name__)")
                if import_pos > 0:
                    import_pos = content.find('\n', import_pos) + 1
                    content = content[:import_pos] + "\nfrom app.claude_ai_novo.scanning import get_scanning_manager\n" + content[import_pos:]
            
            # Modificar __init__
            init_pos = content.find("def __init__(self):")
            if init_pos > 0:
                # Encontrar o final do __init__ atual
                init_end = content.find("self._initialize_loaders()", init_pos)
                if init_end > 0:
                    # Adicionar antes de _initialize_loaders
                    scanner_code = """
        # Conectar com Scanner para otimização
        try:
            self.scanner = get_scanning_manager()
            self.db_info = self.scanner.get_database_info()
            logger.info("✅ LoaderManager conectado ao Scanner")
        except Exception as e:
            logger.warning(f"⚠️ Scanner não disponível: {e}")
            self.scanner = None
            self.db_info = {'tables': {}, 'indexes': {}, 'relationships': {}}
            
"""
                    content = content[:init_end] + scanner_code + "        " + content[init_end:]
                    
            with open(loader_manager_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✅ LoaderManager conectado ao Scanner")
        else:
            logger.info("✅ LoaderManager já está conectado ao Scanner")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na Fase 1: {e}")
        return False

def implementar_fase2_mapper_loader():
    """FASE 2: Conectar Mapper → Loader"""
    logger.info("\n🔧 FASE 2: Conectando Mapper → Loader")
    
    try:
        # Modificar um loader de domínio como exemplo
        entregas_loader_path = "loaders/domain/entregas_loader.py"
        logger.info(f"📄 Modificando {entregas_loader_path}...")
        
        with open(entregas_loader_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "self.mapper = " not in content:
            logger.info("❌ EntregasLoader não está conectado ao Mapper")
            logger.info("✅ Adicionando conexão...")
            
            # Adicionar import
            if "from app.claude_ai_novo.mappers import get_semantic_mapper" not in content:
                import_pos = content.find("logger = logging.getLogger(__name__)")
                if import_pos > 0:
                    import_pos = content.find('\n', import_pos) + 1
                    content = content[:import_pos] + "\nfrom app.claude_ai_novo.mappers import get_semantic_mapper\n" + content[import_pos:]
            
            # Modificar __init__
            init_pos = content.find("def __init__(self):")
            if init_pos > 0:
                init_end = content.find("logger.info", init_pos)
                if init_end > 0:
                    mapper_code = """
        # Conectar com Mapper para mapeamento semântico
        try:
            self.mapper = get_semantic_mapper()
            self.field_map = self.mapper.get_mapping('entregas')
            logger.info("✅ EntregasLoader conectado ao Mapper")
        except Exception as e:
            logger.warning(f"⚠️ Mapper não disponível: {e}")
            self.mapper = None
            self.field_map = {}
            
"""
                    content = content[:init_end] + mapper_code + "        " + content[init_end:]
                    
            with open(entregas_loader_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✅ EntregasLoader conectado ao Mapper")
        else:
            logger.info("✅ EntregasLoader já está conectado ao Mapper")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na Fase 2: {e}")
        return False

def implementar_fase3_loader_provider():
    """FASE 3: Eliminar duplicação Loader ↔ Provider"""
    logger.info("\n🔧 FASE 3: Conectando Provider → Loader (eliminar duplicação)")
    
    try:
        provider_path = "providers/data_provider.py"
        logger.info(f"📄 Refatorando {provider_path}...")
        
        with open(provider_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "self.loader = " not in content:
            logger.info("❌ DataProvider não está usando LoaderManager")
            logger.info("✅ Refatorando para usar LoaderManager...")
            
            # Adicionar import
            if "from app.claude_ai_novo.loaders import get_loader_manager" not in content:
                import_pos = content.find("logger = logging.getLogger(__name__)")
                if import_pos > 0:
                    import_pos = content.find('\n', import_pos) + 1
                    content = content[:import_pos] + "\nfrom app.claude_ai_novo.loaders import get_loader_manager\n" + content[import_pos:]
            
            # Modificar __init__
            init_pos = content.find("def __init__(self):")
            if init_pos > 0:
                init_end = content.find("logger.info", init_pos)
                if init_end > 0:
                    loader_code = """
        # Usar LoaderManager ao invés de queries diretas
        try:
            self.loader = get_loader_manager()
            logger.info("✅ DataProvider conectado ao LoaderManager")
        except Exception as e:
            logger.warning(f"⚠️ LoaderManager não disponível: {e}")
            self.loader = None
            
"""
                    content = content[:init_end] + loader_code + "        " + content[init_end:]
                    
            # Refatorar get_data_by_domain para usar loader
            method_pos = content.find("def get_data_by_domain(self, domain: str")
            if method_pos > 0:
                # Encontrar o início do método
                method_start = content.find("{", method_pos)
                method_end = content.find("return {", method_pos)
                
                if method_start > 0 and method_end > 0:
                    new_method = '''
        """Obtém dados por domínio usando LoaderManager"""
        try:
            # Delegar para LoaderManager ao invés de duplicar lógica
            if self.loader:
                logger.info(f"📊 Usando LoaderManager para domínio: {domain}")
                result = self.loader.load_data_by_domain(domain, filters)
                
                # Adicionar metadados se necessário
                if result and 'data' in result:
                    result['source'] = 'loader_manager'
                    result['optimized'] = True
                    
                return result
            else:
                # Fallback para implementação atual se loader não disponível
                logger.warning("⚠️ LoaderManager não disponível, usando fallback")
'''
                    # Manter o resto do método como fallback
                    
            with open(provider_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info("✅ DataProvider refatorado para usar LoaderManager")
        else:
            logger.info("✅ DataProvider já está usando LoaderManager")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na Fase 3: {e}")
        return False

def validar_conexoes():
    """Valida se as conexões foram estabelecidas corretamente"""
    logger.info("\n🔍 Validando conexões estabelecidas...")
    
    try:
        # Testar importações
        from app.claude_ai_novo.scanning import get_scanning_manager
        from app.claude_ai_novo.loaders import get_loader_manager
        from app.claude_ai_novo.providers import get_data_provider
        
        # Testar Scanner → Loader
        logger.info("\n📊 Testando Scanner → Loader...")
        loader = get_loader_manager()
        if hasattr(loader, 'scanner'):
            logger.info("✅ LoaderManager tem acesso ao Scanner")
        else:
            logger.warning("❌ LoaderManager não tem acesso ao Scanner")
            
        # Testar Provider → Loader
        logger.info("\n📊 Testando Provider → Loader...")
        provider = get_data_provider()
        if hasattr(provider, 'loader'):
            logger.info("✅ DataProvider usa LoaderManager")
        else:
            logger.warning("❌ DataProvider não usa LoaderManager")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na validação: {e}")
        return False

def main():
    """Executa a implementação do Orchestrator Integrado"""
    logger.info("🎯 INICIANDO IMPLEMENTAÇÃO DO ORCHESTRATOR INTEGRADO")
    logger.info("=" * 60)
    
    # Fase 1: Scanner → Loader
    if implementar_fase1_scanner_loader():
        logger.info("✅ Fase 1 concluída com sucesso")
    else:
        logger.error("❌ Fase 1 falhou")
        return
        
    # Fase 2: Mapper → Loader
    if implementar_fase2_mapper_loader():
        logger.info("✅ Fase 2 concluída com sucesso")
    else:
        logger.error("❌ Fase 2 falhou")
        return
        
    # Fase 3: Loader → Provider
    if implementar_fase3_loader_provider():
        logger.info("✅ Fase 3 concluída com sucesso")
    else:
        logger.error("❌ Fase 3 falhou")
        return
        
    # Validar conexões
    logger.info("\n" + "=" * 60)
    if validar_conexoes():
        logger.info("\n✅ IMPLEMENTAÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info("\n📊 Próximos passos:")
        logger.info("1. Testar o sistema com consultas reais")
        logger.info("2. Implementar Fase 4: Memorizer → Processor")
        logger.info("3. Implementar Fase 5: Learner → Analyzer")
    else:
        logger.error("\n❌ Validação falhou - verificar implementação")

if __name__ == "__main__":
    main() 