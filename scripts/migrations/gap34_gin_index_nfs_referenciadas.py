"""
GAP-34: Criar indice GIN em carvia_operacoes.nfs_referenciadas_json.

Otimiza queries que buscam operacoes por conteudo do JSON (linking retroativo).
Com indice GIN, cast::text LIKE e containment @> sao acelerados.

Idempotente: IF NOT EXISTS.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def run():
    from app import create_app, db

    app = create_app()
    with app.app_context():
        # Verificar se ja existe
        result = db.session.execute(db.text("""
            SELECT COUNT(*) FROM pg_indexes
            WHERE indexname = 'ix_carvia_operacoes_nfs_ref_json_gin'
        """))
        if (result.scalar() or 0) > 0:
            print("[OK] Indice GIN ja existe. Nada a fazer.")
            return

        print("[ANTES] Criando indice GIN em carvia_operacoes.nfs_referenciadas_json...")
        db.session.execute(db.text("""
            CREATE INDEX ix_carvia_operacoes_nfs_ref_json_gin
            ON carvia_operacoes
            USING GIN (nfs_referenciadas_json)
            WHERE nfs_referenciadas_json IS NOT NULL
        """))
        db.session.commit()
        print("[OK] Indice GIN criado com sucesso.")


if __name__ == '__main__':
    run()
