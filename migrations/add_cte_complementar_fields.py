"""
Migration: Adicionar Campos de CTe Complementar
================================================

OBJETIVO:
    Adicionar campos para identificar e relacionar CTes complementares

CAMPOS ADICIONADOS:
    - tipo_cte: Tipo do CTe (0=Normal, 1=Complementar, 2=Anulação, 3=Substituto)
    - cte_complementa_chave: Chave do CTe que está sendo complementado
    - cte_complementa_id: ID do CTe original (FK self-referencial)
    - motivo_complemento: Motivo do complemento

ÍNDICES:
    - idx_cte_tipo
    - idx_cte_complementa_chave
    - idx_cte_complementa_id

AUTOR: Sistema de Fretes
DATA: 15/11/2025
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos_cte_complementar():
    """Adiciona campos de CTe complementar na tabela conhecimento_transporte"""
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("🔧 MIGRATION: Adicionar Campos de CTe Complementar")
        print("=" * 80)

        try:
            # 1. Verificar se os campos já existem
            print("\n📋 Verificando campos existentes...")
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'conhecimento_transporte'
                AND column_name IN ('tipo_cte', 'cte_complementa_chave', 'cte_complementa_id', 'motivo_complemento')
            """))
            campos_existentes = [row[0] for row in resultado]

            if len(campos_existentes) > 0:
                print(f"⚠️  Alguns campos já existem: {', '.join(campos_existentes)}")
                resposta = input("Deseja continuar e adicionar apenas os campos faltantes? (s/n): ")
                if resposta.lower() != 's':
                    print("❌ Operação cancelada pelo usuário")
                    return

            # 2. Adicionar campo tipo_cte
            if 'tipo_cte' not in campos_existentes:
                print("\n📝 Adicionando campo 'tipo_cte'...")
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD COLUMN tipo_cte VARCHAR(1) DEFAULT '0'
                """))
                print("   ✅ Campo 'tipo_cte' adicionado")
            else:
                print("   ⏭️  Campo 'tipo_cte' já existe")

            # 3. Adicionar campo cte_complementa_chave
            if 'cte_complementa_chave' not in campos_existentes:
                print("\n📝 Adicionando campo 'cte_complementa_chave'...")
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD COLUMN cte_complementa_chave VARCHAR(44)
                """))
                print("   ✅ Campo 'cte_complementa_chave' adicionado")
            else:
                print("   ⏭️  Campo 'cte_complementa_chave' já existe")

            # 4. Adicionar campo cte_complementa_id
            if 'cte_complementa_id' not in campos_existentes:
                print("\n📝 Adicionando campo 'cte_complementa_id'...")
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD COLUMN cte_complementa_id INTEGER
                """))
                print("   ✅ Campo 'cte_complementa_id' adicionado")
            else:
                print("   ⏭️  Campo 'cte_complementa_id' já existe")

            # 5. Adicionar campo motivo_complemento
            if 'motivo_complemento' not in campos_existentes:
                print("\n📝 Adicionando campo 'motivo_complemento'...")
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD COLUMN motivo_complemento TEXT
                """))
                print("   ✅ Campo 'motivo_complemento' adicionado")
            else:
                print("   ⏭️  Campo 'motivo_complemento' já existe")

            # 6. Criar índices
            print("\n📊 Criando índices...")

            # Índice para tipo_cte
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_cte_tipo
                    ON conhecimento_transporte(tipo_cte)
                """))
                print("   ✅ Índice 'idx_cte_tipo' criado")
            except Exception as e:
                print(f"   ⚠️  Índice 'idx_cte_tipo' pode já existir: {e}")

            # Índice para cte_complementa_chave
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_cte_complementa_chave
                    ON conhecimento_transporte(cte_complementa_chave)
                """))
                print("   ✅ Índice 'idx_cte_complementa_chave' criado")
            except Exception as e:
                print(f"   ⚠️  Índice 'idx_cte_complementa_chave' pode já existir: {e}")

            # Índice para cte_complementa_id
            try:
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_cte_complementa_id
                    ON conhecimento_transporte(cte_complementa_id)
                """))
                print("   ✅ Índice 'idx_cte_complementa_id' criado")
            except Exception as e:
                print(f"   ⚠️  Índice 'idx_cte_complementa_id' pode já existir: {e}")

            # 7. Adicionar constraint de foreign key (self-referencial)
            print("\n🔗 Adicionando constraint de foreign key...")
            try:
                db.session.execute(text("""
                    ALTER TABLE conhecimento_transporte
                    ADD CONSTRAINT fk_cte_complementa_id
                    FOREIGN KEY (cte_complementa_id)
                    REFERENCES conhecimento_transporte(id)
                    ON DELETE SET NULL
                """))
                print("   ✅ Foreign key 'fk_cte_complementa_id' adicionada")
            except Exception as e:
                print(f"   ⚠️  Foreign key pode já existir: {e}")

            # 8. Commit
            db.session.commit()
            print("\n" + "=" * 80)
            print("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\n📋 Resumo:")
            print("   - Campo 'tipo_cte' adicionado (VARCHAR(1))")
            print("   - Campo 'cte_complementa_chave' adicionado (VARCHAR(44))")
            print("   - Campo 'cte_complementa_id' adicionado (INTEGER + FK)")
            print("   - Campo 'motivo_complemento' adicionado (TEXT)")
            print("   - 3 índices criados")
            print("   - 1 foreign key adicionada")
            print("\n🎯 Próximo passo: Executar sincronização de CTes para processar os XMLs")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO na migration: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    adicionar_campos_cte_complementar()
