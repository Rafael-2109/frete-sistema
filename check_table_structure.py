#!/usr/bin/env python3
"""Script para verificar estrutura da tabela projecao_estoque_cache"""

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== Verificando estrutura da tabela projecao_estoque_cache ===\n")
    
    # Verifica se a tabela existe
    result = db.session.execute(text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.tables 
            WHERE table_name = 'projecao_estoque_cache'
        )
    """))
    
    table_exists = result.scalar()
    print(f"Tabela existe: {table_exists}")
    
    if table_exists:
        print("\n=== Colunas da tabela ===")
        result = db.session.execute(text("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_name = 'projecao_estoque_cache'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        for col in columns:
            print(f"- {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
            
        # Verifica especificamente a coluna dia_offset
        print("\n=== Verificando coluna dia_offset ===")
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'projecao_estoque_cache' 
            AND column_name = 'dia_offset'
        """))
        
        has_dia_offset = result.scalar() > 0
        print(f"Coluna dia_offset existe: {has_dia_offset}")
        
        # Verifica o modelo SQLAlchemy
        print("\n=== Verificando modelo ProjecaoEstoqueCache ===")
        try:
            from app.estoque.models_cache import ProjecaoEstoqueCache
            print(f"Modelo encontrado: {ProjecaoEstoqueCache.__tablename__}")
            print("\nColunas no modelo:")
            for column in ProjecaoEstoqueCache.__table__.columns:
                print(f"- {column.name}: {column.type}")
        except ImportError:
            print("Modelo ProjecaoEstoqueCache não encontrado em models_cache!")
            # Tenta outro import
            try:
                from app.carteira.models import ProjecaoEstoqueCache
                print(f"Modelo encontrado em carteira.models: {ProjecaoEstoqueCache.__tablename__}")
                print("\nColunas no modelo:")
                for column in ProjecaoEstoqueCache.__table__.columns:
                    print(f"- {column.name}: {column.type}")
            except ImportError:
                print("Modelo ProjecaoEstoqueCache não encontrado em carteira.models!")
        except Exception as e:
            print(f"Erro ao verificar modelo: {e}")