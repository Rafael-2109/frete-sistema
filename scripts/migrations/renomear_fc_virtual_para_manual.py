"""Migration: renomear FC_VIRTUAL -> MANUAL + adicionar conta_origem.

Refatoracao da W10 Nivel 2 (auditoria CarVia — Sprint 4 followup).

Contexto
--------
A primeira iteracao de W10 N2 criava linhas virtuais com `origem='FC_VIRTUAL'`
sem campo para identificar em QUAL conta o pagamento foi feito. Isso dava
rastreabilidade zero: qualquer pagamento fora do extrato bancario da CarVia
virava uma "caixa preta".

Nova semantica:
  - OFX    -> linha importada de arquivo OFX (default, legacy)
  - CSV    -> linha importada de arquivo CSV bancario
  - MANUAL -> lancamento manual fora do extrato bancario CarVia
              Exige `conta_origem` preenchido (texto livre).
              Ex: "Conta Pessoal Rafael", "Empresa Nacom Goya", "Dinheiro/Caixa"

Linhas MANUAL admitem edicao (PATCH) e delecao (DELETE) enquanto nao
conciliadas — ao contrario de OFX/CSV que sao imutaveis.

Mudancas DDL
------------
1. DROP CHECK constraint antiga (`ck_carvia_extrato_origem` com FC_VIRTUAL)
2. UPDATE `origem='FC_VIRTUAL'` -> `origem='MANUAL'`
3. ADD CHECK constraint nova (`ck_carvia_extrato_origem` com MANUAL)
4. ADD COLUMN `conta_origem VARCHAR(100) NULL`
5. UPDATE `arquivo_ofx='FC_VIRTUAL'` -> `arquivo_ofx='MANUAL'`
6. Backfill `conta_origem='(a informar)'` WHERE origem='MANUAL'
7. ADD CHECK partial `ck_carvia_extrato_manual_conta`:
   (origem != 'MANUAL' OR conta_origem IS NOT NULL)
   Enforcement DB para prevenir linhas MANUAL sem conta_origem.
   CRITICO: rodar APOS o backfill (step 6 do .py / step 4 do .sql).

Idempotencia: verificamos CHECK constraint e presenca do valor 'FC_VIRTUAL'
antes de cada operacao — safe para re-execucao.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def verificar_antes():
    """Verifica estado antes da migration."""
    # 1. Coluna origem existe?
    col_origem = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'origem'
    """)).scalar()
    print(f"[BEFORE] coluna origem = {'existe' if col_origem else 'NAO existe (erro!)'}")

    if not col_origem:
        raise RuntimeError(
            "Coluna 'origem' nao existe — migration anterior "
            "'adicionar_origem_carvia_extrato_linhas' precisa rodar primeiro."
        )

    # 2. Coluna conta_origem ja existe?
    col_conta = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'conta_origem'
    """)).scalar()
    print(f"[BEFORE] coluna conta_origem = {'existe (skip ADD)' if col_conta else 'NAO existe'}")

    # 3. Quantos registros com FC_VIRTUAL?
    qtd_fc_virtual = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carvia_extrato_linhas WHERE origem = 'FC_VIRTUAL'
    """)).scalar()
    print(f"[DATA] linhas com origem='FC_VIRTUAL': {qtd_fc_virtual}")

    qtd_manual = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carvia_extrato_linhas WHERE origem = 'MANUAL'
    """)).scalar()
    print(f"[DATA] linhas com origem='MANUAL': {qtd_manual}")

    # 4. Constraint atual aceita quais valores?
    check_def = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conname = 'ck_carvia_extrato_origem'
    """)).scalar()
    print(f"[BEFORE] CHECK definicao atual: {check_def}")

    # 5. Partial CHECK para enforcement conta_origem obrigatorio em MANUAL
    check_manual_conta = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conname = 'ck_carvia_extrato_manual_conta'
    """)).scalar()
    print(
        "[BEFORE] CHECK ck_carvia_extrato_manual_conta = "
        f"{'existe (skip ADD)' if check_manual_conta else 'NAO existe'}"
    )

    return {
        'col_conta_existe': col_conta is not None,
        'qtd_fc_virtual': qtd_fc_virtual,
        'check_tem_manual': check_def and 'MANUAL' in (check_def or ''),
        'check_manual_conta_existe': check_manual_conta is not None,
    }


def executar_migration(estado):
    """Executa migration em ordem segura."""

    # 1. DROP CHECK antigo (se nao aceita MANUAL)
    if not estado['check_tem_manual']:
        print("[STEP 1] Dropando CHECK constraint antigo...")
        db.session.execute(db.text("""
            ALTER TABLE carvia_extrato_linhas
            DROP CONSTRAINT IF EXISTS ck_carvia_extrato_origem
        """))
        print("[OK] CHECK antigo removido")

    # 2. UPDATE origem FC_VIRTUAL -> MANUAL
    if estado['qtd_fc_virtual'] > 0:
        print(f"[STEP 2] Renomeando {estado['qtd_fc_virtual']} linhas FC_VIRTUAL -> MANUAL...")
        res = db.session.execute(db.text("""
            UPDATE carvia_extrato_linhas
               SET origem = 'MANUAL'
             WHERE origem = 'FC_VIRTUAL'
        """))
        print(f"[OK] {res.rowcount} linhas renomeadas origem -> MANUAL")
    else:
        print("[STEP 2] Nenhuma linha FC_VIRTUAL para renomear (skip)")

    # 3. ADD COLUMN conta_origem
    if not estado['col_conta_existe']:
        print("[STEP 3] Adicionando coluna conta_origem...")
        db.session.execute(db.text("""
            ALTER TABLE carvia_extrato_linhas
            ADD COLUMN IF NOT EXISTS conta_origem VARCHAR(100) NULL
        """))
        print("[OK] coluna conta_origem adicionada")
    else:
        print("[STEP 3] conta_origem ja existe (skip)")

    # 4. Backfill conta_origem em linhas MANUAL sem valor
    print("[STEP 4] Backfill conta_origem='(a informar)' em linhas MANUAL sem valor...")
    res = db.session.execute(db.text("""
        UPDATE carvia_extrato_linhas
           SET conta_origem = '(a informar)'
         WHERE origem = 'MANUAL'
           AND (conta_origem IS NULL OR conta_origem = '')
    """))
    print(f"[OK] {res.rowcount} linhas com conta_origem backfilled")

    # 5. UPDATE arquivo_ofx FC_VIRTUAL -> MANUAL (consistencia)
    print("[STEP 5] Atualizando arquivo_ofx='FC_VIRTUAL' -> 'MANUAL'...")
    res = db.session.execute(db.text("""
        UPDATE carvia_extrato_linhas
           SET arquivo_ofx = 'MANUAL'
         WHERE arquivo_ofx = 'FC_VIRTUAL'
    """))
    print(f"[OK] {res.rowcount} linhas com arquivo_ofx atualizado")

    # 6. ADD CHECK constraint novo (OFX | CSV | MANUAL)
    if not estado['check_tem_manual']:
        print("[STEP 6] Adicionando CHECK constraint novo com valores OFX|CSV|MANUAL...")
        db.session.execute(db.text("""
            ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_origem
            CHECK (origem IN ('OFX', 'CSV', 'MANUAL'))
        """))
        print("[OK] CHECK constraint criado")

    # 7. ADD CHECK partial `ck_carvia_extrato_manual_conta` — enforcement DB
    #    para (origem='MANUAL' => conta_origem IS NOT NULL).
    #    CRITICO: DEPOIS do backfill (step 4) — senao a constraint falha
    #    em linhas MANUAL pre-existentes com conta_origem NULL.
    if not estado['check_manual_conta_existe']:
        print(
            "[STEP 7] Adicionando CHECK ck_carvia_extrato_manual_conta "
            "(origem != 'MANUAL' OR conta_origem IS NOT NULL)..."
        )
        db.session.execute(db.text("""
            ALTER TABLE carvia_extrato_linhas
            ADD CONSTRAINT ck_carvia_extrato_manual_conta
            CHECK (origem != 'MANUAL' OR conta_origem IS NOT NULL)
        """))
        print("[OK] CHECK ck_carvia_extrato_manual_conta criado")
    else:
        print("[STEP 7] ck_carvia_extrato_manual_conta ja existe (skip)")

    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration.

    IMPORTANTE: rodado APOS db.session.commit() em executar_migration().
    Se uma assertion falhar aqui, as mudancas JA estao persistidas. A
    recuperacao depende da IDEMPOTENCIA da migration — basta rerodar apos
    investigar a causa da assertion. Defense-in-depth, nao rollback.
    """
    # 1. Constraint
    check_def = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conname = 'ck_carvia_extrato_origem'
    """)).scalar()
    print(f"[AFTER] CHECK definicao: {check_def}")

    # 1b. Partial CHECK manual_conta
    check_manual_conta = db.session.execute(db.text("""
        SELECT pg_get_constraintdef(oid) FROM pg_constraint
        WHERE conname = 'ck_carvia_extrato_manual_conta'
    """)).scalar()
    print(f"[AFTER] CHECK ck_carvia_extrato_manual_conta: {check_manual_conta}")

    # 2. Coluna conta_origem
    col_conta = db.session.execute(db.text("""
        SELECT column_name, data_type, character_maximum_length
          FROM information_schema.columns
         WHERE table_name = 'carvia_extrato_linhas' AND column_name = 'conta_origem'
    """)).first()
    print(f"[AFTER] conta_origem: {col_conta}")

    # 3. Distribuicao origem
    distrib = db.session.execute(db.text("""
        SELECT origem, COUNT(*) FROM carvia_extrato_linhas
        GROUP BY origem ORDER BY origem
    """)).fetchall()
    print(f"[AFTER] distribuicao origem:")
    for row in distrib:
        print(f"  {row[0]}: {row[1]}")

    # 4. Ha FC_VIRTUAL remanescente?
    qtd_fc_virtual = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carvia_extrato_linhas WHERE origem = 'FC_VIRTUAL'
    """)).scalar()

    # 5. Linhas MANUAL com conta_origem NULL (deveria ser 0 apos backfill)
    qtd_manual_sem_conta = db.session.execute(db.text("""
        SELECT COUNT(*) FROM carvia_extrato_linhas
        WHERE origem = 'MANUAL' AND (conta_origem IS NULL OR conta_origem = '')
    """)).scalar()
    print(f"[AFTER] MANUAL sem conta_origem: {qtd_manual_sem_conta}")

    assert check_def and 'MANUAL' in check_def, \
        f"CHECK constraint nao contem MANUAL: {check_def}"
    assert check_def and 'FC_VIRTUAL' not in check_def, \
        f"CHECK constraint ainda contem FC_VIRTUAL: {check_def}"
    assert col_conta is not None, "Coluna conta_origem nao foi criada"
    assert qtd_fc_virtual == 0, \
        f"Ainda ha {qtd_fc_virtual} linhas FC_VIRTUAL"
    assert qtd_manual_sem_conta == 0, \
        f"Ha {qtd_manual_sem_conta} linhas MANUAL sem conta_origem"
    assert check_manual_conta is not None, \
        "CHECK ck_carvia_extrato_manual_conta nao foi criado"
    assert 'MANUAL' in (check_manual_conta or '') \
        and 'conta_origem' in (check_manual_conta or ''), (
            "CHECK ck_carvia_extrato_manual_conta nao referencia "
            f"origem/conta_origem: {check_manual_conta}"
        )


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        estado = verificar_antes()

        if (
            estado['check_tem_manual']
            and estado['col_conta_existe']
            and estado['qtd_fc_virtual'] == 0
            and estado['check_manual_conta_existe']
        ):
            print("[SKIP] Migration ja aplicada")
        else:
            executar_migration(estado)

        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
