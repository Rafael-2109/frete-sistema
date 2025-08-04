#!/usr/bin/env python3
"""
Sistema de Permissões - Dados Iniciais (Seeds)
==============================================

Script para popular o banco de dados com dados iniciais do sistema de permissões.
Inclui categorias, módulos, submódulos e cenários de teste.

Uso:
    python seeds.py
    
Ou via Flask:
    flask run-seeds
"""

import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório pai ao path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.permissions.models_unified import (
    PermissionCategory, PermissionModule, PermissionSubModule,
    UserPermission, PermissionTemplate, PerfilUsuario,
    Vendedor, EquipeVendas, UserVendedor, UserEquipe,
    PermissionLog, BatchOperation
)
from app.auth.models import Usuario
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_permission_categories(db_session):
    """Criar categorias de permissão básicas"""
    logger.info("Criando categorias de permissão...")
    
    categories = [
        {
            'nome': 'operacional',
            'nome_exibicao': 'Operacional',
            'descricao': 'Módulos operacionais do dia a dia',
            'icone': 'fas fa-cogs',
            'cor': '#17a2b8',
            'ordem': 1
        },
        {
            'nome': 'financeiro',
            'nome_exibicao': 'Financeiro',
            'descricao': 'Controles financeiros e faturamento',
            'icone': 'fas fa-dollar-sign',
            'cor': '#28a745',
            'ordem': 2
        },
        {
            'nome': 'administrativo',
            'nome_exibicao': 'Administrativo',
            'descricao': 'Administração do sistema e usuários',
            'icone': 'fas fa-user-shield',
            'cor': '#dc3545',
            'ordem': 3
        },
        {
            'nome': 'relatorios',
            'nome_exibicao': 'Relatórios',
            'descricao': 'Relatórios e análises',
            'icone': 'fas fa-chart-bar',
            'cor': '#6f42c1',
            'ordem': 4
        },
        {
            'nome': 'integracao',
            'nome_exibicao': 'Integração',
            'descricao': 'Integrações externas e APIs',
            'icone': 'fas fa-exchange-alt',
            'cor': '#fd7e14',
            'ordem': 5
        }
    ]
    
    created_categories = {}
    
    for cat_data in categories:
        category = PermissionCategory.query.filter_by(nome=cat_data['nome']).first()
        
        if not category:
            category = PermissionCategory(**cat_data, criado_por=1)
            db_session.add(category)
            logger.info(f"✓ Categoria criada: {cat_data['nome_exibicao']}")
        else:
            logger.info(f"→ Categoria já existe: {cat_data['nome_exibicao']}")
        
        created_categories[cat_data['nome']] = category
    
    db_session.commit()
    return created_categories


def create_permission_modules(db_session, categories):
    """Criar módulos de permissão dentro das categorias"""
    logger.info("Criando módulos de permissão...")
    
    modules_data = [
        # Operacional
        {
            'category': 'operacional',
            'nome': 'carteira',
            'nome_exibicao': 'Carteira de Fretes',
            'descricao': 'Gestão da carteira de fretes',
            'icone': 'fas fa-truck',
            'cor': '#17a2b8',
            'ordem': 1
        },
        {
            'category': 'operacional',
            'nome': 'embarques',
            'nome_exibicao': 'Embarques',
            'descricao': 'Controle de embarques',
            'icone': 'fas fa-shipping-fast',
            'cor': '#17a2b8',
            'ordem': 2
        },
        {
            'category': 'operacional',
            'nome': 'estoque',
            'nome_exibicao': 'Estoque',
            'descricao': 'Controle de estoque',
            'icone': 'fas fa-boxes',
            'cor': '#17a2b8',
            'ordem': 3
        },
        {
            'category': 'operacional',
            'nome': 'portaria',
            'nome_exibicao': 'Portaria',
            'descricao': 'Controle de portaria',
            'icone': 'fas fa-door-open',
            'cor': '#17a2b8',
            'ordem': 4
        },
        # Financeiro
        {
            'category': 'financeiro',
            'nome': 'faturamento',
            'nome_exibicao': 'Faturamento',
            'descricao': 'Gestão de faturamento',
            'icone': 'fas fa-file-invoice-dollar',
            'cor': '#28a745',
            'ordem': 1
        },
        {
            'category': 'financeiro',
            'nome': 'fretes',
            'nome_exibicao': 'Fretes',
            'descricao': 'Gestão de fretes e valores',
            'icone': 'fas fa-calculator',
            'cor': '#28a745',
            'ordem': 2
        },
        # Administrativo
        {
            'category': 'administrativo',
            'nome': 'usuarios',
            'nome_exibicao': 'Usuários',
            'descricao': 'Gestão de usuários e permissões',
            'icone': 'fas fa-users',
            'cor': '#dc3545',
            'ordem': 1
        },
        {
            'category': 'administrativo',
            'nome': 'configuracoes',
            'nome_exibicao': 'Configurações',
            'descricao': 'Configurações do sistema',
            'icone': 'fas fa-cog',
            'cor': '#dc3545',
            'ordem': 2
        },
        # Relatórios
        {
            'category': 'relatorios',
            'nome': 'operacionais',
            'nome_exibicao': 'Relatórios Operacionais',
            'descricao': 'Relatórios operacionais',
            'icone': 'fas fa-chart-line',
            'cor': '#6f42c1',
            'ordem': 1
        },
        {
            'category': 'relatorios',
            'nome': 'financeiros',
            'nome_exibicao': 'Relatórios Financeiros',
            'descricao': 'Relatórios financeiros',
            'icone': 'fas fa-chart-pie',
            'cor': '#6f42c1',
            'ordem': 2
        },
        # Integração
        {
            'category': 'integracao',
            'nome': 'odoo',
            'nome_exibicao': 'Integração Odoo',
            'descricao': 'Integração com sistema Odoo',
            'icone': 'fas fa-sync',
            'cor': '#fd7e14',
            'ordem': 1
        }
    ]
    
    created_modules = {}
    
    for mod_data in modules_data:
        category = categories[mod_data.pop('category')]
        
        module = PermissionModule.query.filter_by(
            category_id=category.id,
            nome=mod_data['nome']
        ).first()
        
        if not module:
            module = PermissionModule(
                category_id=category.id,
                criado_por=1,
                **mod_data
            )
            db_session.add(module)
            logger.info(f"✓ Módulo criado: {mod_data['nome_exibicao']}")
        else:
            logger.info(f"→ Módulo já existe: {mod_data['nome_exibicao']}")
        
        created_modules[f"{category.nome}.{mod_data['nome']}"] = module
    
    db_session.commit()
    return created_modules


def create_permission_submodules(db_session, modules):
    """Criar submódulos (funções específicas)"""
    logger.info("Criando submódulos de permissão...")
    
    submodules_data = [
        # Carteira
        ('operacional.carteira', 'listar', 'Listar Carteira', 'Visualizar lista de fretes', '/carteira', 'NORMAL'),
        ('operacional.carteira', 'editar', 'Editar Frete', 'Editar informações do frete', '/carteira/editar/*', 'HIGH'),
        ('operacional.carteira', 'separacao', 'Separação', 'Gestão de separação', '/carteira/separacao/*', 'HIGH'),
        ('operacional.carteira', 'workspace', 'Workspace', 'Workspace de montagem', '/carteira/workspace/*', 'NORMAL'),
        
        # Embarques  
        ('operacional.embarques', 'listar', 'Listar Embarques', 'Visualizar embarques', '/embarques', 'NORMAL'),
        ('operacional.embarques', 'criar', 'Criar Embarque', 'Criar novo embarque', '/embarques/criar', 'HIGH'),
        ('operacional.embarques', 'editar', 'Editar Embarque', 'Editar embarque existente', '/embarques/editar/*', 'HIGH'),
        ('operacional.embarques', 'excluir', 'Excluir Embarque', 'Excluir embarque', '/embarques/excluir/*', 'CRITICAL'),
        
        # Estoque
        ('operacional.estoque', 'consultar', 'Consultar Estoque', 'Consultar produtos em estoque', '/estoque', 'NORMAL'),
        ('operacional.estoque', 'movimentar', 'Movimentar Estoque', 'Fazer movimentações', '/estoque/movimentar', 'HIGH'),
        ('operacional.estoque', 'ajustar', 'Ajustar Estoque', 'Fazer ajustes de estoque', '/estoque/ajustar', 'CRITICAL'),
        
        # Portaria
        ('operacional.portaria', 'entrada', 'Controle de Entrada', 'Registrar entrada de veículos', '/portaria/entrada', 'NORMAL'),
        ('operacional.portaria', 'saida', 'Controle de Saída', 'Registrar saída de veículos', '/portaria/saida', 'NORMAL'),
        
        # Faturamento
        ('financeiro.faturamento', 'listar', 'Listar Faturas', 'Visualizar faturas', '/faturamento', 'NORMAL'),
        ('financeiro.faturamento', 'gerar', 'Gerar Fatura', 'Gerar nova fatura', '/faturamento/gerar', 'HIGH'),
        ('financeiro.faturamento', 'aprovar', 'Aprovar Fatura', 'Aprovar fatura para envio', '/faturamento/aprovar/*', 'CRITICAL'),
        ('financeiro.faturamento', 'cancelar', 'Cancelar Fatura', 'Cancelar fatura', '/faturamento/cancelar/*', 'CRITICAL'),
        
        # Fretes
        ('financeiro.fretes', 'calcular', 'Calcular Frete', 'Calcular valor do frete', '/fretes/calcular', 'NORMAL'),
        ('financeiro.fretes', 'tabelas', 'Gerenciar Tabelas', 'Gerenciar tabelas de frete', '/fretes/tabelas', 'HIGH'),
        
        # Usuários
        ('administrativo.usuarios', 'listar', 'Listar Usuários', 'Visualizar usuários', '/usuarios', 'NORMAL'),
        ('administrativo.usuarios', 'criar', 'Criar Usuário', 'Criar novo usuário', '/usuarios/criar', 'HIGH'),
        ('administrativo.usuarios', 'editar', 'Editar Usuário', 'Editar usuário existente', '/usuarios/editar/*', 'HIGH'),
        ('administrativo.usuarios', 'permissoes', 'Gerenciar Permissões', 'Gerenciar permissões de usuários', '/usuarios/permissoes/*', 'CRITICAL'),
        ('administrativo.usuarios', 'excluir', 'Excluir Usuário', 'Excluir usuário', '/usuarios/excluir/*', 'CRITICAL'),
        
        # Configurações
        ('administrativo.configuracoes', 'sistema', 'Configurações do Sistema', 'Configurar parâmetros do sistema', '/configuracoes', 'CRITICAL'),
        ('administrativo.configuracoes', 'backup', 'Backup e Restore', 'Gerenciar backups', '/configuracoes/backup', 'CRITICAL'),
        
        # Relatórios Operacionais
        ('relatorios.operacionais', 'fretes', 'Relatório de Fretes', 'Relatório de movimentação de fretes', '/relatorios/fretes', 'NORMAL'),
        ('relatorios.operacionais', 'embarques', 'Relatório de Embarques', 'Relatório de embarques', '/relatorios/embarques', 'NORMAL'),
        ('relatorios.operacionais', 'estoque', 'Relatório de Estoque', 'Relatório de estoque', '/relatorios/estoque', 'NORMAL'),
        
        # Relatórios Financeiros
        ('relatorios.financeiros', 'faturamento', 'Relatório de Faturamento', 'Relatório financeiro de faturamento', '/relatorios/faturamento', 'HIGH'),
        ('relatorios.financeiros', 'receitas', 'Relatório de Receitas', 'Relatório de receitas', '/relatorios/receitas', 'HIGH'),
        
        # Integração Odoo
        ('integracao.odoo', 'sincronizar', 'Sincronizar Dados', 'Sincronizar dados com Odoo', '/integracao/odoo/sync', 'HIGH'),
        ('integracao.odoo', 'configurar', 'Configurar Integração', 'Configurar parâmetros de integração', '/integracao/odoo/config', 'CRITICAL'),
    ]
    
    created_submodules = {}
    
    for module_key, nome, nome_exibicao, descricao, route_pattern, critical_level in submodules_data:
        module = modules.get(module_key)
        if not module:
            logger.warning(f"Módulo não encontrado: {module_key}")
            continue
        
        submodule = PermissionSubModule.query.filter_by(
            module_id=module.id,
            nome=nome
        ).first()
        
        if not submodule:
            submodule = PermissionSubModule(
                module_id=module.id,
                nome=nome,
                nome_exibicao=nome_exibicao,
                descricao=descricao,
                route_pattern=route_pattern,
                critical_level=critical_level,
                criado_por=1,
                ordem=len(created_submodules) + 1
            )
            db_session.add(submodule)
            logger.info(f"✓ Submódulo criado: {module_key}.{nome}")
        else:
            logger.info(f"→ Submódulo já existe: {module_key}.{nome}")
        
        created_submodules[f"{module_key}.{nome}"] = submodule
    
    db_session.commit()
    return created_submodules


def create_permission_templates(db_session):
    """Criar templates de permissão pré-definidos"""
    logger.info("Criando templates de permissão...")
    
    templates_data = [
        {
            'nome': 'Operador Básico',
            'codigo': 'operador_basico',
            'descricao': 'Permissões básicas para operador do sistema',
            'categoria': 'roles',
            'template_data': {
                'CATEGORY': {
                    '1': {'can_view': True, 'can_edit': False}  # Operacional - somente visualização
                }
            }
        },
        {
            'nome': 'Supervisor Operacional',
            'codigo': 'supervisor_operacional',
            'descricao': 'Permissões de supervisão para área operacional',
            'categoria': 'roles',
            'template_data': {
                'CATEGORY': {
                    '1': {'can_view': True, 'can_edit': True}  # Operacional - edição completa
                }
            }
        },
        {
            'nome': 'Analista Financeiro',
            'codigo': 'analista_financeiro',
            'descricao': 'Permissões para analista da área financeira',
            'categoria': 'roles',
            'template_data': {
                'CATEGORY': {
                    '2': {'can_view': True, 'can_edit': True},  # Financeiro
                    '4': {'can_view': True, 'can_edit': False}  # Relatórios - somente visualização
                }
            }
        },
        {
            'nome': 'Administrador de Sistema',
            'codigo': 'admin_sistema',
            'descricao': 'Permissões administrativas completas',
            'categoria': 'roles',
            'template_data': {
                'CATEGORY': {
                    '3': {'can_view': True, 'can_edit': True, 'can_delete': True}  # Administrativo completo
                }
            }
        }
    ]
    
    created_templates = {}
    
    for template_data in templates_data:
        template = PermissionTemplate.query.filter_by(codigo=template_data['codigo']).first()
        
        if not template:
            template = PermissionTemplate(
                nome=template_data['nome'],
                codigo=template_data['codigo'],
                descricao=template_data['descricao'],
                categoria=template_data['categoria'],
                template_data=json.dumps(template_data['template_data']),
                criado_por=1
            )
            db_session.add(template)
            logger.info(f"✓ Template criado: {template_data['nome']}")
        else:
            logger.info(f"→ Template já existe: {template_data['nome']}")
        
        created_templates[template_data['codigo']] = template
    
    db_session.commit()
    return created_templates


def validate_system(db_session):
    """Validar se o sistema foi criado corretamente"""
    logger.info("Validando sistema de permissões...")
    
    # Contar registros criados
    stats = {
        'categories': PermissionCategory.query.count(),
        'modules': PermissionModule.query.count(),
        'submodules': PermissionSubModule.query.count(),
        'templates': PermissionTemplate.query.count(),
        'users': Usuario.query.filter_by(status='ativo').count(),
        'permissions': UserPermission.query.filter_by(ativo=True).count(),
        'logs': PermissionLog.query.count()
    }
    
    logger.info("📊 Estatísticas do sistema:")
    for key, value in stats.items():
        logger.info(f"  {key.capitalize()}: {value}")
    
    # Validar hierarquia
    if stats['categories'] > 0 and stats['modules'] > 0 and stats['submodules'] > 0:
        logger.info("✅ Hierarquia de permissões criada com sucesso")
    else:
        logger.error("❌ Problema na criação da hierarquia")
    
    # Validar templates
    if stats['templates'] > 0:
        logger.info("✅ Templates de permissão criados")
    else:
        logger.warning("⚠ Nenhum template criado")
    
    return stats


def main():
    """Função principal para executar a criação dos dados"""
    try:
        # Criar app Flask
        app = create_app()
        
        with app.app_context():
            logger.info("🚀 Iniciando criação de dados do sistema de permissões...")
            
            # Criar categorias
            categories = create_permission_categories(db.session)
            
            # Criar módulos
            modules = create_permission_modules(db.session, categories)
            
            # Criar submódulos
            submodules = create_permission_submodules(db.session, modules)
            
            # Criar templates
            templates = create_permission_templates(db.session)
            
            # Validar sistema
            stats = validate_system(db.session)
            
            logger.info("✅ Dados do sistema de permissões criados com sucesso!")
            logger.info("📋 Para testar o sistema:")
            logger.info("  1. Acesse /permissions/unified para a interface administrativa")
            logger.info("  2. Verifique os logs em /api/v1/permissions/statistics")
            logger.info("  3. Execute o script de migração: python migrate_permissions_final.py")
            
            return stats
            
    except Exception as e:
        logger.error(f"❌ Erro ao criar dados: {e}")
        raise


if __name__ == '__main__':
    main()