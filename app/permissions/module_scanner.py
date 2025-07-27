"""
Module Scanner - Auto-discover system modules and functions
=========================================================

This module automatically discovers all Flask routes and blueprints
to create a dynamic permission structure.
"""

from flask import current_app
from collections import defaultdict
import re
import logging

logger = logging.getLogger(__name__)


class ModuleScanner:
    """Scans Flask application for modules and functions"""
    
    # Ignore these blueprints/endpoints
    IGNORED_BLUEPRINTS = {'static', 'auth', 'permissions', 'main'}
    IGNORED_ENDPOINTS = {
        'static', 'login', 'logout', 'register', 'index', 
        'favicon', 'robots', 'sitemap', 'health'
    }
    
    # Module display names mapping
    MODULE_NAMES = {
        'faturamento': 'Faturamento',
        'carteira': 'Carteira de Pedidos',
        'embarques': 'Embarques',
        'entregas': 'Entregas',
        'monitoramento': 'Monitoramento',
        'transportadoras': 'Transportadoras',
        'vendedores': 'Vendedores',
        'relatorios': 'Relatórios',
        'financeiro': 'Financeiro',
        'cotacoes': 'Cotações',
        'pendencias': 'Pendências',
        'agendamentos': 'Agendamentos',
        'cidades': 'Cidades',
        'usuarios': 'Usuários',
        'configuracoes': 'Configurações',
        'api': 'API',
        'integracao': 'Integração',
        'separacao': 'Separação',
        'conferencia': 'Conferência',
        'expedicao': 'Expedição'
    }
    
    # Category mapping
    MODULE_CATEGORIES = {
        'operacional': ['carteira', 'separacao', 'conferencia', 'expedicao', 'embarques', 'entregas'],
        'financeiro': ['faturamento', 'financeiro', 'cotacoes', 'pendencias'],
        'cadastros': ['transportadoras', 'vendedores', 'cidades', 'usuarios'],
        'relatorios': ['relatorios', 'monitoramento'],
        'sistema': ['configuracoes', 'api', 'integracao', 'agendamentos']
    }
    
    # Function display names
    FUNCTION_NAMES = {
        'index': 'Visualizar',
        'list': 'Listar',
        'create': 'Criar',
        'new': 'Novo',
        'edit': 'Editar',
        'update': 'Atualizar',
        'delete': 'Excluir',
        'view': 'Visualizar',
        'show': 'Exibir',
        'detail': 'Detalhes',
        'import': 'Importar',
        'export': 'Exportar',
        'upload': 'Upload',
        'download': 'Download',
        'approve': 'Aprovar',
        'reject': 'Rejeitar',
        'cancel': 'Cancelar',
        'process': 'Processar',
        'generate': 'Gerar',
        'send': 'Enviar',
        'receive': 'Receber',
        'search': 'Pesquisar',
        'filter': 'Filtrar',
        'report': 'Relatório',
        'dashboard': 'Dashboard',
        'analytics': 'Análises',
        'statistics': 'Estatísticas'
    }
    
    @classmethod
    def scan_application(cls):
        """Scan Flask application and return discovered modules"""
        modules = defaultdict(lambda: {
            'nome': '',
            'nome_exibicao': '',
            'categoria': 'sistema',
            'funcoes': []
        })
        
        try:
            # Get all rules from Flask
            for rule in current_app.url_map.iter_rules():
                endpoint = rule.endpoint
                
                # Skip ignored endpoints
                if cls._should_ignore(endpoint):
                    continue
                
                # Extract module and function from endpoint
                module_name, function_name = cls._extract_module_function(endpoint)
                
                if module_name:
                    # Update module info
                    if module_name not in modules:
                        modules[module_name] = {
                            'nome': module_name,
                            'nome_exibicao': cls.MODULE_NAMES.get(module_name, module_name.title()),
                            'categoria': cls._get_category(module_name),
                            'funcoes': []
                        }
                    
                    # Add function if not already exists
                    function_display = cls.FUNCTION_NAMES.get(function_name, function_name.replace('_', ' ').title())
                    function_info = {
                        'nome': function_name,
                        'nome_exibicao': function_display,
                        'rota': str(rule),
                        'metodos': list(rule.methods - {'HEAD', 'OPTIONS'})
                    }
                    
                    # Avoid duplicates
                    if not any(f['nome'] == function_name for f in modules[module_name]['funcoes']):
                        modules[module_name]['funcoes'].append(function_info)
            
            logger.info(f"✅ Discovered {len(modules)} modules with functions")
            return dict(modules)
            
        except Exception as e:
            logger.error(f"Error scanning application: {e}")
            return {}
    
    @classmethod
    def _should_ignore(cls, endpoint):
        """Check if endpoint should be ignored"""
        if not endpoint:
            return True
            
        # Check blueprint
        if '.' in endpoint:
            blueprint = endpoint.split('.')[0]
            if blueprint in cls.IGNORED_BLUEPRINTS:
                return True
        
        # Check endpoint name
        endpoint_lower = endpoint.lower()
        return any(ignored in endpoint_lower for ignored in cls.IGNORED_ENDPOINTS)
    
    @classmethod
    def _extract_module_function(cls, endpoint):
        """Extract module and function names from endpoint"""
        if '.' in endpoint:
            # Blueprint.function format
            parts = endpoint.split('.')
            module = parts[0]
            function = parts[1] if len(parts) > 1 else 'index'
        else:
            # Try to extract from endpoint name
            parts = endpoint.split('_')
            if len(parts) > 1:
                module = parts[0]
                function = '_'.join(parts[1:])
            else:
                module = endpoint
                function = 'index'
        
        # Clean up names
        module = module.lower().replace('-', '_')
        function = function.lower().replace('-', '_')
        
        return module, function
    
    @classmethod
    def _get_category(cls, module_name):
        """Get category for module"""
        for category, modules in cls.MODULE_CATEGORIES.items():
            if module_name in modules:
                return category
        return 'sistema'
    
    @classmethod
    def initialize_permissions_from_scan(cls):
        """Initialize permission structure from scan results"""
        from app import db
        from app.permissions.models import PermissionCategory, ModuloSistema, FuncaoModulo
        
        modules = cls.scan_application()
        
        # Category display names
        category_names = {
            'operacional': 'Operacional',
            'financeiro': 'Financeiro',
            'cadastros': 'Cadastros',
            'relatorios': 'Relatórios',
            'sistema': 'Sistema'
        }
        
        # Create categories
        categories_created = {}
        ordem_cat = 1
        
        for cat_key, cat_name in category_names.items():
            category = PermissionCategory.query.filter_by(nome=cat_key).first()
            if not category:
                category = PermissionCategory(
                    nome=cat_key,
                    nome_exibicao=cat_name,
                    icone=f'fas fa-{cat_key}',
                    ordem=ordem_cat,
                    ativo=True
                )
                db.session.add(category)
                db.session.flush()
            categories_created[cat_key] = category
            ordem_cat += 1
        
        # Create modules and functions
        ordem_mod = 1
        for module_key, module_info in modules.items():
            # Get category
            category = categories_created.get(module_info['categoria'])
            if not category:
                category = categories_created['sistema']
            
            # Create or update module
            modulo = ModuloSistema.query.filter_by(codigo=module_key).first()
            if not modulo:
                modulo = ModuloSistema(
                    codigo=module_key,
                    nome=module_key,
                    nome_exibicao=module_info['nome_exibicao'],
                    descricao=f"Módulo de {module_info['nome_exibicao']}",
                    category_id=category.id,
                    icone=f'fas fa-{module_key}',
                    ordem=ordem_mod,
                    ativo=True
                )
                db.session.add(modulo)
                db.session.flush()
            ordem_mod += 1
            
            # Create functions
            ordem_func = 1
            for func_info in module_info['funcoes']:
                funcao = FuncaoModulo.query.filter_by(
                    modulo_id=modulo.id,
                    codigo=func_info['nome']
                ).first()
                
                if not funcao:
                    funcao = FuncaoModulo(
                        modulo_id=modulo.id,
                        codigo=func_info['nome'],
                        nome=func_info['nome'],
                        nome_exibicao=func_info['nome_exibicao'],
                        descricao=f"{func_info['nome_exibicao']} em {module_info['nome_exibicao']}",
                        rota=func_info['rota'],
                        ordem=ordem_func,
                        ativo=True
                    )
                    db.session.add(funcao)
                ordem_func += 1
        
        try:
            db.session.commit()
            logger.info("✅ Permissions structure initialized from scan")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing permissions: {e}")
            return False