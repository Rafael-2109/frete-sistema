#!/usr/bin/env python3
"""
Script para corrigir a tabela projecao_estoque_cache
Adiciona a coluna dia_offset que está faltando
"""

from app import create_app, db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

with app.app_context():
    print("=== Corrigindo tabela projecao_estoque_cache ===\n")
    
    try:
        # 1. Verificar se a coluna dia_offset existe
        result = db.session.execute(text("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'projecao_estoque_cache' 
            AND column_name = 'dia_offset'
        """))
        
        has_dia_offset = result.scalar() > 0
        
        if not has_dia_offset:
            print("❌ Coluna dia_offset não encontrada. Adicionando...")
            
            # 2. Adicionar a coluna
            db.session.execute(text("""
                ALTER TABLE projecao_estoque_cache 
                ADD COLUMN dia_offset INTEGER
            """))
            
            print("✅ Coluna dia_offset adicionada")
            
            # 3. Preencher valores baseados em data_projecao
            print("📝 Preenchendo valores de dia_offset...")
            
            # Primeiro, obter a menor data para cada produto
            db.session.execute(text("""
                UPDATE projecao_estoque_cache p1
                SET dia_offset = (
                    SELECT COUNT(DISTINCT p2.data_projecao)
                    FROM projecao_estoque_cache p2
                    WHERE p2.cod_produto = p1.cod_produto
                    AND p2.data_projecao < p1.data_projecao
                )
            """))
            
            print("✅ Valores preenchidos")
            
            # 4. Tornar a coluna NOT NULL
            db.session.execute(text("""
                ALTER TABLE projecao_estoque_cache 
                ALTER COLUMN dia_offset SET NOT NULL
            """))
            
            print("✅ Coluna definida como NOT NULL")
            
            db.session.commit()
            print("\n✅ Tabela corrigida com sucesso!")
            
        else:
            print("✅ Coluna dia_offset já existe. Nada a fazer.")
            
        # 5. Verificar estrutura final
        print("\n=== Estrutura final da tabela ===")
        result = db.session.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'projecao_estoque_cache'
            ORDER BY ordinal_position
        """))
        
        for col in result:
            print(f"- {col[0]}: {col[1]} (nullable: {col[2]})")
            
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Erro ao corrigir tabela: {e}")
        import traceback
        traceback.print_exc()


from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("=== Corrigindo tabela projecao_estoque_cache ===\n")

    try:
        # Verificar se a coluna dia_offset existe
        result = db.session.execute(text("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = 'projecao_estoque_cache' 
        AND column_name = 'dia_offset'
        """))
        has_dia_offset = result.scalar() > 0

        if not has_dia_offset:
            print("Coluna dia_offset não encontrada. Adicionando...")

            # Adicionar a coluna
            db.session.execute(text("""
                    ALTER TABLE projecao_estoque_cache 
                    ADD COLUMN dia_offset INTEGER DEFAULT 0
                """))

            print("Coluna adicionada com sucesso!")

            # Preencher valores baseados em data_projecao
            print("Preenchendo valores de dia_offset...")

            db.session.execute(text("""
                UPDATE projecao_estoque_cache p1
                SET dia_offset = (
                    SELECT COUNT(DISTINCT p2.data_projecao)
                    FROM projecao_estoque_cache p2
                    WHERE p2.cod_produto = p1.cod_produto
                    AND p2.data_projecao < p1.data_projecao
                )
            """))

            # Tornar a coluna NOT NULL
            db.session.execute(text("""
                ALTER TABLE projecao_estoque_cache 
                ALTER COLUMN dia_offset SET NOT NULL
            """))

            db.session.commit()
            print("Tabela corrigida com sucesso!")

        else:
            print("Coluna dia_offset já existe.")

    except Exception as e:
        db.session.rollback()
        print(f"Erro: {e}")