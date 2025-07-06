"""
🔍 CLAUDE PROJECT SCANNER - Descoberta Dinâmica Completa
Sistema que permite ao Claude AI descobrir e mapear TODA a estrutura do projeto automaticamente
"""

import os
import ast
import inspect
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from sqlalchemy import inspect as sql_inspect, text
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class ClaudeProjectScanner:
    """Scanner completo do projeto para dar autonomia total ao Claude AI"""
    
    def __init__(self, app_path: Optional[str] = None):
        """Inicializa scanner do projeto"""
        self.app_path = Path(app_path) if app_path else Path(__file__).parent.parent
        self.project_structure = {}
        self.discovered_models = {}
        self.discovered_forms = {}
        self.discovered_routes = {}
        self.discovered_templates = {}
        self.database_schema = {}
        
        logger.info(f"🔍 Claude Project Scanner inicializado: {self.app_path}")
    
    def scan_complete_project(self) -> Dict[str, Any]:
        """
        ESCANEAMENTO COMPLETO DO PROJETO
        Descobre TUDO dinamicamente: módulos, models, forms, routes, templates, banco
        """
        try:
            logger.info("🚀 INICIANDO ESCANEAMENTO COMPLETO DO PROJETO")
            
            # 1. 📁 DESCOBRIR ESTRUTURA DE PASTAS
            self.project_structure = self._discover_project_structure()
            
            # 2. 🗃️ DESCOBRIR TODOS OS MODELOS DINAMICAMENTE
            self.discovered_models = self._discover_all_models()
            
            # 3. 📝 DESCOBRIR TODOS OS FORMULÁRIOS
            self.discovered_forms = self._discover_all_forms()
            
            # 4. 🌐 DESCOBRIR TODAS AS ROTAS
            self.discovered_routes = self._discover_all_routes()
            
            # 5. 🎨 DESCOBRIR TODOS OS TEMPLATES
            self.discovered_templates = self._discover_all_templates()
            
            # 6. 🗄️ DESCOBRIR ESQUEMA COMPLETO DO BANCO
            self.database_schema = self._discover_database_schema()
            
            # 7. 📊 COMPILAR RELATÓRIO COMPLETO
            complete_map = {
                'project_structure': self.project_structure,
                'models': self.discovered_models,
                'forms': self.discovered_forms,
                'routes': self.discovered_routes,
                'templates': self.discovered_templates,
                'database_schema': self.database_schema,
                'scan_summary': self._generate_scan_summary()
            }
            
            logger.info("✅ ESCANEAMENTO COMPLETO FINALIZADO")
            return complete_map
            
        except Exception as e:
            logger.error(f"❌ Erro no escaneamento completo: {e}")
            return {}
    
    def _discover_project_structure(self) -> Dict[str, Any]:
        """Descobre estrutura completa de pastas e arquivos"""
        structure = {}
        
        try:
            for root, dirs, files in os.walk(self.app_path):
                # Ignorar pastas desnecessárias
                dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__', 'node_modules'))]
                
                rel_path = os.path.relpath(root, self.app_path)
                if rel_path == '.':
                    rel_path = 'app_root'
                
                structure[rel_path] = {
                    'directories': dirs.copy(),
                    'python_files': [f for f in files if f.endswith('.py')],
                    'template_files': [f for f in files if f.endswith('.html')],
                    'other_files': [f for f in files if not f.endswith(('.py', '.html', '.pyc'))]
                }
            
            logger.info(f"📁 Estrutura descoberta: {len(structure)} diretórios")
            return structure
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir estrutura: {e}")
            return {}
    
    def _discover_all_models(self) -> Dict[str, Any]:
        """Descobre TODOS os modelos do projeto dinamicamente"""
        models = {}
        
        try:
            # Importar o db para inspeção
            from app import db
            
            # 1. DESCOBRIR VIA SQLALCHEMY METADATA (MAIS CONFIÁVEL)
            inspector = sql_inspect(db.engine)
            table_names = inspector.get_table_names()
            
            for table_name in table_names:
                try:
                    columns = inspector.get_columns(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    indexes = inspector.get_indexes(table_name)
                    
                    models[table_name] = {
                        'source': 'database_inspection',
                        'columns': [
                            {
                                'name': col['name'],
                                'type': str(col['type']),
                                'nullable': col['nullable'],
                                'default': col.get('default'),
                                'primary_key': col.get('primary_key', False)
                            } for col in columns
                        ],
                        'foreign_keys': [
                            {
                                'column': fk['constrained_columns'][0] if fk['constrained_columns'] else None,
                                'referenced_table': fk['referred_table'],
                                'referenced_column': fk['referred_columns'][0] if fk['referred_columns'] else None
                            } for fk in foreign_keys
                        ],
                        'indexes': [idx['name'] for idx in indexes]
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao inspecionar tabela {table_name}: {e}")
            
            # 2. DESCOBRIR VIA ARQUIVOS MODELS.PY (COMPLEMENTAR)
            for module_dir in self.app_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith('.'):
                    models_file = module_dir / 'models.py'
                    if models_file.exists():
                        models.update(self._parse_models_file(models_file, module_dir.name))
            
            logger.info(f"🗃️ Modelos descobertos: {len(models)} tabelas")
            return models
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir modelos: {e}")
            return {}
    
    def _parse_models_file(self, models_file: Path, module_name: str) -> Dict[str, Any]:
        """Parse de arquivo models.py específico"""
        models = {}
        
        try:
            with open(models_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Verificar se herda de db.Model
                    is_model = any(
                        (isinstance(base, ast.Attribute) and 
                         base.attr == 'Model' and 
                         isinstance(base.value, ast.Name) and 
                         base.value.id == 'db') or
                        (isinstance(base, ast.Name) and base.id in ['Model', 'UserMixin'])
                        for base in node.bases
                    )
                    
                    if is_model:
                        model_info = {
                            'source': f'models_file_{module_name}',
                            'file_path': str(models_file),
                            'class_name': node.name,
                            'fields': [],
                            'relationships': [],
                            'methods': []
                        }
                        
                        # Extrair campos e relacionamentos
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        field_name = target.id
                                        field_type = self._extract_field_type(item.value)
                                        
                                        if 'Column' in field_type:
                                            model_info['fields'].append({
                                                'name': field_name,
                                                'type': field_type
                                            })
                                        elif 'relationship' in field_type:
                                            model_info['relationships'].append({
                                                'name': field_name,
                                                'type': field_type
                                            })
                            
                            elif isinstance(item, ast.FunctionDef):
                                model_info['methods'].append(item.name)
                        
                        models[f"{module_name}_{node.name}"] = model_info
            
            return models
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear {models_file}: {e}")
            return {}
    
    def _extract_field_type(self, node) -> str:
        """Extrai tipo do campo de um nó AST"""
        try:
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    return f"{node.func.attr}(...)"
                elif isinstance(node.func, ast.Name):
                    return f"{node.func.id}(...)"
            return "unknown"
        except:
            return "unknown"
    
    def _discover_all_forms(self) -> Dict[str, Any]:
        """Descobre todos os formulários FlaskForm"""
        forms = {}
        
        try:
            for module_dir in self.app_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith('.'):
                    forms_file = module_dir / 'forms.py'
                    if forms_file.exists():
                        forms.update(self._parse_forms_file(forms_file, module_dir.name))
            
            logger.info(f"📝 Formulários descobertos: {len(forms)}")
            return forms
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir formulários: {e}")
            return {}
    
    def _parse_forms_file(self, forms_file: Path, module_name: str) -> Dict[str, Any]:
        """Parse de arquivo forms.py"""
        forms = {}
        
        try:
            with open(forms_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Verificar se herda de FlaskForm
                    is_form = any(
                        (isinstance(base, ast.Name) and base.id in ['FlaskForm', 'Form'])
                        for base in node.bases
                    )
                    
                    if is_form:
                        form_info = {
                            'module': module_name,
                            'file_path': str(forms_file),
                            'class_name': node.name,
                            'fields': [],
                            'validators': []
                        }
                        
                        # Extrair campos do formulário
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        field_name = target.id
                                        field_type = self._extract_field_type(item.value)
                                        
                                        if 'Field' in field_type:
                                            form_info['fields'].append({
                                                'name': field_name,
                                                'type': field_type
                                            })
                        
                        forms[f"{module_name}_{node.name}"] = form_info
            
            return forms
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear forms {forms_file}: {e}")
            return {}
    
    def _discover_all_routes(self) -> Dict[str, Any]:
        """Descobre todas as rotas do projeto"""
        routes = {}
        
        try:
            for module_dir in self.app_path.iterdir():
                if module_dir.is_dir() and not module_dir.name.startswith('.'):
                    routes_file = module_dir / 'routes.py'
                    if routes_file.exists():
                        routes.update(self._parse_routes_file(routes_file, module_dir.name))
            
            logger.info(f"🌐 Rotas descobertas: {len(routes)}")
            return routes
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir rotas: {e}")
            return {}
    
    def _parse_routes_file(self, routes_file: Path, module_name: str) -> Dict[str, Any]:
        """Parse de arquivo routes.py"""
        routes = {}
        
        try:
            with open(routes_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            blueprint_name = None
            current_routes = []
            
            for i, line in enumerate(lines):
                # Detectar blueprint
                if 'Blueprint' in line and '=' in line:
                    blueprint_name = line.split('=')[0].strip()
                
                # Detectar decorador de rota
                if '.route(' in line or '@app.route(' in line:
                    route_info = {
                        'decorator': line.strip(),
                        'line_number': i + 1
                    }
                    
                    # Buscar função na próxima linha
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith('def '):
                            route_info['function'] = next_line
                    
                    current_routes.append(route_info)
            
            if current_routes:
                routes[module_name] = {
                    'blueprint': blueprint_name,
                    'file_path': str(routes_file),
                    'routes': current_routes,
                    'total_routes': len(current_routes)
                }
            
            return routes
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear routes {routes_file}: {e}")
            return {}
    
    def _discover_all_templates(self) -> Dict[str, Any]:
        """Descobre todos os templates HTML"""
        templates = {}
        
        try:
            templates_dir = self.app_path / 'templates'
            if templates_dir.exists():
                for root, dirs, files in os.walk(templates_dir):
                    for file in files:
                        if file.endswith('.html'):
                            file_path = Path(root) / file
                            rel_path = file_path.relative_to(templates_dir)
                            
                            templates[str(rel_path)] = {
                                'full_path': str(file_path),
                                'size_kb': round(file_path.stat().st_size / 1024, 2),
                                'module': rel_path.parts[0] if len(rel_path.parts) > 1 else 'root',
                                'template_vars': self._extract_template_variables(file_path)
                            }
            
            logger.info(f"🎨 Templates descobertos: {len(templates)}")
            return templates
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir templates: {e}")
            return {}
    
    def _extract_template_variables(self, template_file: Path) -> List[str]:
        """Extrai variáveis de um template HTML"""
        variables = set()
        
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscar variáveis {{ }} e {% %}
            import re
            
            # Variáveis {{ variable }}
            var_pattern = r'\{\{\s*([^}]+)\s*\}\}'
            matches = re.findall(var_pattern, content)
            for match in matches:
                # Extrair apenas o nome da variável (antes do primeiro . ou |)
                var_name = match.split('.')[0].split('|')[0].strip()
                if var_name and not var_name.startswith('"') and not var_name.startswith("'"):
                    variables.add(var_name)
            
            # Tags {% for x in y %}
            for_pattern = r'\{\%\s*for\s+\w+\s+in\s+([^%]+)\s*\%\}'
            matches = re.findall(for_pattern, content)
            for match in matches:
                var_name = match.strip()
                if var_name:
                    variables.add(var_name)
            
            return list(variables)[:20]  # Limitar a 20 variáveis
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao extrair variáveis de {template_file}: {e}")
            return []
    
    def _discover_database_schema(self) -> Dict[str, Any]:
        """Descobre esquema completo do banco de dados dinamicamente"""
        schema = {}
        
        try:
            from app import db
            
            inspector = sql_inspect(db.engine)
            
            # Informações gerais do banco
            schema['database_info'] = {
                'dialect': str(db.engine.dialect.name),
                'driver': str(db.engine.driver),
                'server_version': self._get_database_version(db)
            }
            
            # Todas as tabelas
            table_names = inspector.get_table_names()
            schema['tables'] = {}
            
            for table_name in table_names:
                try:
                    schema['tables'][table_name] = {
                        'columns': inspector.get_columns(table_name),
                        'primary_keys': inspector.get_pk_constraint(table_name),
                        'foreign_keys': inspector.get_foreign_keys(table_name),
                        'indexes': inspector.get_indexes(table_name),
                        'unique_constraints': inspector.get_unique_constraints(table_name)
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Erro ao inspecionar tabela {table_name}: {e}")
            
            # Estatísticas de tabelas (se PostgreSQL)
            if 'postgresql' in str(db.engine.dialect.name).lower():
                schema['table_statistics'] = self._get_postgresql_statistics(db)
            
            logger.info(f"🗄️ Esquema do banco descoberto: {len(schema['tables'])} tabelas")
            return schema
            
        except Exception as e:
            logger.error(f"❌ Erro ao descobrir esquema do banco: {e}")
            return {}
    
    def _get_database_version(self, db) -> str:
        """Obtém versão do banco de dados"""
        try:
            if 'postgresql' in str(db.engine.dialect.name).lower():
                result = db.session.execute(text("SELECT version();")).fetchone()
                return result[0] if result else "Unknown"
            else:
                return "Unknown"
        except:
            return "Unknown"
    
    def _get_postgresql_statistics(self, db) -> Dict[str, Any]:
        """Obtém estatísticas específicas do PostgreSQL"""
        try:
            # Tamanho das tabelas
            result = db.session.execute(text("""
                SELECT 
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """)).fetchall()
            
            return {
                'table_sizes': [{'table': row[0], 'size': row[1]} for row in result]
            }
        except Exception as e:
            logger.warning(f"⚠️ Erro ao obter estatísticas PostgreSQL: {e}")
            return {}
    
    def _generate_scan_summary(self) -> Dict[str, Any]:
        """Gera resumo do escaneamento completo"""
        return {
            'total_modules': len([d for d in self.project_structure.keys() if 'python_files' in self.project_structure[d] and self.project_structure[d]['python_files']]),
            'total_models': len(self.discovered_models),
            'total_forms': len(self.discovered_forms),
            'total_routes': sum(route_info.get('total_routes', 0) for route_info in self.discovered_routes.values()),
            'total_templates': len(self.discovered_templates),
            'total_database_tables': len(self.database_schema.get('tables', {})),
            'scan_timestamp': str(datetime.now()),
            'project_root': str(self.app_path)
        }
    
    def read_file_content(self, file_path: str, encoding: str = 'utf-8') -> str:
        """Lê conteúdo de qualquer arquivo do projeto"""
        try:
            full_path = self.app_path / file_path if not os.path.isabs(file_path) else Path(file_path)
            
            # Verificar se arquivo existe
            if not full_path.exists():
                return f"❌ Arquivo não encontrado: {file_path}"
            
            # Verificar se está dentro do projeto
            if not str(full_path).startswith(str(self.app_path)):
                return f"🔒 Acesso negado: arquivo fora do projeto"
            
            with open(full_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.info(f"📖 Lido arquivo: {file_path} ({len(content)} chars)")
            return content
            
        except Exception as e:
            logger.error(f"❌ Erro ao ler {file_path}: {e}")
            return f"❌ Erro ao ler arquivo: {e}"
    
    def list_directory_contents(self, dir_path: str = '') -> Dict[str, Any]:
        """Lista conteúdo de qualquer diretório do projeto"""
        try:
            target_dir = self.app_path / dir_path if dir_path else self.app_path
            
            if not target_dir.exists() or not target_dir.is_dir():
                return {'error': f"Diretório não encontrado: {dir_path}"}
            
            contents = {
                'directories': [],
                'files': [],
                'path': str(target_dir.relative_to(self.app_path))
            }
            
            for item in target_dir.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    contents['directories'].append(item.name)
                elif item.is_file():
                    contents['files'].append({
                        'name': item.name,
                        'size_kb': round(item.stat().st_size / 1024, 2),
                        'extension': item.suffix
                    })
            
            return contents
            
        except Exception as e:
            logger.error(f"❌ Erro ao listar diretório {dir_path}: {e}")
            return {'error': str(e)}
    
    def search_in_files(self, pattern: str, file_extensions: Optional[List[str]] = None, 
                       max_results: int = 50) -> Dict[str, Any]:
        """Busca por padrão em arquivos do projeto"""
        try:
            import re
            
            if file_extensions is None:
                file_extensions = ['.py', '.html', '.js', '.css']
            
            results = []
            files_searched = 0
            
            # Buscar recursivamente
            for root, dirs, files in os.walk(self.app_path):
                # Ignorar diretórios desnecessários
                dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__', 'node_modules', 'venv'))]
                
                for file in files:
                    # Verificar extensão
                    if not any(file.endswith(ext) for ext in file_extensions):
                        continue
                    
                    file_path = Path(root) / file
                    files_searched += 1
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    results.append({
                                        'file': str(file_path.relative_to(self.app_path)),
                                        'line_number': line_num,
                                        'line_content': line.strip()[:200]  # Limitar tamanho
                                    })
                                    
                                    if len(results) >= max_results:
                                        return {
                                            'success': True,
                                            'results': results,
                                            'total_matches': len(results),
                                            'files_searched': files_searched,
                                            'truncated': True
                                        }
                    except Exception as e:
                        # Ignorar arquivos que não podem ser lidos
                        pass
            
            logger.info(f"🔍 Busca '{pattern}': {len(results)} resultados em {files_searched} arquivos")
            
            return {
                'success': True,
                'results': results,
                'total_matches': len(results),
                'files_searched': files_searched,
                'truncated': False
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return {'success': False, 'error': str(e)}

# Instância global do scanner
project_scanner = None

def init_project_scanner(app_path: Optional[str] = None) -> ClaudeProjectScanner:
    """Inicializa o scanner de projeto"""
    global project_scanner
    project_scanner = ClaudeProjectScanner(app_path)
    return project_scanner

def get_project_scanner() -> Optional[ClaudeProjectScanner]:
    """Retorna instância do scanner de projeto"""
    return project_scanner

# Importações necessárias
from datetime import datetime 