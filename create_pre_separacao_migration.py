#!/usr/bin/env python3
"""
Script para criar migração do sistema de pré-separação avançado
"""

import os
import sys
from datetime import datetime

def create_migration_commands():
    print("COMANDOS PARA CRIAR MIGRACAO PRE-SEPARACAO AVANCADO")
    print("=" * 70)
    print()
    
    print("1. ATIVAR AMBIENTE VIRTUAL (se necessário):")
    print("   source venv/bin/activate  # Linux/Mac")
    print("   venv\\Scripts\\activate     # Windows")
    print()
    
    print("2. CRIAR NOVA MIGRACAO:")
    print("   flask db migrate -m 'Implementar sistema pre-separacao avancado'")
    print()
    
    print("3. APLICAR MIGRACAO:")
    print("   flask db upgrade")
    print()
    
    print("4. VERIFICAR STATUS:")
    print("   flask db current")
    print("   flask db show")
    print()
    
    print("CONTEUDO ESPERADO NA MIGRACAO:")
    print("-" * 50)
    
    migration_content = '''"""Implementar sistema pre-separacao avancado

Revision ID: [gerado_automaticamente]
Revises: remover_constraint_unica_pre_separacao
Create Date: [data_atual]

"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Tornar data_expedicao_editada obrigatório (NOT NULL)
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        # Se a coluna já existe, alterar para NOT NULL
        batch_op.alter_column('data_expedicao_editada',
                              existing_type=sa.Date(),
                              nullable=False)
    
    # 2. Criar constraint única composta para contexto único
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_pre_separacao_contexto_unico',
            ['num_pedido', 'cod_produto', 'data_expedicao_editada', 
             'data_agendamento_editada', 'protocolo_editado']
        )
    
    # 3. Criar índices de performance
    op.create_index('idx_pre_sep_data_expedicao', 
                   'pre_separacao_item', 
                   ['cod_produto', 'data_expedicao_editada', 'status'])
    
    op.create_index('idx_pre_sep_dashboard', 
                   'pre_separacao_item', 
                   ['num_pedido', 'status', 'data_criacao'])
    
    op.create_index('idx_pre_sep_recomposicao', 
                   'pre_separacao_item', 
                   ['recomposto', 'hash_item_original'])

def downgrade():
    # Remover índices
    op.drop_index('idx_pre_sep_recomposicao', table_name='pre_separacao_item')
    op.drop_index('idx_pre_sep_dashboard', table_name='pre_separacao_item')
    op.drop_index('idx_pre_sep_data_expedicao', table_name='pre_separacao_item')
    
    # Remover constraint única
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        batch_op.drop_constraint('uq_pre_separacao_contexto_unico', type_='unique')
    
    # Reverter campo para nullable
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        batch_op.alter_column('data_expedicao_editada',
                              existing_type=sa.Date(),
                              nullable=True)
'''
    
    print(migration_content)
    print("-" * 50)
    print()
    
    print("VERIFICACAO APOS MIGRACAO:")
    print("-" * 30)
    print("1. Executar: python verificar_coluna_db.py")
    print("2. Ou usar o SQL: psql -f verificar_coluna.sql")
    print("3. Ou no ambiente de produção: usar painel Render")
    print()
    
    print("COMANDOS PARA PRODUCAO (RENDER):")
    print("-" * 30)
    print("1. Commit e push das alterações")
    print("2. No painel Render, executar:")
    print("   flask db migrate")
    print("   flask db upgrade")
    print()

def check_current_state():
    print("ESTADO ATUAL DOS ARQUIVOS:")
    print("=" * 40)
    
    # Verificar se migrations existem
    if os.path.exists('migrations/versions'):
        files = os.listdir('migrations/versions')
        py_files = [f for f in files if f.endswith('.py')]
        print(f"OK - {len(py_files)} arquivos de migracao encontrados")
        
        # Último arquivo
        if py_files:
            py_files.sort()
            print(f"  Ultimo: {py_files[-1]}")
    
    # Verificar modelo
    if os.path.exists('app/carteira/models.py'):
        print("OK - Modelo PreSeparacaoItem atualizado")
        
        with open('app/carteira/models.py', 'r') as f:
            content = f.read()
            
        if 'nullable=False' in content and 'data_expedicao_editada' in content:
            print("OK - Campo obrigatorio definido no modelo")
        if 'uq_pre_separacao_contexto_unico' in content:
            print("OK - Constraint unica definida no modelo")
    
    print()

def main():
    print("GUIA PARA IMPLEMENTAR COLUNA data_expedicao_editada")
    print("=" * 60)
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    
    check_current_state()
    create_migration_commands()
    
    print("IMPORTANTE:")
    print("-" * 20)
    print("- O modelo Python ja esta correto")
    print("- Falta apenas aplicar no banco de dados")
    print("- Use os comandos acima para criar/aplicar a migracao")
    print("- Teste em desenvolvimento antes de producao")

if __name__ == "__main__":
    main()