"""Padronizar lote_separacao_id para separacao_lote_id em carteira_principal e controle_cruzado_separacao

Revision ID: 818fc9fd1d77
Revises: 2ff2d45b36ff
Create Date: 2025-07-17 18:12:17.180045

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '818fc9fd1d77'
down_revision = '2ff2d45b36ff'
branch_labels = None
depends_on = None


def upgrade():
    """
    Padronizar campos lote_separacao_id para separacao_lote_id
    Converter Integer → String para consistência
    """
    
    # Verificar se estamos no PostgreSQL (Render) ou SQLite (Local)
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    try:
        # 1. CARTEIRA_PRINCIPAL: Renomear + Converter tipo
        print("🔄 Padronizando carteira_principal...")
        
        if dialect_name == 'postgresql':
            # PostgreSQL (Render)
            op.execute(text("""
                ALTER TABLE carteira_principal 
                ADD COLUMN separacao_lote_id VARCHAR(50);
            """))
            
            op.execute(text("""
                UPDATE carteira_principal 
                SET separacao_lote_id = CAST(lote_separacao_id AS VARCHAR(50)) 
                WHERE lote_separacao_id IS NOT NULL;
            """))
            
            op.execute(text("""
                DROP INDEX IF EXISTS idx_carteira_lote_separacao;
            """))
            
            op.execute(text("""
                ALTER TABLE carteira_principal 
                DROP COLUMN lote_separacao_id;
            """))
            
            op.execute(text("""
                CREATE INDEX idx_carteira_separacao_lote 
                ON carteira_principal(separacao_lote_id);
            """))
            
        else:
            # SQLite (Local) - Approach mais simples
            op.execute(text("""
                ALTER TABLE carteira_principal 
                ADD COLUMN separacao_lote_id VARCHAR(50);
            """))
            
            op.execute(text("""
                UPDATE carteira_principal 
                SET separacao_lote_id = CAST(lote_separacao_id AS TEXT) 
                WHERE lote_separacao_id IS NOT NULL;
            """))
        
        # 2. CONTROLE_CRUZADO_SEPARACAO: Mesmo processo
        print("🔄 Padronizando controle_cruzado_separacao...")
        
        if dialect_name == 'postgresql':
            op.execute(text("""
                ALTER TABLE controle_cruzado_separacao 
                ADD COLUMN separacao_lote_id VARCHAR(50);
            """))
            
            op.execute(text("""
                UPDATE controle_cruzado_separacao 
                SET separacao_lote_id = CAST(lote_separacao_id AS VARCHAR(50)) 
                WHERE lote_separacao_id IS NOT NULL;
            """))
            
            op.execute(text("""
                DROP INDEX IF EXISTS idx_controle_lote_pedido;
            """))
            
            op.execute(text("""
                ALTER TABLE controle_cruzado_separacao 
                DROP COLUMN lote_separacao_id;
            """))
            
            op.execute(text("""
                CREATE INDEX idx_controle_separacao_lote_pedido 
                ON controle_cruzado_separacao(separacao_lote_id, num_pedido);
            """))
            
        else:
            # SQLite
            op.execute(text("""
                ALTER TABLE controle_cruzado_separacao 
                ADD COLUMN separacao_lote_id VARCHAR(50);
            """))
            
            op.execute(text("""
                UPDATE controle_cruzado_separacao 
                SET separacao_lote_id = CAST(lote_separacao_id AS TEXT) 
                WHERE lote_separacao_id IS NOT NULL;
            """))
        
        print("✅ Padronização concluída com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro na migração: {e}")
        raise


def downgrade():
    """
    Reverter padronização (emergência)
    """
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    try:
        print("🔄 Revertendo padronização...")
        
        # Reverter CARTEIRA_PRINCIPAL
        if dialect_name == 'postgresql':
            op.execute(text("""
                ALTER TABLE carteira_principal 
                ADD COLUMN lote_separacao_id INTEGER;
            """))
            
            op.execute(text("""
                UPDATE carteira_principal 
                SET lote_separacao_id = CAST(separacao_lote_id AS INTEGER) 
                WHERE separacao_lote_id IS NOT NULL 
                AND separacao_lote_id ~ '^[0-9]+$';
            """))
            
            op.execute(text("""
                ALTER TABLE carteira_principal 
                DROP COLUMN separacao_lote_id;
            """))
        
        # Reverter CONTROLE_CRUZADO_SEPARACAO
        if dialect_name == 'postgresql':
            op.execute(text("""
                ALTER TABLE controle_cruzado_separacao 
                ADD COLUMN lote_separacao_id INTEGER;
            """))
            
            op.execute(text("""
                UPDATE controle_cruzado_separacao 
                SET lote_separacao_id = CAST(separacao_lote_id AS INTEGER) 
                WHERE separacao_lote_id IS NOT NULL 
                AND separacao_lote_id ~ '^[0-9]+$';
            """))
            
            op.execute(text("""
                ALTER TABLE controle_cruzado_separacao 
                DROP COLUMN separacao_lote_id;
            """))
        
        print("✅ Reversão concluída!")
        
    except Exception as e:
        print(f"❌ Erro na reversão: {e}")
        raise
