"""
Fix para Embarque 3307:
1. Corrige data_prevista_embarque corrompida (0261-12-20 -> NULL)
2. Corrige CNPJ dos itens 8240 e 8241 (28.158.175/0001-40 -> 04.139.940/0001-17)
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from sqlalchemy import text


def fix_embarque_3307():
    app = create_app()
    with app.app_context():
        try:
            # 1. Corrigir data_prevista_embarque corrompida
            result1 = db.session.execute(text("""
                UPDATE embarques
                SET data_prevista_embarque = NULL
                WHERE numero = 3307
            """))
            print(f"✅ data_prevista_embarque corrigida: {result1.rowcount} registro(s) atualizado(s)")

            # 2. Corrigir CNPJ dos itens
            result2 = db.session.execute(text("""
                UPDATE embarque_itens
                SET cnpj_cliente = '04.139.940/0001-17'
                WHERE id IN (8240, 8241)
            """))
            print(f"✅ CNPJ dos itens corrigido: {result2.rowcount} registro(s) atualizado(s)")

            db.session.commit()
            print("\n✅ Correções aplicadas com sucesso!")

        except Exception as e:
            print(f"❌ Erro: {e}")
            db.session.rollback()


if __name__ == '__main__':
    fix_embarque_3307()
