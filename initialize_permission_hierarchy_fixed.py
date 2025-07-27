#!/usr/bin/env python
"""
Initialize Permission Hierarchy (Fixed)
=====================================

Creates the hierarchical structure of categories, modules, and submodules
for the permission system with correct attribute names.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during initialization
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from app.permissions.models import (
    PermissionCategory, ModuloSistema, FuncaoModulo,
    Vendedor, EquipeVendas
)

def create_hierarchy():
    """Create the permission hierarchy"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Criando estrutura hierárquica de permissões...")
        
        # Create categories if they don't exist
        categories_data = [
            {
                'name': 'operacional',
                'display_name': 'Operacional',
                'description': 'Módulos operacionais do dia a dia',
                'icon': 'fas fa-tasks',
                'order_index': 1
            },
            {
                'name': 'financeiro',
                'display_name': 'Financeiro',
                'description': 'Gestão financeira e faturamento',
                'icon': 'fas fa-dollar-sign',
                'order_index': 2
            },
            {
                'name': 'cadastros',
                'display_name': 'Cadastros',
                'description': 'Dados mestres e configurações',
                'icon': 'fas fa-database',
                'order_index': 3
            },
            {
                'name': 'consultas',
                'display_name': 'Consultas',
                'description': 'Consultas e relatórios',
                'icon': 'fas fa-search',
                'order_index': 4
            },
            {
                'name': 'carteira',
                'display_name': 'Carteira & Estoque',
                'description': 'Carteira de pedidos e estoque',
                'icon': 'fas fa-industry',
                'order_index': 5
            },
            {
                'name': 'administrador',
                'display_name': 'Administração',
                'description': 'Módulos administrativos',
                'icon': 'fas fa-cog',
                'order_index': 6
            }
        ]
        
        categories = {}
        for cat_data in categories_data:
            category = PermissionCategory.query.filter_by(name=cat_data['name']).first()
            if not category:
                category = PermissionCategory(**cat_data)
                db.session.add(category)
                db.session.flush()
                print(f"✅ Categoria criada: {cat_data['display_name']}")
            else:
                print(f"ℹ️ Categoria já existe: {cat_data['display_name']}")
            categories[cat_data['name']] = category
        
        # Update existing modules with categories
        module_categories = {
            'pedidos': 'operacional',
            'separacao': 'operacional',
            'embarques': 'operacional',
            'portaria': 'operacional',
            'monitoramento': 'operacional',
            'faturamento': 'financeiro',
            'fretes': 'financeiro',
            'financeiro': 'financeiro',
            'transportadoras': 'cadastros',
            'localidades': 'cadastros',
            'veiculos': 'cadastros',
            'tabelas': 'cadastros',
            'vinculos': 'consultas',
            'carteira': 'carteira',
            'producao': 'carteira',
            'estoque': 'carteira',
            'usuarios': 'administrador',
            'permissions': 'administrador',
            'admin': 'administrador'
        }
        
        for module_name, category_name in module_categories.items():
            module = ModuloSistema.query.filter_by(nome=module_name).first()
            if module and category_name in categories:
                module.category_id = categories[category_name].id
                print(f"✅ Módulo '{module_name}' associado à categoria '{category_name}'")
        
        # Create some sample vendors if they don't exist
        vendors_data = [
            {
                'codigo': 'V001',
                'nome': 'Vendedor Principal',
                'razao_social': 'Vendedor Principal LTDA',
                'cnpj': '11.111.111/0001-11',
                'ativo': True
            },
            {
                'codigo': 'V002',
                'nome': 'Vendedor Sul',
                'razao_social': 'Vendedor Região Sul LTDA',
                'cnpj': '22.222.222/0001-22',
                'ativo': True
            },
            {
                'codigo': 'V003',
                'nome': 'Vendedor Norte',
                'razao_social': 'Vendedor Região Norte LTDA',
                'cnpj': '33.333.333/0001-33',
                'ativo': True
            }
        ]
        
        for vendor_data in vendors_data:
            vendor = Vendedor.query.filter_by(codigo=vendor_data['codigo']).first()
            if not vendor:
                vendor = Vendedor(**vendor_data)
                db.session.add(vendor)
                print(f"✅ Vendedor criado: {vendor_data['nome']}")
            else:
                print(f"ℹ️ Vendedor já existe: {vendor_data['nome']}")
        
        # Create some sample teams if they don't exist
        teams_data = [
            {
                'codigo': 'EQ001',
                'nome': 'Equipe Alpha',
                'descricao': 'Equipe de vendas região metropolitana',
                'gerente': 'João Silva',
                'ativo': True
            },
            {
                'codigo': 'EQ002',
                'nome': 'Equipe Beta',
                'descricao': 'Equipe de vendas interior',
                'gerente': 'Maria Santos',
                'ativo': True
            },
            {
                'codigo': 'EQ003',
                'nome': 'Equipe Gamma',
                'descricao': 'Equipe de grandes contas',
                'gerente': 'Pedro Oliveira',
                'ativo': True
            }
        ]
        
        for team_data in teams_data:
            team = EquipeVendas.query.filter_by(codigo=team_data['codigo']).first()
            if not team:
                team = EquipeVendas(**team_data)
                db.session.add(team)
                print(f"✅ Equipe criada: {team_data['nome']}")
            else:
                print(f"ℹ️ Equipe já existe: {team_data['nome']}")
        
        # Create functions (submodules) for some modules
        module_functions = {
            'faturamento': [
                ('dashboard', 'Dashboard', 'Visualizar dashboard de faturamento'),
                ('relatorios', 'Relatórios', 'Gerar relatórios de faturamento'),
                ('importar', 'Importar', 'Importar dados de faturamento'),
                ('exportar', 'Exportar', 'Exportar dados de faturamento')
            ],
            'carteira': [
                ('visualizar', 'Visualizar Carteira', 'Visualizar carteira de pedidos'),
                ('pre_separacao', 'Pré-Separação', 'Gerenciar pré-separação'),
                ('agrupados', 'Pedidos Agrupados', 'Visualizar pedidos agrupados'),
                ('montagem', 'Montagem de Cargas', 'Gerenciar montagem de cargas')
            ],
            'embarques': [
                ('listar', 'Listar Embarques', 'Visualizar lista de embarques'),
                ('criar', 'Criar Embarque', 'Criar novo embarque'),
                ('editar', 'Editar Embarque', 'Editar embarque existente'),
                ('imprimir', 'Imprimir Documentos', 'Imprimir documentos de embarque')
            ]
        }
        
        for module_name, functions in module_functions.items():
            module = ModuloSistema.query.filter_by(nome=module_name).first()
            if module:
                ordem = 1
                for func_nome, func_exibicao, func_descricao in functions:
                    function = FuncaoModulo.query.filter_by(
                        modulo_id=module.id,
                        nome=func_nome
                    ).first()
                    
                    if not function:
                        function = FuncaoModulo(
                            modulo_id=module.id,
                            nome=func_nome,
                            nome_exibicao=func_exibicao,
                            descricao=func_descricao,
                            ordem=ordem,
                            ativo=True
                        )
                        db.session.add(function)
                        print(f"✅ Função criada: {module_name}.{func_nome}")
                    else:
                        print(f"ℹ️ Função já existe: {module_name}.{func_nome}")
                    ordem += 1
        
        db.session.commit()
        
        print("\n🎉 Estrutura hierárquica criada com sucesso!")
        
        # Print summary
        print("\n📊 Resumo:")
        print(f"   - Categorias: {PermissionCategory.query.count()}")
        print(f"   - Módulos: {ModuloSistema.query.count()}")
        print(f"   - Funções: {FuncaoModulo.query.count()}")
        print(f"   - Vendedores: {Vendedor.query.count()}")
        print(f"   - Equipes: {EquipeVendas.query.count()}")

if __name__ == "__main__":
    create_hierarchy()