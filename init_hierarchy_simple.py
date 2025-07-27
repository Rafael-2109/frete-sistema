#!/usr/bin/env python
"""
Simple Initialize Permission Hierarchy
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during initialization
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from app.permissions.models import PermissionCategory

def init_categories():
    """Initialize permission categories"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Criando categorias de permissões...")
        
        # Create categories
        categories = [
            ('operacional', 'Operacional', 'Módulos operacionais do dia a dia', 'fas fa-tasks', 1),
            ('financeiro', 'Financeiro', 'Gestão financeira e faturamento', 'fas fa-dollar-sign', 2),
            ('cadastros', 'Cadastros', 'Dados mestres e configurações', 'fas fa-database', 3),
            ('consultas', 'Consultas', 'Consultas e relatórios', 'fas fa-search', 4),
            ('carteira', 'Carteira & Estoque', 'Carteira de pedidos e estoque', 'fas fa-industry', 5),
            ('administrador', 'Administração', 'Módulos administrativos', 'fas fa-cog', 6)
        ]
        
        for nome, nome_exibicao, descricao, icone, ordem in categories:
            cat = PermissionCategory.query.filter_by(nome=nome).first()
            if not cat:
                cat = PermissionCategory(
                    nome=nome,
                    nome_exibicao=nome_exibicao,
                    descricao=descricao,
                    icone=icone,
                    ordem=ordem
                )
                db.session.add(cat)
                print(f"✅ Categoria criada: {nome_exibicao}")
            else:
                print(f"ℹ️ Categoria já existe: {nome_exibicao}")
        
        db.session.commit()
        print("✅ Categorias inicializadas com sucesso!")

if __name__ == "__main__":
    init_categories()