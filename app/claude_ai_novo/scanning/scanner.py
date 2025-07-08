"""
🔍 CLAUDE PROJECT SCANNER - Interface Unificada Atualizada
=========================================================

Sistema de escaneamento com arquitetura modular.
Mantém interface original mas usa módulos especializados.

NOVA ARQUITETURA:
- ProjectScanner: Núcleo principal e coordenação
- StructureScanner: Descoberta de estrutura e modelos
- CodeScanner: Análise de formulários e rotas
- FileScanner: Manipulação de arquivos e templates
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Imports dos módulos especializados
from .project_scanner import ProjectScanner, get_project_scanner, init_project_scanner
from .structure_scanner import StructureScanner, get_structure_scanner
from .code_scanner import CodeScanner, get_code_scanner
from .file_scanner import FileScanner, get_file_scanner

logger = logging.getLogger(__name__)

class ClaudeProjectScanner:
    """
    Interface unificada para o sistema de escaneamento de projeto.
    
    ARQUITETURA MODULAR - Usa componentes especializados:
    - project_scanner: Coordenação e ciclo principal
    - structure_scanner: Descoberta de estrutura e modelos
    - code_scanner: Análise de formulários e rotas
    - file_scanner: Manipulação de arquivos e templates
    """
    
    def __init__(self, app_path: Optional[str] = None):
        """Inicializa o scanner com arquitetura modular"""
        
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        
        # Inicializar módulo principal (lazy loading)
        self._project_scanner = None
        
        # Para compatibilidade - propriedades herdadas
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        logger.info(f"🔍 ClaudeProjectScanner inicializado com arquitetura modular: {self.app_path}")
    
    @property
    def project_scanner(self):
        """Lazy loading do ProjectScanner"""
        if self._project_scanner is None:
            self._project_scanner = init_project_scanner(str(self.app_path))
        return self._project_scanner
    
    # ================================
    # INTERFACE DE COMPATIBILIDADE
    # Delega para módulos especializados
    # ================================
    
    def scan_complete_project(self) -> Dict[str, Any]:
        """
        ESCANEAMENTO COMPLETO DO PROJETO (método principal).
        
        Delega para o ProjectScanner que coordena todo o processo.
        """
        complete_map = self.project_scanner.scan_complete_project()
        
        # Sincronizar propriedades para compatibilidade
        if 'project_structure' in complete_map:
            self.project_structure = complete_map['project_structure']
        if 'models' in complete_map:
            self.discovered_models = complete_map['models']
        if 'forms' in complete_map:
            self.discovered_forms = complete_map['forms']
        if 'routes' in complete_map:
            self.discovered_routes = complete_map['routes']
        if 'templates' in complete_map:
            self.discovered_templates = complete_map['templates']
        if 'database_schema' in complete_map:
            self.database_schema = complete_map['database_schema']
        
        return complete_map
    
    def read_file_content(self, file_path: str, encoding: str = 'utf-8') -> str:
        """Lê conteúdo de arquivo - delega para FileScanner"""
        return self.project_scanner.file_scanner.read_file_content(file_path, encoding)
    
    def list_directory_contents(self, dir_path: str = '') -> Dict[str, Any]:
        """Lista conteúdo de diretório - delega para FileScanner"""
        return self.project_scanner.file_scanner.list_directory_contents(dir_path)
    
    def search_in_files(self, pattern: str, file_extensions: Optional[List[str]] = None, 
                       max_results: int = 500) -> Dict[str, Any]:
        """Busca em arquivos - delega para FileScanner"""
        return self.project_scanner.file_scanner.search_in_files(pattern, file_extensions, max_results)
    
    # ================================
    # MÉTODOS ESPECÍFICOS DOS MÓDULOS
    # Acesso direto aos componentes especializados
    # ================================
    
    def scan_project_light(self) -> Dict[str, Any]:
        """Escaneamento rápido usando ProjectScanner"""
        return self.project_scanner.scan_project_light()
    
    def discover_project_structure(self) -> Dict[str, Any]:
        """Descobre estrutura usando StructureScanner"""
        return self.project_scanner.structure_scanner.discover_project_structure()
    
    def discover_all_models(self) -> Dict[str, Any]:
        """Descobre modelos usando StructureScanner"""
        return self.project_scanner.structure_scanner.discover_all_models()
    
    def discover_all_forms(self) -> Dict[str, Any]:
        """Descobre formulários usando CodeScanner"""
        return self.project_scanner.code_scanner.discover_all_forms()
    
    def discover_all_routes(self) -> Dict[str, Any]:
        """Descobre rotas usando CodeScanner"""
        return self.project_scanner.code_scanner.discover_all_routes()
    
    def discover_all_templates(self) -> Dict[str, Any]:
        """Descobre templates usando FileScanner"""
        return self.project_scanner.file_scanner.discover_all_templates()
    
    # ================================
    # NOVOS MÉTODOS AVANÇADOS
    # Aproveitam a arquitetura modular
    # ================================
    
    def get_scanner_status(self) -> Dict[str, Any]:
        """Obtém status completo usando ProjectScanner"""
        return self.project_scanner.get_scanner_status()
    
    def get_modulos_especializados(self) -> Dict[str, Any]:
        """
        Retorna referências aos módulos especializados.
        
        Returns:
            Dict com instâncias dos módulos
        """
        return {
            'project_scanner': self.project_scanner,
            'structure_scanner': self.project_scanner.structure_scanner,
            'code_scanner': self.project_scanner.code_scanner,
            'file_scanner': self.project_scanner.file_scanner
        }
    
    def executar_diagnostico_completo(self) -> Dict[str, Any]:
        """
        Executa diagnóstico completo usando todos os módulos.
        
        Returns:
            Dict com diagnóstico abrangente
        """
        try:
            diagnostico = {
                "timestamp": self.project_scanner.get_scanner_status().get("timestamp"),
                "scanner_status": self.project_scanner.get_scanner_status(),
                "scan_light": self.project_scanner.scan_project_light(),
                "arquitetura": {
                    "modular": True,
                    "modulos_ativos": 4,
                    "project_scanner": "ProjectScanner",
                    "structure_scanner": "StructureScanner", 
                    "code_scanner": "CodeScanner",
                    "file_scanner": "FileScanner"
                },
                "capacidades": [
                    "Escaneamento completo de projeto",
                    "Descoberta automática de modelos",
                    "Análise de formulários e rotas",
                    "Manipulação de arquivos e templates",
                    "Busca avançada em código",
                    "Inspeção de banco de dados"
                ]
            }
            
            # Avaliar saúde geral
            scanner_status = diagnostico.get("scanner_status", {})
            if scanner_status.get("status") == "ready":
                diagnostico["saude_geral"] = "PRONTO"
            else:
                diagnostico["saude_geral"] = "INICIANDO"
            
            return diagnostico
            
        except Exception as e:
            logger.error(f"❌ Erro no diagnóstico completo: {e}")
            return {
                "erro": str(e),
                "timestamp": "N/A",
                "saude_geral": "ERRO"
            }
    
    def reset_scanner(self):
        """Reseta todos os dados do scanner"""
        if self._project_scanner:
            self._project_scanner.reset_scanner_data()
        
        # Limpar propriedades de compatibilidade
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        logger.info("🔄 Scanner resetado completamente")
    
    # ================================
    # MÉTODOS DE COMPATIBILIDADE
    # Para manter código existente funcionando
    # ================================
    
    def _discover_project_structure(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para structure_scanner"""
        return self.project_scanner.structure_scanner.discover_project_structure()
    
    def _discover_all_models(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para structure_scanner"""
        return self.project_scanner.structure_scanner.discover_all_models()
    
    def _discover_all_forms(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para code_scanner"""
        return self.project_scanner.code_scanner.discover_all_forms()
    
    def _discover_all_routes(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para code_scanner"""
        return self.project_scanner.code_scanner.discover_all_routes()
    
    def _discover_all_templates(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para file_scanner"""
        return self.project_scanner.file_scanner.discover_all_templates()
    
    def _generate_scan_summary(self) -> Dict[str, Any]:
        """Método de compatibilidade - delega para project_scanner"""
        return self.project_scanner._generate_scan_summary()
    
    def __str__(self) -> str:
        """Representação string do scanner"""
        return f"<ClaudeProjectScanner[MODULAR] app_path={self.app_path} modulos=4>"
    
    def __repr__(self) -> str:
        """Representação detalhada do scanner"""
        return self.__str__()


# ================================
# FUNÇÕES DE CONVENIÊNCIA GLOBAIS
# ================================

# Instância global para compatibilidade
project_scanner = None

def init_project_scanner_legacy(app_path: Optional[str] = None) -> ClaudeProjectScanner:
    """
    Inicializa o scanner de projeto (interface legacy).
    
    Args:
        app_path: Caminho raiz do projeto
        
    Returns:
        Instância do ClaudeProjectScanner
    """
    global project_scanner
    project_scanner = ClaudeProjectScanner(app_path)
    return project_scanner

def get_project_scanner_legacy() -> Optional[ClaudeProjectScanner]:
    """
    Obtém instância do scanner de projeto (interface legacy).
    
    Returns:
        Instância do ClaudeProjectScanner ou None
    """
    return project_scanner

# Aliases para compatibilidade com código existente
init_claude_project_scanner = init_project_scanner_legacy
get_claude_project_scanner = get_project_scanner_legacy

# ================================
# INICIALIZAÇÃO AUTOMÁTICA
# ================================

# Garantir que módulos estão disponíveis para import
__all__ = [
    'ClaudeProjectScanner',
    'init_project_scanner_legacy', 
    'get_project_scanner_legacy',
    'init_claude_project_scanner',
    'get_claude_project_scanner',
    'ProjectScanner',
    'StructureScanner', 
    'CodeScanner',
    'FileScanner'
]

logger.info("🔍 Sistema de Escaneamento Modular carregado com sucesso")
logger.info("📊 Arquitetura: 4 módulos especializados (ProjectScanner, StructureScanner, CodeScanner, FileScanner)")
logger.info("✅ Interface de compatibilidade mantida para código existente") 