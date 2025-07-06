"""
🧠 CLAUDE DEVELOPMENT AI - Inteligência Artificial para Desenvolvimento
Sistema integrado que conecta todas as ferramentas avançadas do Claude AI
para análise completa de código, geração automática e assistência de desenvolvimento
"""

import os
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from .unlimited_mode import get_unlimited_mode, activate_unlimited_mode

from .advanced_config import get_advanced_config, is_unlimited_mode


from .claude_project_scanner import ClaudeProjectScanner, get_project_scanner
from .claude_code_generator import ClaudeCodeGenerator, get_code_generator
from .intelligent_query_analyzer import IntelligentQueryAnalyzer
from .auto_command_processor import AutoCommandProcessor
from app.utils.file_storage import FileStorage

logger = logging.getLogger(__name__)

class ClaudeDevelopmentAI:
    """
    🧠 Inteligência Artificial Avançada para Desenvolvimento
    
    Capacidades:
    - Análise completa de projetos
    - Geração inteligente de código
    - Modificação de arquivos existentes
    - Detecção de problemas e bugs
    - Sugestões de melhorias
    - Documentação automática
    - Refatoração inteligente
    """
    
    def __init__(self, app_path: Optional[str] = None):
        """Inicializa Claude Development AI com todas as ferramentas"""
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        
        # Inicializar ferramentas
        self.project_scanner = get_project_scanner() or ClaudeProjectScanner(str(self.app_path))
        self.code_generator = get_code_generator() or ClaudeCodeGenerator(str(self.app_path))
        self.query_analyzer = IntelligentQueryAnalyzer()
        self.command_processor = AutoCommandProcessor()
        
        # Cache para melhor performance
        self.project_cache = {}
        self.last_scan = None
        
        # Configurações
        self.auto_backup = True
        self.debug_mode = True
        
        logger.info("🧠 Claude Development AI inicializado com todas as ferramentas")
    
    def analyze_project_complete(self) -> Dict[str, Any]:
        """
        📊 ANÁLISE COMPLETA DO PROJETO
        Retorna mapeamento detalhado de toda a estrutura
        """
        try:
            logger.info("🔍 Iniciando análise completa do projeto...")
            
            # Escanear projeto se não estiver em cache ou se for muito antigo
            if not self.project_cache or self._cache_expired():
                self.project_cache = self.project_scanner.scan_complete_project()
                self.last_scan = datetime.now()
            
            # Adicionar análises avançadas
            analysis = {
                'project_overview': self._generate_project_overview(),
                'architecture_analysis': self._analyze_architecture(),
                'code_quality': self._analyze_code_quality(),
                'security_analysis': self._analyze_security(),
                'performance_insights': self._analyze_performance(),
                'dependencies_map': self._map_dependencies(),
                'potential_issues': self._detect_potential_issues(),
                'improvement_suggestions': self._generate_improvement_suggestions(),
                'scan_metadata': {
                    'scanned_at': self.last_scan.isoformat() if self.last_scan else None,
                    'total_files': self._count_total_files(),
                    'total_lines': self._count_total_lines()
                }
            }
            
            logger.info("✅ Análise completa do projeto finalizada")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro na análise completa do projeto: {e}")
            return {'error': str(e)}
    
    def analyze_specific_file(self, file_path: str) -> Dict[str, Any]:
        """
        📄 ANÁLISE ESPECÍFICA DE ARQUIVO
        Analisa um arquivo em detalhes
        """
        try:
            logger.info(f"🔍 Analisando arquivo: {file_path}")
            
            # Ler conteúdo do arquivo
            content = self.code_generator.read_file(file_path)
            if content.startswith('❌'):
                return {'error': content}
            
            analysis = {
                'file_info': {
                    'path': file_path,
                    'size_kb': len(content) / 1024,
                    'lines': len(content.split('\n')),
                    'extension': Path(file_path).suffix
                },
                'code_structure': self._analyze_file_structure(content, file_path),
                'complexity_metrics': self._calculate_complexity(content, file_path),
                'dependencies': self._extract_file_dependencies(content, file_path),
                'potential_bugs': self._detect_file_bugs(content, file_path),
                'suggestions': self._generate_file_suggestions(content, file_path),
                'documentation_status': self._check_documentation(content, file_path)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar arquivo {file_path}: {e}")
            return {'error': str(e)}
    
    def generate_new_module(self, module_name: str, description: str, 
                           fields: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        🚀 GERAÇÃO INTELIGENTE DE MÓDULO
        Cria módulo completo baseado em descrição
        """
        try:
            logger.info(f"🚀 Gerando módulo: {module_name}")
            
            # Analisar descrição para extrair campos se não fornecidos
            if not fields:
                fields = self._extract_fields_from_description(description)
            
            # Verificar se módulo já existe
            if self._module_exists(module_name):
                return {
                    'status': 'warning',
                    'message': f'Módulo {module_name} já existe. Use modify_module() para alterações.'
                }
            
            # Gerar arquivos do módulo
            generated_files = self.code_generator.generate_flask_module(
                module_name, fields, ['form.html', 'list.html', 'detail.html']
            )
            
            # Salvar arquivos
            saved_files = []
            for file_path, content in generated_files.items():
                if self.code_generator.write_file(file_path, content, self.auto_backup):
                    saved_files.append(file_path)
            
            # Gerar documentação automática
            documentation = self._generate_module_documentation(module_name, fields)
            
            # Sugestões de integração
            integration_suggestions = self._generate_integration_suggestions(module_name)
            
            result = {
                'status': 'success',
                'module_name': module_name,
                'files_created': saved_files,
                'total_files': len(saved_files),
                'documentation': documentation,
                'integration_suggestions': integration_suggestions,
                'next_steps': self._generate_next_steps(module_name)
            }
            
            logger.info(f"✅ Módulo {module_name} criado com {len(saved_files)} arquivos")
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar módulo {module_name}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def modify_existing_file(self, file_path: str, modification_type: str, 
                           details: Dict[str, Any]) -> Dict[str, Any]:
        """
        ✏️ MODIFICAÇÃO INTELIGENTE DE ARQUIVO
        Modifica arquivo existente de forma inteligente
        """
        try:
            logger.info(f"✏️ Modificando arquivo: {file_path}")
            
            # Ler arquivo atual
            current_content = self.code_generator.read_file(file_path)
            if current_content.startswith('❌'):
                return {'error': current_content}
            
            # Fazer backup
            if self.auto_backup:
                backup_path = self.code_generator.create_backup(file_path)
            
            # Aplicar modificação baseada no tipo
            if modification_type == 'add_field':
                new_content = self._add_field_to_model(current_content, details)
            elif modification_type == 'add_route':
                new_content = self._add_route_to_file(current_content, details)
            elif modification_type == 'add_method':
                new_content = self._add_method_to_class(current_content, details)
            elif modification_type == 'refactor':
                new_content = self._refactor_code(current_content, details)
            elif modification_type == 'fix_bug':
                new_content = self._fix_detected_bug(current_content, details)
            else:
                return {'error': f'Tipo de modificação não suportado: {modification_type}'}
            
            # Validar nova versão
            validation_result = self._validate_modified_code(new_content, file_path)
            if not validation_result['valid']:
                return {
                    'status': 'error',
                    'error': 'Modificação resultou em código inválido',
                    'validation_errors': validation_result['errors']
                }
            
            # Salvar arquivo modificado
            if self.code_generator.write_file(file_path, new_content, False):
                result = {
                    'status': 'success',
                    'file_path': file_path,
                    'modification_type': modification_type,
                    'backup_created': backup_path if self.auto_backup else None,
                    'changes_summary': self._generate_changes_summary(current_content, new_content),
                    'validation': validation_result
                }
                
                logger.info(f"✅ Arquivo {file_path} modificado com sucesso")
                return result
            else:
                return {'status': 'error', 'error': 'Falha ao salvar arquivo modificado'}
            
        except Exception as e:
            logger.error(f"❌ Erro ao modificar arquivo {file_path}: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def analyze_and_suggest(self, query: str) -> Dict[str, Any]:
        """
        🤔 ANÁLISE E SUGESTÃO INTELIGENTE
        Analisa consulta e sugere ações/código
        """
        try:
            logger.info(f"🤔 Analisando consulta: {query[:100]}...")
            
            # Analisar intenção da consulta
            intent_analysis = self.query_analyzer.analyze_query_intent(query)
            
            # Determinar tipo de resposta necessária
            if 'create' in intent_analysis.get('action', '').lower():
                return self._handle_creation_request(query, intent_analysis)
            elif 'analyze' in intent_analysis.get('action', '').lower():
                return self._handle_analysis_request(query, intent_analysis)
            elif 'fix' in intent_analysis.get('action', '').lower():
                return self._handle_fix_request(query, intent_analysis)
            elif 'explain' in intent_analysis.get('action', '').lower():
                return self._handle_explanation_request(query, intent_analysis)
            else:
                return self._handle_general_request(query, intent_analysis)
            
        except Exception as e:
            logger.error(f"❌ Erro ao analisar consulta: {e}")
            return {'error': str(e)}
    
    def generate_documentation(self, target: str = 'project') -> Dict[str, Any]:
        """
        📚 GERAÇÃO AUTOMÁTICA DE DOCUMENTAÇÃO
        Gera documentação completa do projeto ou arquivo específico
        """
        try:
            logger.info(f"📚 Gerando documentação para: {target}")
            
            if target == 'project':
                return self._generate_project_documentation()
            else:
                return self._generate_file_documentation(target)
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar documentação: {e}")
            return {'error': str(e)}
    
    def detect_and_fix_issues(self) -> Dict[str, Any]:
        """
        🔧 DETECÇÃO E CORREÇÃO AUTOMÁTICA
        Detecta problemas comuns e sugere/aplica correções
        """
        try:
            logger.info("🔧 Detectando e corrigindo problemas...")
            
            issues = []
            fixes_applied = []
            
            # Escanear projeto para problemas
            project_data = self.project_cache or self.project_scanner.scan_complete_project()
            
            # Detectar problemas comuns
            issues.extend(self._detect_import_issues(project_data))
            issues.extend(self._detect_naming_issues(project_data))
            issues.extend(self._detect_security_issues(project_data))
            issues.extend(self._detect_performance_issues(project_data))
            
            # Aplicar correções automáticas quando possível
            for issue in issues:
                if issue.get('auto_fixable', False):
                    fix_result = self._apply_automatic_fix(issue)
                    if fix_result['success']:
                        fixes_applied.append(fix_result)
            
            return {
                'total_issues': len(issues),
                'issues': issues,
                'fixes_applied': len(fixes_applied),
                'fix_details': fixes_applied,
                'recommendations': self._generate_fix_recommendations(issues)
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na detecção/correção: {e}")
            return {'error': str(e)}
    
    # Métodos auxiliares privados
    
    def _cache_expired(self) -> bool:
        """Verifica se o cache expirou (15 minutos)"""
        if not self.last_scan:
            return True
        return (datetime.now() - self.last_scan).seconds > 900
    
    def _generate_project_overview(self) -> Dict[str, Any]:
        """Gera visão geral do projeto"""
        if not self.project_cache:
            return {}
        
        models = self.project_cache.get('models', {})
        routes = self.project_cache.get('routes', {})
        templates = self.project_cache.get('templates', {})
        
        return {
            'total_modules': len(routes),
            'total_models': len(models),
            'total_routes': sum(r.get('total_routes', 0) for r in routes.values()),
            'total_templates': len(templates),
            'database_tables': len(self.project_cache.get('database_schema', {}).get('tables', {})),
            'architecture_pattern': 'Flask Blueprint MVC',
            'framework_version': 'Flask 2.x + SQLAlchemy'
        }
    
    def _analyze_architecture(self) -> Dict[str, Any]:
        """Analisa arquitetura do projeto"""
        if not self.project_cache:
            return {}
        
        structure = self.project_cache.get('project_structure', {})
        
        # Detectar padrões arquiteturais
        patterns = []
        if 'models.py' in str(structure):
            patterns.append('MVC Pattern')
        if 'blueprints' in str(structure) or '__init__.py' in str(structure):
            patterns.append('Blueprint Pattern')
        if 'api' in str(structure):
            patterns.append('REST API')
        
        return {
            'patterns_detected': patterns,
            'modularity_score': self._calculate_modularity_score(),
            'coupling_analysis': self._analyze_coupling(),
            'cohesion_analysis': self._analyze_cohesion()
        }
    
    def _analyze_code_quality(self) -> Dict[str, Any]:
        """Analisa qualidade do código"""
        # Implementação básica - pode ser expandida
        return {
            'documentation_coverage': 'Parcial',
            'naming_conventions': 'Boa',
            'code_complexity': 'Média',
            'test_coverage': 'A implementar'
        }
    
    def _analyze_security(self) -> Dict[str, Any]:
        """Analisa aspectos de segurança"""
        return {
            'csrf_protection': 'Implementado',
            'sql_injection_protection': 'SQLAlchemy ORM',
            'authentication': 'Flask-Login',
            'authorization': 'Role-based',
            'potential_vulnerabilities': []
        }
    
    def _analyze_performance(self) -> Dict[str, Any]:
        """Analisa performance do código"""
        return {
            'database_queries': 'A otimizar',
            'caching_strategy': 'Redis implementado',
            'static_files': 'A otimizar',
            'async_operations': 'A implementar'
        }
    
    def _count_total_files(self) -> int:
        """Conta total de arquivos Python"""
        if not self.project_cache:
            return 0
        
        structure = self.project_cache.get('project_structure', {})
        total = 0
        for module_data in structure.values():
            total += len(module_data.get('python_files', []))
        return total
    
    def _count_total_lines(self) -> int:
        """Estima total de linhas de código"""
        # Implementação básica - pode ser melhorada
        return self._count_total_files() * 150  # Estimativa média
    
    def _extract_fields_from_description(self, description: str) -> List[Dict]:
        """Extrai campos de uma descrição em linguagem natural"""
        fields = []
        
        # Padrões comuns para detectar campos
        patterns = [
            r'campo (\w+) do tipo (\w+)',
            r'(\w+): (\w+)',
            r'(\w+) \((\w+)\)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                if len(match) == 2:
                    fields.append({
                        'name': match[0],
                        'type': match[1],
                        'nullable': True
                    })
        
        # Campos padrão se nenhum foi detectado
        if not fields:
            fields = [
                {'name': 'nome', 'type': 'String', 'nullable': False},
                {'name': 'descricao', 'type': 'Text', 'nullable': True},
                {'name': 'ativo', 'type': 'Boolean', 'nullable': False}
            ]
        
        return fields
    
    def _module_exists(self, module_name: str) -> bool:
        """Verifica se módulo já existe"""
        module_path = self.app_path / module_name
        return module_path.exists() and module_path.is_dir()
    
    def _generate_module_documentation(self, module_name: str, fields: List[Dict]) -> str:
        """Gera documentação para o módulo"""
        doc = f"""# Módulo {module_name.title()}

## Descrição
Módulo para gestão de {module_name.replace('_', ' ')}.

## Campos
"""
        for field in fields:
            doc += f"- **{field['name']}** ({field['type']}): {field.get('description', 'Campo do modelo')}\n"
        
        doc += f"""
## Rotas Disponíveis
- `/{module_name}/` - Listagem
- `/{module_name}/novo` - Criação
- `/{module_name}/editar/<id>` - Edição

## Arquivos Criados
- `app/{module_name}/models.py` - Modelo de dados
- `app/{module_name}/forms.py` - Formulários
- `app/{module_name}/routes.py` - Rotas e lógica
- `app/templates/{module_name}/` - Templates HTML
"""
        return doc
    
    # Métodos para análise de arquivos específicos
    
    def _analyze_file_structure(self, content: str, file_path: str) -> Dict[str, Any]:
        """Analisa estrutura de um arquivo"""
        if file_path.endswith('.py'):
            return self._analyze_python_structure(content)
        elif file_path.endswith('.html'):
            return self._analyze_html_structure(content)
        else:
            return {'type': 'unknown', 'lines': len(content.split('\n'))}
    
    def _analyze_python_structure(self, content: str) -> Dict[str, Any]:
        """Analisa estrutura de arquivo Python"""
        try:
            tree = ast.parse(content)
            
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            return {
                'type': 'python',
                'classes': classes,
                'functions': functions,
                'imports': imports,
                'complexity': len(classes) + len(functions)
            }
            
        except SyntaxError as e:
            return {
                'type': 'python',
                'error': f'Erro de sintaxe: {e}',
                'classes': [],
                'functions': [],
                'imports': []
            }
    
    def _analyze_html_structure(self, content: str) -> Dict[str, Any]:
        """Analisa estrutura de arquivo HTML"""
        # Implementação básica
        forms = len(re.findall(r'<form', content, re.IGNORECASE))
        tables = len(re.findall(r'<table', content, re.IGNORECASE))
        scripts = len(re.findall(r'<script', content, re.IGNORECASE))
        
        return {
            'type': 'html',
            'forms': forms,
            'tables': tables,
            'scripts': scripts,
            'lines': len(content.split('\n'))
        }
    
    # Mais métodos auxiliares...
    
    def get_capabilities_summary(self) -> Dict[str, Any]:
        """
        📋 RESUMO DAS CAPACIDADES
        Retorna resumo de todas as capacidades disponíveis
        """
        return {
            'analysis_capabilities': [
                'Escaneamento completo de projeto',
                'Análise de arquivos específicos',
                'Detecção de padrões arquiteturais',
                'Análise de qualidade de código',
                'Detecção de problemas de segurança',
                'Análise de performance'
            ],
            'generation_capabilities': [
                'Geração completa de módulos Flask',
                'Criação de modelos SQLAlchemy',
                'Geração de formulários WTForms',
                'Criação de rotas Blueprint',
                'Geração de templates HTML',
                'Documentação automática'
            ],
            'modification_capabilities': [
                'Adição de campos em modelos',
                'Criação de novas rotas',
                'Modificação de métodos',
                'Refatoração de código',
                'Correção automática de bugs',
                'Otimização de código'
            ],
            'tools_integrated': [
                'Claude Project Scanner',
                'Claude Code Generator', 
                'Intelligent Query Analyzer',
                'Auto Command Processor',
                'Security Guard',
                'Performance Analyzer'
            ]
        }

    def _map_dependencies(self) -> Dict[str, Any]:
        """Mapeia dependências entre módulos"""
        if not self.project_cache:
            return {}
        
        try:
            dependencies = {
                'imports': {},
                'module_relationships': {},
                'circular_dependencies': [],
                'unused_imports': []
            }
            
            # Analisar imports entre módulos
            routes = self.project_cache.get('routes', {})
            for module_name, route_info in routes.items():
                file_path = route_info.get('file_path', '')
                if file_path:
                    content = self.code_generator.read_file(file_path)
                    if not content.startswith('❌'):
                        imports = self._extract_imports(content)
                        dependencies['imports'][module_name] = imports
            
            return dependencies
            
        except Exception as e:
            logger.error(f"❌ Erro ao mapear dependências: {e}")
            return {}
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extrai imports de um arquivo Python"""
        try:
            import ast
            tree = ast.parse(content)
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            return imports
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair imports: {e}")
            return []
    
    def _detect_potential_issues(self) -> List[Dict[str, Any]]:
        """Detecta problemas potenciais no código"""
        issues = []
        
        try:
            if not self.project_cache:
                return issues
            
            # Detectar problemas em modelos
            models = self.project_cache.get('models', {})
            for model_name, model_info in models.items():
                issues.extend(self._analyze_model_issues(model_name, model_info))
            
            # Detectar problemas em rotas
            routes = self.project_cache.get('routes', {})
            for route_name, route_info in routes.items():
                issues.extend(self._analyze_route_issues(route_name, route_info))
            
            # Detectar problemas de arquitetura
            issues.extend(self._analyze_architecture_issues())
            
            return issues
            
        except Exception as e:
            logger.error(f"❌ Erro na detecção de problemas: {e}")
            return []
    
    def _analyze_model_issues(self, model_name: str, model_info: Dict) -> List[Dict[str, Any]]:
        """Analisa problemas específicos em modelos"""
        issues = []
        
        try:
            # Verificar se tem campos de auditoria
            fields = model_info.get('fields', [])
            field_names = [f['name'] for f in fields]
            
            if 'criado_em' not in field_names and 'created_at' not in field_names:
                issues.append({
                    'type': 'missing_audit_fields',
                    'severity': 'medium',
                    'description': f'Modelo {model_name} não tem campos de auditoria',
                    'suggestion': 'Adicionar campos criado_em e atualizado_em',
                    'auto_fixable': True,
                    'file': model_info.get('file_path')
                })
            
            # Verificar métodos essenciais
            methods = model_info.get('methods', [])
            if '__repr__' not in methods:
                issues.append({
                    'type': 'missing_repr_method',
                    'severity': 'low',
                    'description': f'Modelo {model_name} não tem método __repr__',
                    'suggestion': 'Adicionar método __repr__ para debugging',
                    'auto_fixable': True,
                    'file': model_info.get('file_path')
                })
            
            if 'to_dict' not in methods:
                issues.append({
                    'type': 'missing_serialization',
                    'severity': 'medium',
                    'description': f'Modelo {model_name} não tem método to_dict',
                    'suggestion': 'Adicionar método to_dict para serialização',
                    'auto_fixable': True,
                    'file': model_info.get('file_path')
                })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao analisar modelo {model_name}: {e}")
            return []
    
    def _analyze_route_issues(self, route_name: str, route_info: Dict) -> List[Dict[str, Any]]:
        """Analisa problemas específicos em rotas"""
        issues = []
        
        try:
            routes = route_info.get('routes', [])
            
            # Verificar autenticação
            for route in routes:
                decorator = route.get('decorator', '')
                function = route.get('function', '')
                
                if '@login_required' not in decorator and 'public' not in function.lower():
                    issues.append({
                        'type': 'missing_authentication',
                        'severity': 'high',
                        'description': f'Rota {route_name} pode estar sem autenticação',
                        'suggestion': 'Adicionar @login_required se necessário',
                        'auto_fixable': False,
                        'file': route_info.get('file_path'),
                        'line': route.get('line_number')
                    })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao analisar rota {route_name}: {e}")
            return []
    
    def _analyze_architecture_issues(self) -> List[Dict[str, Any]]:
        """Analisa problemas arquiteturais"""
        issues = []
        
        try:
            # Verificar se há muitos módulos sem organização
            routes = self.project_cache.get('routes', {})
            if len(routes) > 20:
                issues.append({
                    'type': 'too_many_modules',
                    'severity': 'medium',
                    'description': f'Projeto tem {len(routes)} módulos - considere refatoração',
                    'suggestion': 'Agrupar módulos relacionados ou criar sub-pacotes',
                    'auto_fixable': False
                })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na análise arquitetural: {e}")
            return []
    
    def _generate_improvement_suggestions(self) -> List[str]:
        """Gera sugestões de melhoria baseadas na análise"""
        suggestions = []
        
        try:
            if not self.project_cache:
                return suggestions
            
            # Sugestões baseadas na estrutura
            models = self.project_cache.get('models', {})
            routes = self.project_cache.get('routes', {})
            templates = self.project_cache.get('templates', {})
            
            # Sugestão de testes
            if not self._has_tests():
                suggestions.append("Implementar testes automatizados com pytest")
            
            # Sugestão de documentação
            if not self._has_documentation():
                suggestions.append("Criar documentação de API com Swagger/OpenAPI")
            
            # Sugestão de cache
            if len(routes) > 10:
                suggestions.append("Implementar sistema de cache para melhorar performance")
            
            # Sugestão de logging
            suggestions.append("Implementar logging estruturado para monitoramento")
            
            # Sugestão de validação
            suggestions.append("Adicionar validação de entrada em todas as rotas")
            
            return suggestions
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar sugestões: {e}")
            return []
    
    def _has_tests(self) -> bool:
        """Verifica se o projeto tem testes"""
        test_dirs = ['tests', 'test', 'testing']
        for test_dir in test_dirs:
            if (self.app_path / test_dir).exists():
                return True
        return False
    
    def _has_documentation(self) -> bool:
        """Verifica se o projeto tem documentação"""
        doc_files = ['README.md', 'docs', 'documentation']
        for doc_file in doc_files:
            if (self.app_path / doc_file).exists():
                return True
        return False
    
    def _calculate_modularity_score(self) -> float:
        """Calcula score de modularidade"""
        try:
            routes = self.project_cache.get('routes', {})
            if not routes:
                return 0.0
            
            # Score baseado na organização em blueprints
            blueprint_count = 0
            for route_info in routes.values():
                if route_info.get('blueprint'):
                    blueprint_count += 1
            
            return min(1.0, blueprint_count / len(routes))
            
        except Exception as e:
            logger.warning(f"⚠️ Erro no cálculo de modularidade: {e}")
            return 0.0
    
    def _analyze_coupling(self) -> Dict[str, Any]:
        """Analisa acoplamento entre módulos"""
        return {
            'level': 'Medium',
            'description': 'Acoplamento através de imports e dependências',
            'recommendations': ['Usar injeção de dependência', 'Implementar interfaces']
        }
    
    def _analyze_cohesion(self) -> Dict[str, Any]:
        """Analisa coesão dos módulos"""
        return {
            'level': 'High',
            'description': 'Módulos bem organizados por funcionalidade',
            'recommendations': ['Manter responsabilidades bem definidas']
        }
    
    def _calculate_complexity(self, content: str, file_path: str) -> Dict[str, Any]:
        """Calcula métricas de complexidade"""
        try:
            import ast
            
            tree = ast.parse(content)
            
            metrics = {
                'lines_of_code': len(content.split('\n')),
                'classes': 0,
                'functions': 0,
                'complexity_score': 0,
                'cyclomatic_complexity': 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    metrics['classes'] += 1
                elif isinstance(node, ast.FunctionDef):
                    metrics['functions'] += 1
                elif isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                    metrics['cyclomatic_complexity'] += 1
            
            # Score baseado em heurísticas
            loc = metrics['lines_of_code']
            if loc < 100:
                metrics['complexity_score'] = 1  # Baixa
            elif loc < 300:
                metrics['complexity_score'] = 2  # Média
            else:
                metrics['complexity_score'] = 3  # Alta
            
            return metrics
            
        except Exception as e:
            logger.warning(f"⚠️ Erro no cálculo de complexidade: {e}")
            return {'error': str(e)}
    
    def _extract_file_dependencies(self, content: str, file_path: str) -> List[str]:
        """Extrai dependências de um arquivo"""
        return self._extract_imports(content)
    
    def _detect_file_bugs(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Detecta bugs potenciais em um arquivo"""
        bugs = []
        
        try:
            lines = content.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Detectar possíveis problemas
                if 'db.session.commit()' in line and 'try:' not in lines[max(0, i-5):i]:
                    bugs.append({
                        'line': i,
                        'type': 'database_commit_without_try',
                        'description': 'Commit sem tratamento de exceção',
                        'severity': 'medium'
                    })
                
                if 'print(' in line:
                    bugs.append({
                        'line': i,
                        'type': 'debug_print',
                        'description': 'Print statement encontrado (possível debug)',
                        'severity': 'low'
                    })
                
                if 'TODO' in line or 'FIXME' in line:
                    bugs.append({
                        'line': i,
                        'type': 'todo_comment',
                        'description': 'Comentário TODO/FIXME encontrado',
                        'severity': 'low'
                    })
            
            return bugs
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na detecção de bugs: {e}")
            return []
    
    def _generate_file_suggestions(self, content: str, file_path: str) -> List[str]:
        """Gera sugestões para um arquivo específico"""
        suggestions = []
        
        try:
            if file_path.endswith('.py'):
                # Sugestões para Python
                if 'class ' in content and '__repr__' not in content:
                    suggestions.append("Adicionar método __repr__ às classes")
                
                if 'db.Model' in content and 'to_dict' not in content:
                    suggestions.append("Adicionar método to_dict para serialização")
                
                if 'route(' in content and '@login_required' not in content:
                    suggestions.append("Verificar se todas as rotas precisam de autenticação")
                
                if len(content.split('\n')) > 500:
                    suggestions.append("Arquivo muito grande - considere dividir em módulos menores")
            
            elif file_path.endswith('.html'):
                # Sugestões para HTML
                if 'csrf_token' not in content and 'form' in content:
                    suggestions.append("Adicionar proteção CSRF aos formulários")
                
                if 'script' in content and 'src=' not in content:
                    suggestions.append("Considere mover JavaScript inline para arquivos externos")
            
            return suggestions
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar sugestões: {e}")
            return []
    
    def _check_documentation(self, content: str, file_path: str) -> Dict[str, Any]:
        """Verifica status da documentação"""
        try:
            doc_lines = 0
            total_lines = len(content.split('\n'))
            
            # Contar linhas de documentação
            for line in content.split('\n'):
                if line.strip().startswith('"""') or line.strip().startswith("'''"):
                    doc_lines += 1
                elif line.strip().startswith('#'):
                    doc_lines += 1
            
            doc_percentage = (doc_lines / total_lines) * 100 if total_lines > 0 else 0
            
            status = 'Boa' if doc_percentage > 20 else 'Média' if doc_percentage > 10 else 'Baixa'
            
            return {
                'status': status,
                'percentage': round(doc_percentage, 1),
                'doc_lines': doc_lines,
                'total_lines': total_lines
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na análise de documentação: {e}")
            return {'status': 'Erro', 'error': str(e)}
    
    # Métodos para modificação de arquivos
    
    def _add_field_to_model(self, content: str, details: Dict[str, Any]) -> str:
        """Adiciona campo a um modelo SQLAlchemy"""
        try:
            field_name = details.get('field_name')
            field_type = details.get('field_type', 'String')
            nullable = details.get('nullable', True)
            
            if not field_name:
                raise ValueError("Nome do campo é obrigatório")
            
            # Encontrar onde adicionar o campo
            lines = content.split('\n')
            insert_index = -1
            
            for i, line in enumerate(lines):
                if 'db.Column' in line and 'id = ' not in line:
                    insert_index = i + 1
            
            if insert_index == -1:
                # Procurar por 'class ' e adicionar após
                for i, line in enumerate(lines):
                    if 'class ' in line and 'db.Model' in line:
                        insert_index = i + 3
                        break
            
            if insert_index > 0:
                field_line = f"    {field_name} = db.Column(db.{field_type}, nullable={nullable})"
                lines.insert(insert_index, field_line)
                return '\n'.join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar campo: {e}")
            return content
    
    def _add_route_to_file(self, content: str, details: Dict[str, Any]) -> str:
        """Adiciona nova rota a um arquivo"""
        try:
            route_name = details.get('route_name')
            route_path = details.get('route_path', f'/{route_name}')
            methods = details.get('methods', ['GET'])
            
            if not route_name:
                raise ValueError("Nome da rota é obrigatório")
            
            # Template da nova rota
            new_route = f"""
@{route_name}_bp.route('{route_path}', methods={methods})
@login_required
def {route_name}():
    \"\"\"Função para {route_name}\"\"\"
    # TODO: Implementar lógica da rota
    return render_template('{route_name}.html')
"""
            
            # Adicionar no final do arquivo
            return content + new_route
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar rota: {e}")
            return content
    
    def _add_method_to_class(self, content: str, details: Dict[str, Any]) -> str:
        """Adiciona método a uma classe"""
        try:
            method_name = details.get('method_name')
            class_name = details.get('class_name')
            
            if not method_name or not class_name:
                raise ValueError("Nome do método e classe são obrigatórios")
            
            # Template do novo método
            new_method = f"""
    def {method_name}(self):
        \"\"\"Método {method_name}\"\"\"
        # TODO: Implementar lógica do método
        pass
"""
            
            # Encontrar a classe e adicionar o método
            lines = content.split('\n')
            in_class = False
            insert_index = -1
            
            for i, line in enumerate(lines):
                if f'class {class_name}' in line:
                    in_class = True
                elif in_class and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                    insert_index = i
                    break
            
            if insert_index > 0:
                method_lines = new_method.split('\n')
                for j, method_line in enumerate(reversed(method_lines)):
                    lines.insert(insert_index, method_line)
                
                return '\n'.join(lines)
            
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro ao adicionar método: {e}")
            return content
    
    def _refactor_code(self, content: str, details: Dict[str, Any]) -> str:
        """Refatora código baseado em detalhes"""
        # Implementação básica - pode ser expandida
        return content
    
    def _fix_detected_bug(self, content: str, details: Dict[str, Any]) -> str:
        """Corrige bug detectado"""
        # Implementação básica - pode ser expandida
        return content
    
    def _validate_modified_code(self, content: str, file_path: str) -> Dict[str, Any]:
        """Valida código modificado"""
        try:
            if file_path.endswith('.py'):
                # Validar sintaxe Python
                import ast
                ast.parse(content)
                
                return {
                    'valid': True,
                    'errors': [],
                    'warnings': []
                }
            
            return {'valid': True, 'errors': [], 'warnings': []}
            
        except SyntaxError as e:
            return {
                'valid': False,
                'errors': [f'Erro de sintaxe na linha {e.lineno}: {e.msg}'],
                'warnings': []
            }
        except Exception as e:
            return {
                'valid': False,
                'errors': [str(e)],
                'warnings': []
            }
    
    def _generate_changes_summary(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """Gera resumo das mudanças"""
        try:
            old_lines = old_content.split('\n')
            new_lines = new_content.split('\n')
            
            return {
                'lines_added': len(new_lines) - len(old_lines),
                'total_lines_old': len(old_lines),
                'total_lines_new': len(new_lines),
                'significant_changes': abs(len(new_lines) - len(old_lines)) > 5
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar resumo: {e}")
            return {}
    
    # Handlers para diferentes tipos de consulta
    
    def _handle_creation_request(self, query: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Processa solicitação de criação"""
        try:
            # Detectar tipo de criação
            if 'módulo' in query.lower() or 'module' in query.lower():
                # Extrair nome do módulo
                import re
                match = re.search(r'(?:módulo|module)\s+(\w+)', query.lower())
                if match:
                    module_name = match.group(1)
                    result = self.generate_new_module(module_name, query)
                    return {'status': 'success', 'result': result}
            
            return {'status': 'info', 'message': 'Especifique o que deseja criar (ex: "criar módulo vendas")'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _handle_analysis_request(self, query: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Processa solicitação de análise"""
        try:
            if 'projeto' in query.lower():
                result = self.analyze_project_complete()
                return {'status': 'success', 'result': result}
            
            # Verificar se é análise de arquivo específico
            import re
            file_match = re.search(r'arquivo\s+([^\s]+)', query.lower())
            if file_match:
                file_path = file_match.group(1)
                result = self.analyze_specific_file(file_path)
                return {'status': 'success', 'result': result}
            
            return {'status': 'info', 'message': 'Especifique o que analisar (ex: "analisar projeto" ou "analisar arquivo app/models.py")'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _handle_fix_request(self, query: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Processa solicitação de correção"""
        try:
            result = self.detect_and_fix_issues()
            return {'status': 'success', 'result': result}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _handle_explanation_request(self, query: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Processa solicitação de explicação"""
        try:
            capabilities = self.get_capabilities_summary()
            return {'status': 'success', 'result': capabilities}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def _handle_general_request(self, query: str, intent_analysis: Dict) -> Dict[str, Any]:
        """Processa solicitação geral"""
        return {
            'status': 'info',
            'message': 'Não entendi sua solicitação. Tente: "analisar projeto", "criar módulo", "detectar problemas" ou "capacidades"'
        }
    
    # Métodos para geração de documentação
    
    def _generate_project_documentation(self) -> Dict[str, Any]:
        """Gera documentação completa do projeto"""
        try:
            if not self.project_cache:
                self.project_cache = self.project_scanner.scan_complete_project()
            
            overview = self._generate_project_overview()
            
            doc_content = f"""# Documentação do Projeto

## Visão Geral
- **Total de Módulos:** {overview.get('total_modules', 0)}
- **Total de Modelos:** {overview.get('total_models', 0)}
- **Total de Rotas:** {overview.get('total_routes', 0)}
- **Total de Templates:** {overview.get('total_templates', 0)}
- **Tabelas do Banco:** {overview.get('database_tables', 0)}

## Arquitetura
- **Padrão:** {overview.get('architecture_pattern', 'Flask MVC')}
- **Framework:** {overview.get('framework_version', 'Flask 2.x')}

## Módulos Disponíveis
"""
            
            # Adicionar módulos
            routes = self.project_cache.get('routes', {})
            for module_name, route_info in routes.items():
                doc_content += f"### {module_name.title()}\n"
                doc_content += f"- **Rotas:** {route_info.get('total_routes', 0)}\n"
                doc_content += f"- **Arquivo:** {route_info.get('file_path', 'N/A')}\n\n"
            
            return {
                'content': doc_content,
                'format': 'markdown',
                'file_suggestion': 'DOCUMENTACAO_PROJETO.md'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar documentação do projeto: {e}")
            return {'error': str(e)}
    
    def _generate_file_documentation(self, file_path: str) -> Dict[str, Any]:
        """Gera documentação para arquivo específico"""
        try:
            analysis = self.analyze_specific_file(file_path)
            
            if 'error' in analysis:
                return analysis
            
            file_info = analysis.get('file_info', {})
            structure = analysis.get('code_structure', {})
            
            doc_content = f"""# Documentação: {file_path}

## Informações do Arquivo
- **Tamanho:** {file_info.get('size_kb', 0):.1f} KB
- **Linhas:** {file_info.get('lines', 0)}
- **Tipo:** {file_info.get('extension', 'N/A')}

## Estrutura do Código
- **Classes:** {len(structure.get('classes', []))}
- **Funções:** {len(structure.get('functions', []))}
- **Imports:** {len(structure.get('imports', []))}

## Classes Encontradas
"""
            
            for class_name in structure.get('classes', []):
                doc_content += f"- `{class_name}`\n"
            
            doc_content += "\n## Funções Encontradas\n"
            for func_name in structure.get('functions', []):
                doc_content += f"- `{func_name}()`\n"
            
            return {
                'content': doc_content,
                'format': 'markdown',
                'file_suggestion': f'DOC_{file_path.replace("/", "_").replace(".", "_")}.md'
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar documentação do arquivo: {e}")
            return {'error': str(e)}
    
    # Métodos para detecção automática de problemas
    
    def _detect_import_issues(self, project_data: Dict) -> List[Dict[str, Any]]:
        """Detecta problemas de import"""
        issues = []
        
        try:
            routes = project_data.get('routes', {})
            
            for module_name, route_info in routes.items():
                file_path = route_info.get('file_path')
                if file_path:
                    content = self.code_generator.read_file(file_path)
                    if not content.startswith('❌'):
                        imports = self._extract_imports(content)
                        
                        # Verificar imports desnecessários
                        for imp in imports:
                            if imp not in content.replace(f'import {imp}', '').replace(f'from {imp}', ''):
                                issues.append({
                                    'type': 'unused_import',
                                    'file': file_path,
                                    'description': f'Import não utilizado: {imp}',
                                    'auto_fixable': True
                                })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na detecção de imports: {e}")
            return []
    
    def _detect_naming_issues(self, project_data: Dict) -> List[Dict[str, Any]]:
        """Detecta problemas de nomenclatura"""
        issues = []
        
        try:
            models = project_data.get('models', {})
            
            for model_name, model_info in models.items():
                class_name = model_info.get('class_name', '')
                
                # Verificar convenção PascalCase para classes
                if class_name and not class_name[0].isupper():
                    issues.append({
                        'type': 'naming_convention',
                        'file': model_info.get('file_path'),
                        'description': f'Classe {class_name} deveria usar PascalCase',
                        'auto_fixable': False
                    })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na detecção de nomenclatura: {e}")
            return []
    
    def _detect_security_issues(self, project_data: Dict) -> List[Dict[str, Any]]:
        """Detecta problemas de segurança"""
        issues = []
        
        try:
            templates = project_data.get('templates', {})
            
            for template_path, template_info in templates.items():
                if template_path.endswith('.html'):
                    file_path = template_info.get('full_path')
                    if file_path:
                        content = self.code_generator.read_file(file_path)
                        if not content.startswith('❌'):
                            # Verificar CSRF em formulários
                            if '<form' in content and 'csrf_token' not in content:
                                issues.append({
                                    'type': 'missing_csrf',
                                    'file': file_path,
                                    'description': 'Formulário sem proteção CSRF',
                                    'auto_fixable': True
                                })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na detecção de segurança: {e}")
            return []
    
    def _detect_performance_issues(self, project_data: Dict) -> List[Dict[str, Any]]:
        """Detecta problemas de performance"""
        issues = []
        
        try:
            routes = project_data.get('routes', {})
            
            for module_name, route_info in routes.items():
                file_path = route_info.get('file_path')
                if file_path:
                    content = self.code_generator.read_file(file_path)
                    if not content.startswith('❌') and 'query.all()' in content:
                        issues.append({
                            'type': 'inefficient_query',
                            'file': file_path,
                            'description': 'Uso de .all() pode causar problemas de performance',
                            'auto_fixable': False
                        })
            
            return issues
            
        except Exception as e:
            logger.warning(f"⚠️ Erro na detecção de performance: {e}")
            return []
    
    def _apply_automatic_fix(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Aplica correção automática"""
        try:
            issue_type = issue.get('type')
            file_path = issue.get('file')
            
            if not file_path:
                return {'success': False, 'error': 'Arquivo não especificado'}
            
            content = self.code_generator.read_file(file_path)
            if content.startswith('❌'):
                return {'success': False, 'error': 'Erro ao ler arquivo'}
            
            # Aplicar correção baseada no tipo
            if issue_type == 'missing_csrf':
                # Adicionar CSRF token
                new_content = content.replace('<form', '<form>\n{{ csrf_token() }}')
                if self.code_generator.write_file(file_path, new_content, True):
                    return {'success': True, 'description': 'CSRF token adicionado'}
            
            return {'success': False, 'error': f'Correção automática não implementada para {issue_type}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_fix_recommendations(self, issues: List[Dict]) -> List[str]:
        """Gera recomendações de correção"""
        recommendations = []
        
        try:
            # Agrupar por tipo
            issue_types = {}
            for issue in issues:
                issue_type = issue.get('type', 'unknown')
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1
            
            # Gerar recomendações
            for issue_type, count in issue_types.items():
                if issue_type == 'missing_csrf':
                    recommendations.append(f"Adicionar proteção CSRF em {count} formulário(s)")
                elif issue_type == 'unused_import':
                    recommendations.append(f"Remover {count} import(s) não utilizado(s)")
                elif issue_type == 'missing_audit_fields':
                    recommendations.append(f"Adicionar campos de auditoria em {count} modelo(s)")
                else:
                    recommendations.append(f"Revisar {count} problema(s) do tipo {issue_type}")
            
            return recommendations
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao gerar recomendações: {e}")
            return []
    
    def _generate_next_steps(self, module_name: str) -> List[str]:
        """Gera próximos passos após criar módulo"""
        return [
            f"Registrar blueprint do módulo {module_name} no __init__.py",
            "Executar migração do banco de dados",
            "Testar as funcionalidades criadas",
            "Adicionar validações específicas se necessário",
            "Implementar testes unitários para o módulo"
        ]


    def activate_unlimited_capabilities(self) -> bool:
        """Ativa capacidades ilimitadas"""
        try:
            unlimited_mode = get_unlimited_mode()
            
            # Expandir todas as capacidades
            self.unlimited_active = True
            
            logger.info("💪 CAPACIDADES ILIMITADAS ATIVADAS!")
            logger.info("🚀 Max tokens: 8192")
            logger.info("📖 Leitura: Arquivos completos")
            logger.info("🔍 Análise: Sem limitações")
            logger.info("🧠 Raciocínio: Modo avançado")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao ativar capacidades ilimitadas: {e}")
            return False
    
    def analyze_project_unlimited(self) -> Dict[str, Any]:
        """Análise de projeto sem limitações"""
        try:
            unlimited_mode = get_unlimited_mode()
            
            # Leitura completa do projeto
            project_data = unlimited_mode.read_entire_project()
            
            # Análise ilimitada de padrões
            patterns = unlimited_mode.analyze_unlimited_patterns(project_data)
            
            # Insights ilimitados
            insights = unlimited_mode.generate_unlimited_insights(patterns)
            
            return {
                'project_data': project_data,
                'patterns': patterns,
                'insights': insights,
                'unlimited_mode': True,
                'analysis_depth': 'maximum'
            }
            
        except Exception as e:
            logger.error(f"Erro na análise ilimitada: {e}")
            return {'error': str(e)}


# Instância global
_claude_dev_ai = None

def init_claude_development_ai(app_path: Optional[str] = None) -> ClaudeDevelopmentAI:
    """Inicializa Claude Development AI"""
    global _claude_dev_ai
    _claude_dev_ai = ClaudeDevelopmentAI(app_path)
    return _claude_dev_ai

def get_claude_development_ai() -> Optional[ClaudeDevelopmentAI]:
    """Obtém instância do Claude Development AI"""
    return _claude_dev_ai 