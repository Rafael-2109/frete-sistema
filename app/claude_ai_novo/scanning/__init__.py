"""
🔍 SCANNING - Módulo de Escaneamento
===================================

Módulo responsável por escanear código, estruturas e metadados.
Responsabilidade: ESCANEAR (descobrir, analisar estruturas, metadados)
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Flask fallback para execução standalone
try:
    from ..utils.flask_fallback import is_flask_available
    flask_available = is_flask_available()
except ImportError:
    flask_available = False
    logger.warning("Flask fallback não disponível")

# Import dos componentes principais
_components = {}

try:
    from .scanning_manager import ScanningManager
    _components['ScanningManager'] = ScanningManager
except ImportError as e:
    logger.warning(f"ScanningManager não disponível: {e}")

try:
    from .database_manager import DatabaseManager
    _components['DatabaseManager'] = DatabaseManager
except ImportError as e:
    logger.warning(f"DatabaseManager não disponível: {e}")

try:
    from .project_scanner import ProjectScanner
    _components['ProjectScanner'] = ProjectScanner
except ImportError as e:
    logger.warning(f"ProjectScanner não disponível: {e}")

try:
    from .database_scanner import DatabaseScanner
    _components['DatabaseScanner'] = DatabaseScanner
except ImportError as e:
    logger.warning(f"DatabaseScanner não disponível: {e}")

try:
    from .code_scanner import CodeScanner
    _components['CodeScanner'] = CodeScanner
except ImportError as e:
    logger.warning(f"CodeScanner não disponível: {e}")

try:
    from .file_scanner import FileScanner
    _components['FileScanner'] = FileScanner
except ImportError as e:
    logger.warning(f"FileScanner não disponível: {e}")

try:
    from .structure_scanner import StructureScanner
    _components['StructureScanner'] = StructureScanner
except ImportError as e:
    logger.warning(f"StructureScanner não disponível: {e}")

try:
    from .readme_scanner import ReadmeScanner
    _components['ReadmeScanner'] = ReadmeScanner
except ImportError as e:
    logger.warning(f"ReadmeScanner não disponível: {e}")

# Funções de conveniência OBRIGATÓRIAS
def get_scanning_manager(app_path: Optional[str] = None) -> Optional[Any]:
    """Retorna instância configurada do ScanningManager."""
    try:
        cls = _components.get('ScanningManager')
        if cls:
            logger.info("Criando instância ScanningManager")
            return cls(app_path)
        else:
            logger.warning("ScanningManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ScanningManager: {e}")
        return None

def get_database_manager(db_engine=None, db_session=None) -> Optional[Any]:
    """Retorna instância configurada do DatabaseManager."""
    try:
        cls = _components.get('DatabaseManager')
        if cls:
            logger.info("Criando instância DatabaseManager")
            return cls(db_engine, db_session)
        else:
            logger.warning("DatabaseManager não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar DatabaseManager: {e}")
        return None

def get_project_scanner(app_path: Optional[str] = None) -> Optional[Any]:
    """Retorna instância configurada do ProjectScanner."""
    try:
        cls = _components.get('ProjectScanner')
        if cls:
            logger.info("Criando instância ProjectScanner")
            return cls(app_path)
        else:
            logger.warning("ProjectScanner não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ProjectScanner: {e}")
        return None

def get_database_scanner(db_engine=None) -> Optional[Any]:
    """Retorna instância configurada do DatabaseScanner."""
    try:
        cls = _components.get('DatabaseScanner')
        if cls:
            logger.info("Criando instância DatabaseScanner")
            return cls(db_engine)
        else:
            logger.warning("DatabaseScanner não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar DatabaseScanner: {e}")
        return None

def get_readme_scanner() -> Optional[Any]:
    """Retorna instância configurada do ReadmeScanner."""
    try:
        cls = _components.get('ReadmeScanner')
        if cls:
            logger.info("Criando instância ReadmeScanner")
            return cls()
        else:
            logger.warning("ReadmeScanner não disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao criar ReadmeScanner: {e}")
        return None

# Flask fallback para execução standalone
def scan_project(app_path: Optional[str] = None) -> dict:
    """Função de conveniência para escaneamento de projeto."""
    try:
        manager = get_scanning_manager(app_path)
        if manager:
            return manager.scan_complete_project()
        return {'error': 'ScanningManager não disponível', 'scanned': False}
    except Exception as e:
        logger.error(f"Erro ao escanear projeto: {e}")
        return {'error': str(e), 'scanned': False}

def scan_database(db_engine=None) -> dict:
    """Função de conveniência para escaneamento de banco."""
    try:
        scanner = get_database_scanner(db_engine)
        if scanner:
            return scanner.scan_complete_database()
        return {'error': 'DatabaseScanner não disponível', 'scanned': False}
    except Exception as e:
        logger.error(f"Erro ao escanear banco: {e}")
        return {'error': str(e), 'scanned': False}

def get_scanning_status() -> dict:
    """Função de conveniência para status dos scanners."""
    try:
        manager = get_scanning_manager()
        if manager:
            return manager.get_scanner_status()
        return {'error': 'ScanningManager não disponível'}
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return {'error': str(e)}

# Export explícito
__all__ = [
    'get_scanning_manager',
    'get_database_manager', 
    'get_project_scanner',
    'get_database_scanner',
    'get_readme_scanner',
    'scan_project',
    'scan_database',
    'get_scanning_status'
]

# Execução standalone
if __name__ == "__main__":
    print("🔍 SCANNING - Testando componentes")
    
    # Teste do ScanningManager
    manager = get_scanning_manager()
    if manager:
        print("✅ ScanningManager OK")
        status = manager.get_scanner_status()
        print(f"📊 Status: {status.get('status', 'unknown')}")
    else:
        print("❌ ScanningManager não disponível")
    
    # Teste dos componentes individuais
    components = ['DatabaseManager', 'ProjectScanner', 'DatabaseScanner', 'ReadmeScanner']
    for component in components:
        if component in _components:
            print(f"✅ {component} OK")
        else:
            print(f"❌ {component} não disponível")
    
    print("✅ Teste concluído")