"""Migration: indice parcial unique p/ evitar duplicacao de provisorio CARVIA.

Corrige BUG B1 da analise COT-76: a criacao do provisorio nao era idempotente,
gerando 2+ EmbarqueItems com mesmo (embarque_id, separacao_lote_id, provisorio=TRUE).

Index parcial: ate sobre status='ativo' AND provisorio=TRUE.
- itens cancelados podem coexistir (historico)
- multiplos provisorios distintos (carvia_cotacao_id distintos) no mesmo embarque sao OK
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


INDEX_NAME = 'uq_embarque_itens_provisorio_carvia_ativo'


def verificar_antes():
    existe = db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'embarque_itens' AND indexname = :i
    """), {'i': INDEX_NAME}).scalar()
    print(f"[BEFORE] index {INDEX_NAME} = {'existe' if existe else 'NAO existe'}")

    # Verifica se ha duplicatas pendentes que impediriam a criacao
    dup = db.session.execute(db.text("""
        SELECT embarque_id, separacao_lote_id, COUNT(*) AS qtd
        FROM embarque_itens
        WHERE status = 'ativo' AND provisorio = TRUE
        GROUP BY embarque_id, separacao_lote_id
        HAVING COUNT(*) > 1
        LIMIT 10
    """)).fetchall()
    if dup:
        print(f"[WARN] Ha {len(dup)} grupos de provisorios duplicados ATIVOS:")
        for row in dup:
            print(f"  embarque={row[0]} lote={row[1]} qtd={row[2]}")
        print("  Index nao pode ser criado ate dedup manual. Abortando.")
    return bool(existe), bool(dup)


def executar_migration():
    db.session.execute(db.text(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
            ON embarque_itens (embarque_id, separacao_lote_id)
            WHERE status = 'ativo' AND provisorio = TRUE
    """))
    print(f"[OK] Index {INDEX_NAME} criado")
    db.session.commit()


def verificar_depois():
    existe = db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'embarque_itens' AND indexname = :i
    """), {'i': INDEX_NAME}).scalar()
    print(f"[AFTER] index {INDEX_NAME} = {'existe' if existe else 'NAO existe'}")
    assert existe, "Index nao foi criado"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe, tem_dup = verificar_antes()
        if ja_existe:
            print("[SKIP] index ja existe")
        elif tem_dup:
            print("[ABORT] resolva duplicacao manualmente antes de aplicar")
            sys.exit(1)
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
