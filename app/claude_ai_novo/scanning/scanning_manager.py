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
from app.claude_ai_novo.scanning.project_scanner import ProjectScanner, get_project_scanner, init_project_scanner
from app.claude_ai_novo.scanning.structure_scanner import StructureScanner, get_structure_scanner
from app.claude_ai_novo.scanning.code_scanner import CodeScanner, get_code_scanner
from app.claude_ai_novo.scanning.file_scanner import FileScanner, get_file_scanner
from app.claude_ai_novo.scanning.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ScanningManager:
    """
    Gerenciador unificado para o sistema de escaneamento de projeto.
    
    ARQUITETURA MODULAR - Coordena componentes especializados:
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
        
        # Lazy loading do DatabaseManager (OPERAÇÕES DE BANCO)
        self._database_manager = None
        
        # Para compatibilidade - propriedades herdadas
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        logger.info(f"🔍 ScanningManager inicializado com arquitetura modular: {self.app_path}")
    
    @property
    def project_scanner(self):
        """Lazy loading do ProjectScanner"""
        if self._project_scanner is None:
            self._project_scanner = init_project_scanner(str(self.app_path))
        return self._project_scanner
    
    @property
    def database_manager(self):
        """Lazy loading do DatabaseManager"""
        if self._database_manager is None:
            try:
                from app.claude_ai_novo.scanning.database_manager import DatabaseManager
                self._database_manager = DatabaseManager()
                logger.info("📊 DatabaseManager integrado ao ScanningManager")
            except ImportError as e:
                logger.warning(f"⚠️ DatabaseManager não disponível: {e}")
                self._database_manager = False  # Marcar como indisponível
        return self._database_manager if self._database_manager is not False else None
    
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
    
    def scan_database(self, operation: str = "list_tables", **kwargs) -> Dict[str, Any]:
        """Executa operações de banco usando DatabaseManager"""
        try:
            if not self.database_manager:
                return {
                    "error": "DatabaseManager não disponível",
                    "operation": operation,
                    "available": False
                }
            
            if operation == "list_tables":
                tables = self.database_manager.listar_tabelas()
                return {
                    "operation": "list_tables",
                    "tables": tables,
                    "count": len(tables),
                    "success": True
                }
            elif operation == "table_info":
                table_name = kwargs.get("table_name")
                if not table_name:
                    return {"error": "table_name não fornecido"}
                
                fields = self.database_manager.obter_campos_tabela(table_name)
                return {
                    "operation": "table_info",
                    "table": table_name,
                    "fields": fields,
                    "success": True
                }
            elif operation == "analyze_table":
                table_name = kwargs.get("table_name")
                if not table_name:
                    return {"error": "table_name não fornecido"}
                
                analysis = self.database_manager.analisar_tabela_completa(table_name)
                return {
                    "operation": "analyze_table",
                    "table": table_name,
                    "analysis": analysis,
                    "success": True
                }
            elif operation == "database_stats":
                stats = self.database_manager.obter_estatisticas_gerais()
                return {
                    "operation": "database_stats",
                    "statistics": stats,
                    "success": True
                }
            elif operation == "search_fields":
                field_type = kwargs.get("field_type")
                field_name = kwargs.get("field_name")
                
                if field_type:
                    results = self.database_manager.buscar_campos_por_tipo(field_type)
                elif field_name:
                    results = self.database_manager.buscar_campos_por_nome(field_name)
                else:
                    return {"error": "field_type ou field_name deve ser fornecido"}
                
                return {
                    "operation": "search_fields",
                    "results": results,
                    "count": len(results),
                    "success": True
                }
            else:
                return {
                    "error": f"Operação '{operation}' não suportada",
                    "supported_operations": [
                        "list_tables", "table_info", "analyze_table", 
                        "database_stats", "search_fields"
                    ]
                }
                
        except Exception as e:
            logger.error(f"❌ Erro na operação de banco {operation}: {e}")
            return {
                "error": str(e),
                "operation": operation,
                "success": False
            }
    
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
            'file_scanner': self.project_scanner.file_scanner,
            'database_manager': self.database_manager
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
                    "modulos_ativos": 5,
                    "project_scanner": "ProjectScanner",
                    "structure_scanner": "StructureScanner", 
                    "code_scanner": "CodeScanner",
                    "file_scanner": "FileScanner",
                    "database_manager": "DatabaseManager"
                },
                "capacidades": [
                    "Escaneamento completo de projeto",
                    "Descoberta automática de modelos",
                    "Análise de formulários e rotas",
                    "Manipulação de arquivos e templates",
                    "Busca avançada em código",
                    "Inspeção de banco de dados",
                    "Análise de tabelas e campos",
                    "Mapeamento de relacionamentos",
                    "Busca de campos por tipo/nome",
                    "Estatísticas de banco de dados"
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
    
    
    def get_database_info(self) -> Dict[str, Any]:
        """Obtém informações completas do banco de dados"""
        try:
            if not self.database_manager:
                self.database_manager = DatabaseManager()
                
            # Escanear estrutura do banco
            db_info = self.database_manager.scan_database_structure()
            
            # Adicionar metadados úteis
            if db_info and 'tables' in db_info:
                for table_name, table_info in db_info['tables'].items():
                    # Adicionar informações de índices
                    if 'indexes' not in table_info:
                        table_info['indexes'] = []
                    
                    # Adicionar informações de relacionamentos
                    if 'relationships' not in table_info:
                        table_info['relationships'] = []
                        
            logger.info(f"✅ Informações do banco obtidas: {len(db_info.get('tables', {}))} tabelas")
            return db_info
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter informações do banco: {e}")
            return {}
    def __str__(self) -> str:
        """Representação string do scanner"""
        return f"<ScanningManager[MODULAR] app_path={self.app_path} modulos=4>"
    
    def __repr__(self) -> str:
        """Representação detalhada do scanner"""
        return self.__str__()


# ================================
# FUNÇÕES DE CONVENIÊNCIA GLOBAIS
# ================================

# Instância global para compatibilidade
project_scanner = None

def init_project_scanner_legacy(app_path: Optional[str] = None) -> ScanningManager:
    """
    Inicializa o scanner de projeto (interface legacy).
    
    Args:
        app_path: Caminho raiz do projeto
        
    Returns:
        Instância do ScanningManager
    """
    global project_scanner
    project_scanner = ScanningManager(app_path)
    return project_scanner

def get_project_scanner_legacy() -> Optional[ScanningManager]:
    """
    Obtém instância do scanner de projeto (interface legacy).
    
    Returns:
        Instância do ScanningManager ou None
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
    'ScanningManager',
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
logger.info("📊 Arquitetura: 5 módulos especializados (ProjectScanner, StructureScanner, CodeScanner, FileScanner, DatabaseManager)")
logger.info("✅ Interface de compatibilidade mantida para código existente") 