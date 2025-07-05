"""adicionar_status_agendamento

Revision ID: e468e43c3f66
Revises: 5b695f58d103
Create Date: 2025-06-17 20:09:41.533338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e468e43c3f66'
down_revision = '5b695f58d103'
branch_labels = None
depends_on = None


def upgrade():
    # Verificar se a tabela existe e se as colunas já existem
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Verificar se a tabela existe
    if 'agendamentos_entrega' not in inspector.get_table_names():
        print("⚠️ Tabela 'agendamentos_entrega' não existe - pulando migração")
        return
    
    # Obter colunas existentes
    colunas_existentes = [col['name'] for col in inspector.get_columns('agendamentos_entrega')]
    print(f"🔍 Colunas existentes: {colunas_existentes}")
    
    # PRIMEIRO: Adicionar todas as colunas
    
    # Adicionar campo status aos agendamentos (só se não existir)
    if 'status' not in colunas_existentes:
        op.add_column('agendamentos_entrega', sa.Column('status', sa.String(20), nullable=True))
        print("✅ Coluna 'status' adicionada")
    else:
        print("ℹ️ Coluna 'status' já existe - pulando")
    
    # Adicionar campos de confirmação (só se não existirem)
    if 'confirmado_por' not in colunas_existentes:
        op.add_column('agendamentos_entrega', sa.Column('confirmado_por', sa.String(100), nullable=True))
        print("✅ Coluna 'confirmado_por' adicionada")
    else:
        print("ℹ️ Coluna 'confirmado_por' já existe - pulando")
        
    if 'confirmado_em' not in colunas_existentes:
        op.add_column('agendamentos_entrega', sa.Column('confirmado_em', sa.DateTime, nullable=True))
        print("✅ Coluna 'confirmado_em' adicionada")
    else:
        print("ℹ️ Coluna 'confirmado_em' já existe - pulando")
        
    if 'observacoes_confirmacao' not in colunas_existentes:
        op.add_column('agendamentos_entrega', sa.Column('observacoes_confirmacao', sa.Text, nullable=True))
        print("✅ Coluna 'observacoes_confirmacao' adicionada")
    else:
        print("ℹ️ Coluna 'observacoes_confirmacao' já existe - pulando")
    
    # SEGUNDO: Fazer os UPDATEs (agora as colunas já existem)
    
    # Atualizar todos os registros existentes para 'confirmado'
    # (agendamentos antigos só eram registrados quando já confirmados)
    op.execute("UPDATE agendamentos_entrega SET status = 'confirmado' WHERE status IS NULL OR status = ''")
    print("✅ Agendamentos existentes marcados como 'confirmado' (processo antigo)")
    
    # Preencher campos de confirmação para agendamentos existentes
    op.execute("""UPDATE agendamentos_entrega 
                  SET confirmado_por = 'Sistema Legacy', 
                      confirmado_em = criado_em 
                  WHERE status = 'confirmado' AND confirmado_por IS NULL""")
    print("✅ Campos de confirmação preenchidos para agendamentos legacy")
    
    print("🎉 Migração concluída com sucesso!")


def downgrade():
    # Remover campos adicionados
    op.drop_column('agendamentos_entrega', 'observacoes_confirmacao')
    op.drop_column('agendamentos_entrega', 'confirmado_em')
    op.drop_column('agendamentos_entrega', 'confirmado_por')
    op.drop_column('agendamentos_entrega', 'status')
