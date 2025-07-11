"""
🔍 PROJECT SCANNER - Núcleo Principal
====================================

Núcleo central que coordena todo o escaneamento do projeto.
Orquestra os demais módulos especializados de scanner.

Responsabilidades:
- Coordenação principal do escaneamento
- Interface unificada
- Gestão do ciclo completo de descoberta
- Compilação de relatórios finais
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProjectScanner:
    """
    Núcleo central do sistema de escaneamento de projeto.
    
    Coordena todos os processos de descoberta e análise
    do projeto para dar autonomia total ao Claude AI.
    """
    
    def __init__(self, app_path: Optional[str] = None):
        """
        Inicializa o scanner de projeto.
        
        Args:
            app_path: Caminho raiz do projeto
        """
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        
        # Dados descobertos
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        # Inicializar scanners especializados (lazy loading)
        self._structure_scanner = None
        self._code_scanner = None
        self._file_scanner = None
        self._database_scanner = None
        
        logger.info(f"🔍 ProjectScanner inicializado: {self.app_path}")
    
    @property
    def structure_scanner(self):
        """Lazy loading do StructureScanner"""
        if self._structure_scanner is None:
            from app.claude_ai_novo.scanning.structure_scanner import get_structure_scanner
            self._structure_scanner = get_structure_scanner(self.app_path)
        return self._structure_scanner
    
    @property
    def code_scanner(self):
        """Lazy loading do CodeScanner"""
        if self._code_scanner is None:
            from app.claude_ai_novo.scanning.code_scanner import get_code_scanner
            self._code_scanner = get_code_scanner(self.app_path)
        return self._code_scanner
    
    @property
    def file_scanner(self):
        """Lazy loading do FileScanner"""
        if self._file_scanner is None:
            from app.claude_ai_novo.scanning.file_scanner import get_file_scanner
            self._file_scanner = get_file_scanner(self.app_path)
        return self._file_scanner
    
    @property
    def database_scanner(self):
        """Lazy loading do DatabaseScanner"""
        if self._database_scanner is None:
            from app.claude_ai_novo.scanning.database_scanner import get_database_scanner
            self._database_scanner = get_database_scanner()
        return self._database_scanner
    
    def scan_complete_project(self) -> Dict[str, Any]:
        """
        ESCANEAMENTO COMPLETO DO PROJETO (método principal).
        
        Descobre TUDO dinamicamente: módulos, models, forms, routes, templates, banco.
        
        Returns:
            Dict com mapeamento completo do projeto
        """
        try:
            logger.info("🚀 INICIANDO ESCANEAMENTO COMPLETO DO PROJETO")
            
            # 1. 📁 DESCOBRIR ESTRUTURA DE PASTAS
            self.project_structure = self.structure_scanner.discover_project_structure()
            
            # 2. 🗃️ DESCOBRIR TODOS OS MODELOS DINAMICAMENTE
            self.discovered_models = self.structure_scanner.discover_all_models()
            
            # 3. 📝 DESCOBRIR TODOS OS FORMULÁRIOS
            self.discovered_forms = self.code_scanner.discover_all_forms()
            
            # 4. 🌐 DESCOBRIR TODAS AS ROTAS
            self.discovered_routes = self.code_scanner.discover_all_routes()
            
            # 5. 🎨 DESCOBRIR TODOS OS TEMPLATES
            self.discovered_templates = self.file_scanner.discover_all_templates()
            
            # 6. 🗄️ DESCOBRIR ESQUEMA COMPLETO DO BANCO
            self.database_schema = self.database_scanner.discover_database_schema()
            
            # 7. 📊 COMPILAR RELATÓRIO COMPLETO
            complete_map = {
                'project_structure': self.project_structure,
                'models': self.discovered_models,
                'forms': self.discovered_forms,
                'routes': self.discovered_routes,
                'templates': self.discovered_templates,
                'database_schema': self.database_schema,
                'scan_summary': self._generate_scan_summary(),
                'scan_metadata': self._generate_scan_metadata()
            }
            
            logger.info("✅ ESCANEAMENTO COMPLETO FINALIZADO")
            return complete_map
            
        except Exception as e:
            logger.error(f"❌ Erro no escaneamento completo: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'partial_data': self._get_partial_scan_data()
            }
    
    def scan_project_light(self) -> Dict[str, Any]:
        """
        Escaneamento rápido com informações essenciais.
        
        Returns:
            Dict com informações básicas do projeto
        """
        try:
            logger.info("⚡ INICIANDO ESCANEAMENTO RÁPIDO")
            
            light_scan = {
                'project_structure': self.structure_scanner.discover_project_structure(),
                'models_count': len(self.structure_scanner.discover_all_models()),
                'templates_count': len(self.file_scanner.discover_all_templates()),
                'scan_summary': self._generate_light_summary(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("⚡ ESCANEAMENTO RÁPIDO FINALIZADO")
            return light_scan
            
        except Exception as e:
            logger.error(f"❌ Erro no escaneamento rápido: {e}")
            return {'error': str(e)}
    
    def _generate_scan_summary(self) -> Dict[str, Any]:
        """
        Gera resumo completo do escaneamento.
        
        Returns:
            Dict com estatísticas do scan
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'project_root': str(self.app_path),
            'totals': {
                'modules': len([d for d in self.project_structure.keys() 
                               if 'python_files' in self.project_structure.get(d, {}) 
                               and self.project_structure[d].get('python_files', [])]),
                'models': len(self.discovered_models),
                'forms': len(self.discovered_forms),
                'routes': sum(route_info.get('total_routes', 0) 
                             for route_info in self.discovered_routes.values()),
                'templates': len(self.discovered_templates),
                'database_tables': len(self.database_schema.get('tables', {}))
            },
            'quality_metrics': self._calculate_quality_metrics(),
            'recommendations': self._generate_recommendations()
        }
    
    def _generate_light_summary(self) -> Dict[str, Any]:
        """Gera resumo rápido do escaneamento"""
        return {
            'timestamp': datetime.now().isoformat(),
            'project_root': str(self.app_path),
            'scan_type': 'light',
            'directories_found': len(self.project_structure),
            'status': 'completed'
        }
    
    def _generate_scan_metadata(self) -> Dict[str, Any]:
        """
        Gera metadados do escaneamento.
        
        Returns:
            Dict com metadados detalhados
        """
        return {
            'scanner_version': '1.0.0',
            'scan_date': datetime.now().isoformat(),
            'modules_loaded': {
                'structure_scanner': self._structure_scanner is not None,
                'code_scanner': self._code_scanner is not None,
                'file_scanner': self._file_scanner is not None,
                'database_scanner': self._database_scanner is not None
            },
            'scan_depth': 'complete',
            'project_path': str(self.app_path),
            'python_version': os.sys.version
        }
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """
        Calcula métricas de qualidade do projeto.
        
        Returns:
            Dict com métricas de qualidade
        """
        metrics = {
            'models_with_relationships': 0,
            'forms_count': len(self.discovered_forms),
            'routes_count': 0,
            'templates_with_variables': 0,
            'code_organization_score': 0
        }
        
        try:
            # Contar modelos com relacionamentos
            for model_info in self.discovered_models.values():
                if model_info.get('foreign_keys') or model_info.get('relationships'):
                    metrics['models_with_relationships'] += 1
            
            # Contar rotas totais
            metrics['routes_count'] = sum(
                route_info.get('total_routes', 0) 
                for route_info in self.discovered_routes.values()
            )
            
            # Contar templates com variáveis
            for template_info in self.discovered_templates.values():
                if template_info.get('template_vars'):
                    metrics['templates_with_variables'] += 1
            
            # Score de organização (baseado na estrutura)
            total_modules = len(self.project_structure)
            modules_with_models = len([m for m in self.discovered_models.values() 
                                     if m.get('source', '').startswith('models_file')])
            
            if total_modules > 0:
                metrics['code_organization_score'] = int(round(
                    (modules_with_models / total_modules) * 100, 0
                ))
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao calcular métricas: {e}")
        
        return metrics
    
    def _generate_recommendations(self) -> List[str]:
        """
        Gera recomendações baseadas no scan.
        
        Returns:
            Lista de recomendações
        """
        recommendations = []
        
        try:
            # Recomendações baseadas em modelos
            if len(self.discovered_models) == 0:
                recommendations.append("📦 Nenhum modelo encontrado - considere criar modelos de dados")
            
            # Recomendações baseadas em templates
            if len(self.discovered_templates) == 0:
                recommendations.append("🎨 Nenhum template encontrado - adicione templates HTML")
            
            # Recomendações baseadas em rotas
            total_routes = sum(route_info.get('total_routes', 0) 
                              for route_info in self.discovered_routes.values())
            if total_routes == 0:
                recommendations.append("🌐 Nenhuma rota encontrada - adicione endpoints")
            
            # Recomendações baseadas na organização
            if len(self.project_structure) < 3:
                recommendations.append("📁 Estrutura muito simples - considere modularizar")
            
            # Recomendações baseadas no banco
            if not self.database_schema.get('tables'):
                recommendations.append("🗄️ Banco de dados vazio - execute migrações")
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar recomendações: {e}")
        
        return recommendations
    
    def _get_partial_scan_data(self) -> Dict[str, Any]:
        """
        Obtém dados parciais em caso de erro.
        
        Returns:
            Dict com dados parciais disponíveis
        """
        return {
            'project_structure': self.project_structure,
            'discovered_models': self.discovered_models,
            'discovered_forms': self.discovered_forms,
            'discovered_routes': self.discovered_routes,
            'discovered_templates': self.discovered_templates,
            'database_schema': self.database_schema
        }
    
    def get_scanner_status(self) -> Dict[str, Any]:
        """
        Obtém status atual do scanner.
        
        Returns:
            Dict com status do scanner
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'app_path': str(self.app_path),
            'modules_loaded': {
                'structure_scanner': self._structure_scanner is not None,
                'code_scanner': self._code_scanner is not None,
                'file_scanner': self._file_scanner is not None,
                'database_scanner': self._database_scanner is not None
            },
            'data_available': {
                'project_structure': bool(self.project_structure),
                'models': bool(self.discovered_models),
                'forms': bool(self.discovered_forms),
                'routes': bool(self.discovered_routes),
                'templates': bool(self.discovered_templates),
                'database_schema': bool(self.database_schema)
            },
            'status': 'ready'
        }
    
    def reset_scanner_data(self):
        """Limpa todos os dados descobertos"""
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        logger.info("🔄 Dados do scanner limpos")


# Singleton para uso global
_project_scanner = None

def get_project_scanner() -> ProjectScanner:
    """
    Obtém instância única do scanner de projeto.
    
    Returns:
        Instância do ProjectScanner
    """
    global _project_scanner
    if _project_scanner is None:
        _project_scanner = ProjectScanner()
    return _project_scanner

def init_project_scanner(app_path: Optional[str] = None) -> ProjectScanner:
    """
    Inicializa o scanner de projeto.
    
    Args:
        app_path: Caminho raiz do projeto
        
    Returns:
        Instância do ProjectScanner
    """
    global _project_scanner
    _project_scanner = ProjectScanner(app_path)
    return _project_scanner

# Alias para compatibilidade
ClaudeProjectScanner = ProjectScanner
project_scanner = None

def init_claude_project_scanner(app_path: Optional[str] = None) -> ProjectScanner:
    """Alias para compatibilidade"""
    return init_project_scanner(app_path) 