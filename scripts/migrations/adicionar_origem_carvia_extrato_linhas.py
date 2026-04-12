"""Migration: CarviaExtratoLinha.origem (W10 Nivel 2).

Adiciona campo `origem` em carvia_extrato_linhas para distinguir linhas
reais (OFX/CSV bancario) de linhas virtuais criadas pelo Fluxo de Caixa
(FC_VIRTUAL).

Contexto: W10 Nivel 2 da auditoria CarVia. FC passa a criar linhas
virtuais em vez de manipular CarviaContaMovimentacao diretamente. Assim
Conciliacao vira a unica SOT para pagamento.

Valores:
  - OFX        → linha importada de arquivo OFX (default, legacy)
  - CSV        → linha importada de arquivo CSV bancario
  - FC_VIRTUAL → linha virtual criada pelo Fluxo de Caixa

Backfill: todas as linhas existentes recebem origem='OFX' (comportamento
original).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def verificar_antes():
    """Verifica se a coluna ja existe."""
    existe = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'origem'
    """)).scalar()
    print(f"[BEFORE] carvia_extrato_linhas.origem = {'existe' if existe else 'NAO existe'}")

    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_extrato_linhas"
    )).scalar()
    print(f"[DATA] Total de linhas no extrato: {total}")

    return existe is not None


def executar_migration():
    """Executa a migration."""
    # 1. Adicionar coluna com default 'OFX' para backfill
    db.session.execute(db.text("""
        ALTER TABLE carvia_extrato_linhas
        ADD COLUMN IF NOT EXISTS origem VARCHAR(20) NOT NULL DEFAULT 'OFX'
    """))
    print("[OK] Coluna origem adicionada (default 'OFX')")

    # 2. Criar indice para consultas de filtro
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_extrato_origem
            ON carvia_extrato_linhas (origem)
    """))
    print("[OK] Indice ix_carvia_extrato_origem criado")

    # 3. Adicionar CHECK constraint para valores validos
    check_exists = db.session.execute(db.text("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'carvia_extrato_linhas'
        AND constraint_name = 'ck_carvia_extrato_origem'
    """)).scalar()

    if not check_exists:
        db.session.execute(db.text("""
            ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_origem
            CHECK (origem IN ('OFX', 'CSV', 'FC_VIRTUAL'))
        """))
        print("[OK] CHECK constraint ck_carvia_extrato_origem criado")

    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration."""
    # Coluna
    tipo = db.session.execute(db.text("""
        SELECT data_type FROM information_schema.columns
        WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'origem'
    """)).scalar()
    print(f"[AFTER] origem tipo = {tipo}")

    # Indice
    idx = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_extrato_linhas'
        AND indexname = 'ix_carvia_extrato_origem'
    """)).scalar()
    print(f"[AFTER] indice ix_carvia_extrato_origem = {'existe' if idx else 'NAO existe'}")

    # Distribuicao
    distrib = db.session.execute(db.text("""
        SELECT origem, COUNT(*) FROM carvia_extrato_linhas
        GROUP BY origem ORDER BY origem
    """)).fetchall()
    print(f"[DATA] Distribuicao por origem:")
    for row in distrib:
        print(f"  {row[0]}: {row[1]}")

    assert tipo == 'character varying', f"Tipo inesperado: {tipo}"
    assert idx is not None, "Indice nao foi criado"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        existe = verificar_antes()
        if existe:
            print("[SKIP] Coluna origem ja existe")
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
