"""
Migration: Add Vendor and Team Associations
==========================================

This migration adds support for:
- Multiple vendor associations per user
- Multiple sales team associations per user
- Permission inheritance based on vendor/team

Run this migration after backing up your database:
python migrations/add_vendor_team_associations.py
"""

from app import create_app, db
from app.permissions.models import (
    Vendedor, EquipeVendas, UsuarioVendedor, UsuarioEquipeVendas,
    PermissaoVendedor, PermissaoEquipe
)
from app.auth.models import Usuario
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create new tables for vendor and team associations"""
    try:
        # Create Vendedor table
        logger.info("Creating vendedor table...")
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS vendedor (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nome VARCHAR(100) NOT NULL,
                razao_social VARCHAR(200),
                cnpj_cpf VARCHAR(18),
                email VARCHAR(120),
                telefone VARCHAR(20),
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                criado_por INTEGER REFERENCES usuarios(id)
            );
        """))
        
        # Create EquipeVendas table
        logger.info("Creating equipe_vendas table...")
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS equipe_vendas (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) UNIQUE NOT NULL,
                nome VARCHAR(100) NOT NULL,
                descricao VARCHAR(255),
                gerente_id INTEGER REFERENCES usuarios(id),
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                criado_por INTEGER REFERENCES usuarios(id)
            );
        """))
        
        # Update UsuarioVendedor table (drop and recreate with new structure)
        logger.info("Updating usuario_vendedor table...")
        db.session.execute(text("DROP TABLE IF EXISTS usuario_vendedor CASCADE;"))
        db.session.execute(text("""
            CREATE TABLE usuario_vendedor (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
                tipo_acesso VARCHAR(20) DEFAULT 'visualizar',
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                adicionado_por INTEGER REFERENCES usuarios(id),
                adicionado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                observacoes VARCHAR(255),
                CONSTRAINT uq_usuario_vendedor UNIQUE (usuario_id, vendedor_id)
            );
            
            CREATE INDEX idx_usuario_vendedor_ativo ON usuario_vendedor(usuario_id, ativo);
            CREATE INDEX idx_vendedor_lookup ON usuario_vendedor(vendedor_id, ativo);
        """))
        
        # Update UsuarioEquipeVendas table (drop and recreate with new structure)
        logger.info("Updating usuario_equipe_vendas table...")
        db.session.execute(text("DROP TABLE IF EXISTS usuario_equipe_vendas CASCADE;"))
        db.session.execute(text("""
            CREATE TABLE usuario_equipe_vendas (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
                cargo_equipe VARCHAR(50),
                tipo_acesso VARCHAR(20) DEFAULT 'membro',
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                adicionado_por INTEGER REFERENCES usuarios(id),
                adicionado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                observacoes VARCHAR(255),
                CONSTRAINT uq_usuario_equipe UNIQUE (usuario_id, equipe_id)
            );
            
            CREATE INDEX idx_usuario_equipe_ativo ON usuario_equipe_vendas(usuario_id, ativo);
            CREATE INDEX idx_equipe_lookup ON usuario_equipe_vendas(equipe_id, ativo);
        """))
        
        # Create PermissaoVendedor table
        logger.info("Creating permissao_vendedor table...")
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS permissao_vendedor (
                id SERIAL PRIMARY KEY,
                vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
                funcao_id INTEGER NOT NULL REFERENCES funcao_modulo(id),
                pode_visualizar BOOLEAN DEFAULT FALSE NOT NULL,
                pode_editar BOOLEAN DEFAULT FALSE NOT NULL,
                concedida_por INTEGER REFERENCES usuarios(id),
                concedida_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                CONSTRAINT uq_permissao_vendedor_funcao UNIQUE (vendedor_id, funcao_id)
            );
            
            CREATE INDEX idx_permissao_vendedor_ativo ON permissao_vendedor(vendedor_id, ativo);
        """))
        
        # Create PermissaoEquipe table
        logger.info("Creating permissao_equipe table...")
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS permissao_equipe (
                id SERIAL PRIMARY KEY,
                equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
                funcao_id INTEGER NOT NULL REFERENCES funcao_modulo(id),
                pode_visualizar BOOLEAN DEFAULT FALSE NOT NULL,
                pode_editar BOOLEAN DEFAULT FALSE NOT NULL,
                concedida_por INTEGER REFERENCES usuarios(id),
                concedida_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                CONSTRAINT uq_permissao_equipe_funcao UNIQUE (equipe_id, funcao_id)
            );
            
            CREATE INDEX idx_permissao_equipe_ativo ON permissao_equipe(equipe_id, ativo);
        """))
        
        db.session.commit()
        logger.info("✅ Tables created successfully!")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error creating tables: {e}")
        raise

def migrate_existing_data():
    """Migrate existing vendor data from usuarios table"""
    try:
        logger.info("Starting data migration...")
        
        # Get all unique vendors from usuarios table
        usuarios_com_vendedor = Usuario.query.filter(
            Usuario.vendedor_vinculado.isnot(None),
            Usuario.vendedor_vinculado != ''
        ).all()
        
        vendedores_criados = {}
        
        # Create vendors from unique vendedor_vinculado values
        vendedores_unicos = set()
        for user in usuarios_com_vendedor:
            if user.vendedor_vinculado:
                vendedores_unicos.add(user.vendedor_vinculado)
        
        logger.info(f"Found {len(vendedores_unicos)} unique vendors to migrate")
        
        for vendedor_nome in vendedores_unicos:
            # Create vendor
            vendedor = Vendedor(
                codigo=vendedor_nome.replace(' ', '_').upper(),
                nome=vendedor_nome,
                ativo=True
            )
            db.session.add(vendedor)
            db.session.flush()  # Get the ID
            vendedores_criados[vendedor_nome] = vendedor.id
            logger.info(f"Created vendor: {vendedor_nome}")
        
        # Associate users with their vendors
        for user in usuarios_com_vendedor:
            if user.vendedor_vinculado in vendedores_criados:
                associacao = UsuarioVendedor(
                    usuario_id=user.id,
                    vendedor_id=vendedores_criados[user.vendedor_vinculado],
                    tipo_acesso='visualizar' if user.perfil == 'vendedor' else 'editar',
                    ativo=True
                )
                db.session.add(associacao)
                logger.info(f"Associated user {user.email} with vendor {user.vendedor_vinculado}")
        
        # Create default sales teams
        equipes_padrao = [
            {'codigo': 'VENDAS_DIRETAS', 'nome': 'Vendas Diretas', 'descricao': 'Equipe de vendas diretas'},
            {'codigo': 'VENDAS_INTERNAS', 'nome': 'Vendas Internas', 'descricao': 'Equipe de vendas internas'},
            {'codigo': 'GRANDES_CONTAS', 'nome': 'Grandes Contas', 'descricao': 'Equipe de grandes contas'}
        ]
        
        for equipe_data in equipes_padrao:
            equipe = EquipeVendas(**equipe_data)
            db.session.add(equipe)
            logger.info(f"Created team: {equipe_data['nome']}")
        
        db.session.commit()
        logger.info("✅ Data migration completed successfully!")
        
        # Print summary
        total_vendors = Vendedor.query.count()
        total_teams = EquipeVendas.query.count()
        total_associations = UsuarioVendedor.query.count()
        
        logger.info(f"""
        Migration Summary:
        - Total vendors created: {total_vendors}
        - Total teams created: {total_teams}
        - Total user-vendor associations: {total_associations}
        """)
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error migrating data: {e}")
        raise

def add_sample_permissions():
    """Add sample permissions for vendors and teams"""
    try:
        logger.info("Adding sample permissions...")
        
        # Get some vendors and teams
        vendor = Vendedor.query.first()
        equipe = EquipeVendas.query.first()
        
        if vendor:
            # Add permissions for vendor
            from app.permissions.models import FuncaoModulo
            
            # Give vendors permission to view orders
            funcao_carteira_listar = FuncaoModulo.query.filter_by(
                nome='listar'
            ).join(FuncaoModulo.modulo).filter_by(
                nome='carteira'
            ).first()
            
            if funcao_carteira_listar:
                perm_vendor = PermissaoVendedor(
                    vendedor_id=vendor.id,
                    funcao_id=funcao_carteira_listar.id,
                    pode_visualizar=True,
                    pode_editar=False
                )
                db.session.add(perm_vendor)
                logger.info(f"Added permission for vendor {vendor.nome}")
        
        if equipe:
            # Add permissions for team
            from app.permissions.models import FuncaoModulo
            
            # Give teams permission to view monitoring
            funcao_monit_listar = FuncaoModulo.query.filter_by(
                nome='listar'
            ).join(FuncaoModulo.modulo).filter_by(
                nome='monitoramento'
            ).first()
            
            if funcao_monit_listar:
                perm_equipe = PermissaoEquipe(
                    equipe_id=equipe.id,
                    funcao_id=funcao_monit_listar.id,
                    pode_visualizar=True,
                    pode_editar=False
                )
                db.session.add(perm_equipe)
                logger.info(f"Added permission for team {equipe.nome}")
        
        db.session.commit()
        logger.info("✅ Sample permissions added!")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"❌ Error adding sample permissions: {e}")

def main():
    """Run the migration"""
    app = create_app()
    
    with app.app_context():
        logger.info("Starting vendor/team associations migration...")
        
        # Create tables
        create_tables()
        
        # Migrate existing data
        migrate_existing_data()
        
        # Add sample permissions
        add_sample_permissions()
        
        logger.info("🎉 Migration completed successfully!")

if __name__ == '__main__':
    main()