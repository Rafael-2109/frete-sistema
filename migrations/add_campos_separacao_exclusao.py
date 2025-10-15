"""
Script de migração para adicionar novos campos aos modelos CarteiraPrincipal e Separacao
Data: 2025-10-14
Autor: Sistema

NOVOS CAMPOS:
- CarteiraPrincipal.motivo_exclusao (Text): Motivo do cancelamento/exclusão da separação
- Separacao.obs_separacao (Text): Observações sobre a separação
- Separacao.falta_item (Boolean): Indica se falta item no estoque
- Separacao.falta_pagamento (Boolean): Indica se pagamento está pendente
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text

def adicionar_campos():
    app = create_app()

    with app.app_context():
        try:
            print("=" * 80)
            print("INICIANDO MIGRAÇÃO: Adição de campos de separação e exclusão")
            print("=" * 80)

            # 1. Adicionar motivo_exclusao em CarteiraPrincipal
            print("\n1. Verificando campo 'motivo_exclusao' em 'carteira_principal'...")
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='carteira_principal'
                AND column_name='motivo_exclusao'
            """))

            if resultado.fetchone() is None:
                print("   → Campo não existe. Adicionando...")
                db.session.execute(text("""
                    ALTER TABLE carteira_principal
                    ADD COLUMN motivo_exclusao TEXT NULL
                """))
                db.session.commit()
                print("   ✅ Campo 'motivo_exclusao' adicionado com sucesso!")
            else:
                print("   ⚠️  Campo 'motivo_exclusao' já existe. Pulando...")

            # 2. Adicionar obs_separacao em Separacao
            print("\n2. Verificando campo 'obs_separacao' em 'separacao'...")
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='separacao'
                AND column_name='obs_separacao'
            """))

            if resultado.fetchone() is None:
                print("   → Campo não existe. Adicionando...")
                db.session.execute(text("""
                    ALTER TABLE separacao
                    ADD COLUMN obs_separacao TEXT NULL
                """))
                db.session.commit()
                print("   ✅ Campo 'obs_separacao' adicionado com sucesso!")
            else:
                print("   ⚠️  Campo 'obs_separacao' já existe. Pulando...")

            # 3. Adicionar falta_item em Separacao
            print("\n3. Verificando campo 'falta_item' em 'separacao'...")
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='separacao'
                AND column_name='falta_item'
            """))

            if resultado.fetchone() is None:
                print("   → Campo não existe. Adicionando...")
                db.session.execute(text("""
                    ALTER TABLE separacao
                    ADD COLUMN falta_item BOOLEAN NOT NULL DEFAULT FALSE
                """))
                db.session.commit()
                print("   ✅ Campo 'falta_item' adicionado com sucesso!")
            else:
                print("   ⚠️  Campo 'falta_item' já existe. Pulando...")

            # 4. Adicionar falta_pagamento em Separacao
            print("\n4. Verificando campo 'falta_pagamento' em 'separacao'...")
            resultado = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='separacao'
                AND column_name='falta_pagamento'
            """))

            if resultado.fetchone() is None:
                print("   → Campo não existe. Adicionando...")
                db.session.execute(text("""
                    ALTER TABLE separacao
                    ADD COLUMN falta_pagamento BOOLEAN NOT NULL DEFAULT FALSE
                """))
                db.session.commit()
                print("   ✅ Campo 'falta_pagamento' adicionado com sucesso!")
            else:
                print("   ⚠️  Campo 'falta_pagamento' já existe. Pulando...")

            print("\n" + "=" * 80)
            print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
            print("=" * 80)
            print("\nResumo dos campos adicionados:")
            print("  • carteira_principal.motivo_exclusao (TEXT)")
            print("  • separacao.obs_separacao (TEXT)")
            print("  • separacao.falta_item (BOOLEAN)")
            print("  • separacao.falta_pagamento (BOOLEAN)")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print(f"\n❌ ERRO durante a migração: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    adicionar_campos()
