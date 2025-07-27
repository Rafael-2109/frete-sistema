#!/usr/bin/env python
"""
Create vendor and team tables for hierarchical permissions
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Disable Claude AI during migration
os.environ['SKIP_CLAUDE_AI'] = 'true'

from app import create_app, db
from sqlalchemy import text

def create_tables():
    """Create vendor and team tables"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Criando tabelas de vendedor e equipe...")
        
        # SQL para criar tabela vendedor
        create_vendedor_sql = """
        CREATE TABLE IF NOT EXISTS vendedor (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            nome VARCHAR(100) NOT NULL,
            razao_social VARCHAR(150),
            cnpj_cpf VARCHAR(20),
            email VARCHAR(100),
            telefone VARCHAR(20),
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            criado_por INTEGER REFERENCES usuarios(id)
        );
        """
        
        # SQL para criar tabela equipe_vendas
        create_equipe_sql = """
        CREATE TABLE IF NOT EXISTS equipe_vendas (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            gerente VARCHAR(100),
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            criado_por INTEGER REFERENCES usuarios(id)
        );
        """
        
        # SQL para criar tabela usuario_vendedor
        create_usuario_vendedor_sql = """
        CREATE TABLE IF NOT EXISTS usuario_vendedor (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            vendedor_id INTEGER NOT NULL REFERENCES vendedor(id),
            tipo_acesso VARCHAR(20) DEFAULT 'visualizar',
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, vendedor_id)
        );
        """
        
        # SQL para criar tabela usuario_equipe_vendas
        create_usuario_equipe_sql = """
        CREATE TABLE IF NOT EXISTS usuario_equipe_vendas (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
            equipe_id INTEGER NOT NULL REFERENCES equipe_vendas(id),
            cargo_equipe VARCHAR(50) DEFAULT 'Membro',
            tipo_acesso VARCHAR(20) DEFAULT 'membro',
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, equipe_id)
        );
        """
        
        try:
            # Criar tabelas
            db.session.execute(text(create_vendedor_sql))
            print("✅ Tabela 'vendedor' criada")
            
            db.session.execute(text(create_equipe_sql))
            print("✅ Tabela 'equipe_vendas' criada")
            
            db.session.execute(text(create_usuario_vendedor_sql))
            print("✅ Tabela 'usuario_vendedor' criada")
            
            db.session.execute(text(create_usuario_equipe_sql))
            print("✅ Tabela 'usuario_equipe_vendas' criada")
            
            db.session.commit()
            
            # Inserir alguns dados de exemplo
            print("\n📝 Inserindo dados de exemplo...")
            
            # Vendedor exemplo
            insert_vendedor_sql = """
            INSERT INTO vendedor (codigo, nome, razao_social, cnpj_cpf, email, telefone)
            VALUES ('V001', 'Vendedor Exemplo 1', 'Exemplo Ltda', '12.345.678/0001-90', 'vendedor1@example.com', '(11) 1234-5678')
            ON CONFLICT (codigo) DO NOTHING;
            """
            db.session.execute(text(insert_vendedor_sql))
            
            # Equipe exemplo
            insert_equipe_sql = """
            INSERT INTO equipe_vendas (codigo, nome, descricao, gerente)
            VALUES ('EQ001', 'Equipe Sul', 'Equipe de vendas região Sul', 'João Silva')
            ON CONFLICT (codigo) DO NOTHING;
            """
            db.session.execute(text(insert_equipe_sql))
            
            db.session.commit()
            print("✅ Dados de exemplo inseridos")
            
            # Verificar tabelas criadas
            print("\n📋 Verificando tabelas criadas:")
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('vendedor', 'equipe_vendas', 'usuario_vendedor', 'usuario_equipe_vendas')
                ORDER BY table_name
            """))
            
            for row in result:
                print(f"   ✅ {row[0]}")
            
            print("\n✅ Todas as tabelas foram criadas com sucesso!")
            print("\n🎯 Agora você pode acessar /permissions/hierarchical-manager")
            
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Erro ao criar tabelas: {e}")
            raise

if __name__ == "__main__":
    create_tables()