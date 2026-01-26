"""
Migration: Adicionar campos de rastreamento de mudanças em POs
==============================================================

Novos campos em validacao_nf_po_dfe:
- po_modificada_apos_validacao: Flag Boolean (True = PO usada foi modificada)
- ultima_validacao_em: Timestamp da última validação executada
- po_ids_usados: JSON com IDs das POs usadas nesta validação

Índice:
- idx_validacao_po_modificada: (po_modificada_apos_validacao, status)

Propósito:
- Permitir skip inteligente no job de validação
- Só reprocessar DFEs quando POs usadas foram modificadas

Executar local:
    source .venv/bin/activate && python scripts/migrations/add_po_tracking_fields.py

SQL para Render:
    ALTER TABLE validacao_nf_po_dfe
    ADD COLUMN IF NOT EXISTS po_modificada_apos_validacao BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS ultima_validacao_em TIMESTAMP NULL,
    ADD COLUMN IF NOT EXISTS po_ids_usados TEXT NULL;

    CREATE INDEX IF NOT EXISTS idx_validacao_po_modificada
    ON validacao_nf_po_dfe(po_modificada_apos_validacao, status);
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Executa a migration para adicionar campos de rastreamento de POs"""
    app = create_app()
    with app.app_context():
        try:
            print("🔄 Iniciando migration: add_po_tracking_fields")

            # Verificar se campos já existem
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe'
                AND column_name IN ('po_modificada_apos_validacao', 'ultima_validacao_em', 'po_ids_usados')
            """))
            campos_existentes = [r[0] for r in resultado.fetchall()]

            if 'po_modificada_apos_validacao' not in campos_existentes:
                print("  + Adicionando campo po_modificada_apos_validacao...")
                db.session.execute(text("""
                    ALTER TABLE validacao_nf_po_dfe
                    ADD COLUMN po_modificada_apos_validacao BOOLEAN DEFAULT FALSE NOT NULL
                """))
            else:
                print("  ✓ Campo po_modificada_apos_validacao já existe")

            if 'ultima_validacao_em' not in campos_existentes:
                print("  + Adicionando campo ultima_validacao_em...")
                db.session.execute(text("""
                    ALTER TABLE validacao_nf_po_dfe
                    ADD COLUMN ultima_validacao_em TIMESTAMP NULL
                """))
            else:
                print("  ✓ Campo ultima_validacao_em já existe")

            if 'po_ids_usados' not in campos_existentes:
                print("  + Adicionando campo po_ids_usados...")
                db.session.execute(text("""
                    ALTER TABLE validacao_nf_po_dfe
                    ADD COLUMN po_ids_usados TEXT NULL
                """))
            else:
                print("  ✓ Campo po_ids_usados já existe")

            # Criar índice composto
            print("  + Criando índice idx_validacao_po_modificada...")
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_validacao_po_modificada
                ON validacao_nf_po_dfe(po_modificada_apos_validacao, status)
            """))

            db.session.commit()
            print("✅ Migration executada com sucesso!")

            # Verificar resultado
            resultado = db.session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'validacao_nf_po_dfe'
                AND column_name IN ('po_modificada_apos_validacao', 'ultima_validacao_em', 'po_ids_usados')
                ORDER BY column_name
            """))

            print("\n📋 Campos adicionados:")
            for row in resultado.fetchall():
                print(f"   - {row[0]}: {row[1]} (nullable={row[2]}, default={row[3]})")

        except Exception as e:
            print(f"❌ Erro na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
