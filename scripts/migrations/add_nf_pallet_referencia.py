"""
Migration: Adiciona campos nf_pallet_referencia e nf_pallet_origem em embarque_itens

Esses campos rastreiam qual NF de pallet cobre cada NF de venda:
- nf_pallet_referencia: Número da NF de pallet que cobre esta NF de venda
- nf_pallet_origem: 'EMBARQUE' se veio da transportadora, 'ITEM' se foi específico do cliente

Data: 04/01/2026
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("Migration: Adicionando campos de FK para NF de pallet")
            print("=" * 60)

            # 1. Adicionar campo nf_pallet_referencia
            print("\n[1/2] Adicionando campo nf_pallet_referencia...")
            try:
                db.session.execute(text("""
                    ALTER TABLE embarque_itens
                    ADD COLUMN IF NOT EXISTS nf_pallet_referencia VARCHAR(20)
                """))
                print("  ✓ Campo nf_pallet_referencia adicionado")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("  → Campo nf_pallet_referencia já existe")
                else:
                    raise

            # 2. Adicionar campo nf_pallet_origem
            print("\n[2/2] Adicionando campo nf_pallet_origem...")
            try:
                db.session.execute(text("""
                    ALTER TABLE embarque_itens
                    ADD COLUMN IF NOT EXISTS nf_pallet_origem VARCHAR(10)
                """))
                print("  ✓ Campo nf_pallet_origem adicionado")
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                    print("  → Campo nf_pallet_origem já existe")
                else:
                    raise

            db.session.commit()
            print("\n" + "=" * 60)
            print("Migration concluída com sucesso!")
            print("=" * 60)

        except Exception as e:
            print(f"\n[ERRO] Falha na migration: {e}")
            db.session.rollback()
            raise


if __name__ == '__main__':
    executar_migration()
