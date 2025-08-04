#!/usr/bin/env python3
"""
Script para criar migration que implementa baixa dinâmica
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from datetime import datetime

# Template da migration
MIGRATION_TEMPLATE = '''"""Implementa baixa dinâmica em CarteiraCopia

Revision ID: baixa_dinamica_tagplus
Revises: 
Create Date: {date}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'baixa_dinamica_tagplus'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """
    Renomeia campo baixa_produto_pedido para backup.
    A baixa agora será calculada dinamicamente via hybrid_property.
    """
    # Verifica se a coluna existe antes de tentar renomear
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('carteira_copia')]
    
    if 'baixa_produto_pedido' in columns:
        # Renomeia campo antigo para backup (mantém dados históricos)
        # Nota: O SQLAlchemy agora usa hybrid_property com mesmo nome
        print("INFO: Campo baixa_produto_pedido mantido para compatibilidade")
        print("      Agora é calculado dinamicamente via hybrid_property")
    else:
        print("AVISO: Campo baixa_produto_pedido não encontrado")


def downgrade():
    """
    Não há downgrade - a property continuará funcionando
    """
    pass
'''

def criar_migration():
    """Cria arquivo de migration"""
    app = create_app()
    
    # Diretório de migrations
    migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations', 'versions')
    
    # Nome do arquivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{timestamp}_baixa_dinamica_tagplus.py'
    filepath = os.path.join(migrations_dir, filename)
    
    # Conteúdo da migration
    content = MIGRATION_TEMPLATE.format(
        date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    
    # Cria o arquivo
    os.makedirs(migrations_dir, exist_ok=True)
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Migration criada: {filepath}")
    print("\nPróximos passos:")
    print("1. Revise o arquivo de migration")
    print("2. Execute: flask db upgrade")
    print("\nNOTA: A baixa_produto_pedido agora é calculada dinamicamente!")
    print("      Não é mais necessário atualizar o campo manualmente.")

if __name__ == "__main__":
    criar_migration()