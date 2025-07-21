"""Fix pre-separacao system advanced

Revision ID: fix_pre_sep_system
Revises: 76bbd63e3bed
Create Date: 2025-07-21 19:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import func

# revision identifiers, used by Alembic.
revision = 'fix_pre_sep_system'
down_revision = '76bbd63e3bed'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Verificar se a tabela pre_separacao_item existe
    # Se não existir, criar a estrutura completa
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if not inspector.has_table('pre_separacao_item'):
        # Criar tabela completa se não existir
        op.create_table('pre_separacao_item',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('num_pedido', sa.String(length=50), nullable=False),
            sa.Column('cod_produto', sa.String(length=50), nullable=False),
            sa.Column('cnpj_cliente', sa.String(length=20), nullable=True),
            sa.Column('nome_produto', sa.String(length=255), nullable=True),
            sa.Column('qtd_original_carteira', sa.Numeric(precision=15, scale=3), nullable=False),
            sa.Column('qtd_selecionada_usuario', sa.Numeric(precision=15, scale=3), nullable=False),
            sa.Column('qtd_restante_calculada', sa.Numeric(precision=15, scale=3), nullable=False),
            sa.Column('valor_original_item', sa.Numeric(precision=15, scale=2), nullable=True),
            sa.Column('peso_original_item', sa.Numeric(precision=15, scale=3), nullable=True),
            sa.Column('hash_item_original', sa.String(length=128), nullable=True),
            sa.Column('data_expedicao_editada', sa.Date(), nullable=False),  # OBRIGATÓRIO
            sa.Column('data_agendamento_editada', sa.Date(), nullable=True),
            sa.Column('protocolo_editado', sa.String(length=50), nullable=True),
            sa.Column('observacoes_usuario', sa.Text(), nullable=True),
            sa.Column('recomposto', sa.Boolean(), nullable=True),
            sa.Column('data_recomposicao', sa.DateTime(), nullable=True),
            sa.Column('recomposto_por', sa.String(length=100), nullable=True),
            sa.Column('versao_carteira_original', sa.String(length=50), nullable=True),
            sa.Column('versao_carteira_recomposta', sa.String(length=50), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=True),
            sa.Column('tipo_envio', sa.String(length=10), nullable=True),
            sa.Column('data_criacao', sa.DateTime(), nullable=True),
            sa.Column('criado_por', sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Criar índices básicos
        op.create_index(op.f('ix_pre_separacao_item_num_pedido'), 'pre_separacao_item', ['num_pedido'], unique=False)
        op.create_index(op.f('ix_pre_separacao_item_cod_produto'), 'pre_separacao_item', ['cod_produto'], unique=False)
        op.create_index(op.f('ix_pre_separacao_item_cnpj_cliente'), 'pre_separacao_item', ['cnpj_cliente'], unique=False)
        op.create_index(op.f('ix_pre_separacao_item_recomposto'), 'pre_separacao_item', ['recomposto'], unique=False)
        op.create_index(op.f('ix_pre_separacao_item_status'), 'pre_separacao_item', ['status'], unique=False)
        
    else:
        # Tabela existe, aplicar alterações necessárias
        columns = [col['name'] for col in inspector.get_columns('pre_separacao_item')]
        
        with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
            # Verificar e tornar data_expedicao_editada obrigatório
            if 'data_expedicao_editada' in columns:
                # Primeiro, popular campos NULL com data atual se existirem
                op.execute("UPDATE pre_separacao_item SET data_expedicao_editada = CURRENT_DATE WHERE data_expedicao_editada IS NULL")
                
                # Alterar coluna para NOT NULL
                batch_op.alter_column('data_expedicao_editada',
                                     existing_type=sa.Date(),
                                     nullable=False)
            else:
                # Adicionar coluna se não existir
                batch_op.add_column(sa.Column('data_expedicao_editada', sa.Date(), nullable=False, server_default='2025-01-01'))
                batch_op.alter_column('data_expedicao_editada', server_default=None)
    
    # 2. Remover constraints antigas problemáticas
    try:
        with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
            # Tentar remover constraints antigas que podem estar impedindo múltiplas pré-separações
            batch_op.drop_constraint('pre_separacao_itens_pedido_produto_unique', type_='unique')
    except:
        pass  # Constraint pode não existir
    
    # 3. Criar nova constraint única composta (contexto único)
    with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_pre_sep_context',  # Nome curto para evitar problemas
            ['num_pedido', 'cod_produto', 'data_expedicao_editada', 'data_agendamento_editada', 'protocolo_editado']
        )
    
    # 4. Criar índices de performance
    op.create_index('idx_pre_sep_exp_date', 'pre_separacao_item', 
                   ['cod_produto', 'data_expedicao_editada', 'status'])
    
    op.create_index('idx_pre_sep_dashboard', 'pre_separacao_item', 
                   ['num_pedido', 'status', 'data_criacao'])
    
    op.create_index('idx_pre_sep_recomp', 'pre_separacao_item', 
                   ['recomposto', 'hash_item_original'])

def downgrade():
    # Remover índices criados
    try:
        op.drop_index('idx_pre_sep_recomp', table_name='pre_separacao_item')
        op.drop_index('idx_pre_sep_dashboard', table_name='pre_separacao_item')
        op.drop_index('idx_pre_sep_exp_date', table_name='pre_separacao_item')
    except:
        pass
    
    # Remover constraint única
    try:
        with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
            batch_op.drop_constraint('uq_pre_sep_context', type_='unique')
    except:
        pass
    
    # Reverter campo data_expedicao_editada para nullable
    try:
        with op.batch_alter_table('pre_separacao_item', schema=None) as batch_op:
            batch_op.alter_column('data_expedicao_editada',
                                 existing_type=sa.Date(),
                                 nullable=True)
    except:
        pass