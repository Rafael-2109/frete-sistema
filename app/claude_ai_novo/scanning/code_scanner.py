"""
💻 CODE SCANNER - Análise de Código
==================================

Especialista em análise de código Python,
descoberta de formulários e rotas Flask.

Responsabilidades:
- Descoberta de formulários FlaskForm
- Análise de rotas Flask
- Parse de decoradores
- Extração de funcionalidades
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class CodeScanner:
    """
    Especialista em análise de código e descoberta de funcionalidades.
    
    Analisa código Python para descobrir formulários,
    rotas e outras funcionalidades do Flask.
    """
    
    def __init__(self, app_path: Path):
        """
        Inicializa o scanner de código.
        
        Args:
            app_path: Caminho raiz do projeto
        """
        self.app_path = app_path
        logger.info("💻 CodeScanner inicializado")
    
    def discover_all_forms(self) -> Dict[str, Any]:
        """
        Descobre todos os formulários FlaskForm do projeto.
        
        Returns:
            Dict com formulários descobertos
        """
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
    
    def discover_all_routes(self) -> Dict[str, Any]:
        """
        Descobre todas as rotas Flask do projeto.
        
        Returns:
            Dict com rotas descobertas
        """
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
    
    def _parse_forms_file(self, forms_file: Path, module_name: str) -> Dict[str, Any]:
        """
        Parse detalhado de arquivo forms.py.
        
        Args:
            forms_file: Caminho para o arquivo
            module_name: Nome do módulo
            
        Returns:
            Dict com formulários encontrados
        """
        forms = {}
        
        try:
            with open(forms_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    # Verificar se herda de FlaskForm
                    is_form = self._is_flask_form(node)
                    
                    if is_form:
                        form_info = {
                            'module': module_name,
                            'file_path': str(forms_file),
                            'class_name': node.name,
                            'fields': [],
                            'validators': [],
                            'methods': []
                        }
                        
                        # Extrair campos e métodos do formulário
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                self._parse_form_field(item, form_info)
                            elif isinstance(item, ast.FunctionDef):
                                form_info['methods'].append({
                                    'name': item.name,
                                    'is_validator': item.name.startswith('validate_')
                                })
                        
                        forms[f"{module_name}_{node.name}"] = form_info
            
            return forms
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear {forms_file}: {e}")
            return {}
    
    def _is_flask_form(self, class_node: ast.ClassDef) -> bool:
        """Verifica se classe herda de FlaskForm"""
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                if base.id in ['FlaskForm', 'Form']:
                    return True
            elif isinstance(base, ast.Attribute):
                if base.attr in ['FlaskForm', 'Form']:
                    return True
        return False
    
    def _parse_form_field(self, assign_node: ast.Assign, form_info: Dict[str, Any]) -> None:
        """Parse de campo de formulário"""
        for target in assign_node.targets:
            if isinstance(target, ast.Name):
                field_name: str = target.id
                field_info = self._extract_form_field_info(assign_node.value)
                
                if field_info.get('type') and 'Field' in str(field_info.get('type', '')):
                    form_info['fields'].append({
                        'name': field_name,
                        'type': field_info.get('type'),
                        'validators': field_info.get('validators', []),
                        'render_kw': field_info.get('render_kw', {}),
                        'choices': field_info.get('choices', [])
                    })
    
    def _extract_form_field_info(self, value_node) -> Dict[str, Any]:
        """Extrai informações detalhadas do campo de formulário"""
        field_info: Dict[str, Any] = {'type': None}
        
        try:
            if isinstance(value_node, ast.Call):
                # Tipo do campo
                if isinstance(value_node.func, ast.Name):
                    field_info['type'] = value_node.func.id
                elif isinstance(value_node.func, ast.Attribute):
                    field_info['type'] = value_node.func.attr
                
                # Extrair argumentos nomeados
                for keyword in value_node.keywords:
                    if keyword.arg == 'validators':
                        field_info['validators'] = self._extract_validators(keyword.value)
                    elif keyword.arg == 'render_kw':
                        field_info['render_kw'] = self._extract_dict_value(keyword.value)
                    elif keyword.arg == 'choices':
                        field_info['choices'] = self._extract_choices(keyword.value)
                
        except Exception as e:
            logger.debug(f"Erro ao extrair campo de formulário: {e}")
        
        return field_info
    
    def _extract_validators(self, validators_node) -> List[str]:
        """Extrai lista de validadores"""
        validators = []
        try:
            if isinstance(validators_node, ast.List):
                for elt in validators_node.elts:
                    if isinstance(elt, ast.Call):
                        if isinstance(elt.func, ast.Name):
                            validators.append(elt.func.id)
                        elif isinstance(elt.func, ast.Attribute):
                            validators.append(elt.func.attr)
        except:
            pass
        return validators
    
    def _extract_dict_value(self, dict_node) -> Dict[str, Any]:
        """Extrai valor de dicionário"""
        result = {}
        try:
            if isinstance(dict_node, ast.Dict):
                for key, value in zip(dict_node.keys, dict_node.values):
                    if isinstance(key, ast.Constant):
                        key_str = str(key.value)
                        if isinstance(value, ast.Constant):
                            result[key_str] = value.value
        except:
            pass
        return result
    
    def _extract_choices(self, choices_node) -> List[Any]:
        """Extrai lista de choices"""
        choices = []
        try:
            if isinstance(choices_node, ast.List):
                for elt in choices_node.elts:
                    if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                        value = self._extract_simple_value(elt.elts[0])
                        label = self._extract_simple_value(elt.elts[1])
                        choices.append((value, label))
        except:
            pass
        return choices
    
    def _extract_simple_value(self, value_node) -> Any:
        """Extrai valor simples de um nó AST"""
        try:
            if isinstance(value_node, ast.Constant):
                return value_node.value
            elif isinstance(value_node, ast.Str):
                return value_node.s
            elif isinstance(value_node, ast.Num):
                return value_node.n
        except:
            pass
        return None
    
    def _parse_routes_file(self, routes_file: Path, module_name: str) -> Dict[str, Any]:
        """
        Parse detalhado de arquivo routes.py.
        
        Args:
            routes_file: Caminho para o arquivo
            module_name: Nome do módulo
            
        Returns:
            Dict com rotas encontradas
        """
        routes = {}
        
        try:
            with open(routes_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            blueprint_name = self._extract_blueprint_name(lines)
            discovered_routes = self._extract_routes_from_lines(lines)
            
            if discovered_routes:
                routes[module_name] = {
                    'blueprint': blueprint_name,
                    'file_path': str(routes_file),
                    'routes': discovered_routes,
                    'total_routes': len(discovered_routes),
                    'methods_summary': self._analyze_route_methods(discovered_routes)
                }
            
            return routes
            
        except Exception as e:
            logger.warning(f"⚠️ Erro ao parsear routes {routes_file}: {e}")
            return {}
    
    def _extract_blueprint_name(self, lines: List[str]) -> Optional[str]:
        """Extrai nome do blueprint do arquivo"""
        for line in lines:
            if 'Blueprint' in line and '=' in line:
                parts = line.split('=')
                if len(parts) >= 2:
                    return parts[0].strip()
        return None
    
    def _extract_routes_from_lines(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extrai rotas das linhas do arquivo"""
        routes = []
        
        for i, line in enumerate(lines):
            # Detectar decorador de rota
            if '.route(' in line or '@app.route(' in line:
                route_info = {
                    'decorator': line.strip(),
                    'line_number': i + 1,
                    'url_pattern': self._extract_url_pattern(line),
                    'methods': self._extract_route_methods(line)
                }
                
                # Buscar função na próxima linha(s)
                function_info = self._extract_function_info(lines, i + 1)
                route_info.update(function_info)
                
                routes.append(route_info)
        
        return routes
    
    def _extract_url_pattern(self, route_line: str) -> str:
        """Extrai padrão de URL da linha de rota"""
        try:
            # Buscar entre aspas
            import re
            match = re.search(r'["\']([^"\']+)["\']', route_line)
            return match.group(1) if match else 'unknown'
        except:
            return 'unknown'
    
    def _extract_route_methods(self, route_line: str) -> List[str]:
        """Extrai métodos HTTP da linha de rota"""
        methods = []
        try:
            if 'methods=' in route_line:
                # Buscar lista de métodos
                import re
                match = re.search(r'methods=\[(.*?)\]', route_line)
                if match:
                    methods_str = match.group(1)
                    methods = [m.strip().strip('\'"') for m in methods_str.split(',')]
        except:
            pass
        return methods or ['GET']  # Default para GET
    
    def _extract_function_info(self, lines: List[str], start_index: int) -> Dict[str, Any]:
        """Extrai informações da função de rota"""
        function_info = {'function_name': 'unknown', 'function_line': None}
        
        try:
            # Buscar função nas próximas linhas (máximo 5)
            for i in range(start_index, min(start_index + 5, len(lines))):
                line = lines[i].strip()
                if line.startswith('def '):
                    function_info['function_name'] = line.split('(')[0].replace('def ', '')
                    function_info['function_line'] = line
                    break
        except:
            pass
        
        return function_info
    
    def _analyze_route_methods(self, routes: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analisa métodos HTTP usados nas rotas"""
        methods_count = {}
        
        for route in routes:
            for method in route.get('methods', ['GET']):
                methods_count[method] = methods_count.get(method, 0) + 1
        
        return methods_count


# Singleton para uso global
_code_scanner = None

def get_code_scanner(app_path: Optional[Path] = None) -> CodeScanner:
    """
    Obtém instância do scanner de código.
    
    Args:
        app_path: Caminho do projeto
        
    Returns:
        Instância do CodeScanner
    """
    global _code_scanner
    if _code_scanner is None or app_path:
        if app_path is None:
            app_path = Path(__file__).parent.parent
        # Garantir que app_path é um Path válido
        assert app_path is not None, "app_path não pode ser None"
        _code_scanner = CodeScanner(app_path)
    return _code_scanner 