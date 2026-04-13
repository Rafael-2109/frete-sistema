"""Migration: aprovacao de subcontratos + conta corrente transportadoras CarVia.

Porta para o CarVia (esfera de Compra) os fluxos de "Em Tratativa" e
"Conta Corrente Considerado x Pago" do modulo Nacom (app/fretes/).

Operacoes:
1. ALTER carvia_subcontratos: + valor_pago, valor_pago_em, valor_pago_por,
   requer_aprovacao + indice parcial ix_carvia_sub_requer_aprovacao
2. CREATE TABLE carvia_aprovacoes_subcontrato (historico de tratativas)
3. CREATE TABLE carvia_conta_corrente_transportadoras (movimentacoes CC)

Idempotente — pode rodar multiplas vezes. Verifica antes/depois.

Ref:
  .claude/plans/wobbly-tumbling-treasure.md
  /tmp/subagent-findings/aprovacao_fretes_nacom.md
  /tmp/subagent-findings/conta_corrente_nacom.md
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


COLS_SUBCONTRATO = ('valor_pago', 'valor_pago_em', 'valor_pago_por', 'requer_aprovacao')
TABELAS_NOVAS = ('carvia_aprovacoes_subcontrato', 'carvia_conta_corrente_transportadoras')


def verificar_antes():
    """Verifica estado antes da migration."""
    cols = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = ANY(:cols)
        ORDER BY column_name
    """), {'cols': list(COLS_SUBCONTRATO)}).fetchall()
    cols_existentes = [c[0] for c in cols]

    tabs = db.session.execute(db.text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name = ANY(:tabs)
        ORDER BY table_name
    """), {'tabs': list(TABELAS_NOVAS)}).fetchall()
    tabs_existentes = [t[0] for t in tabs]

    print(f"[BEFORE] Colunas em carvia_subcontratos: {cols_existentes or 'nenhuma'}")
    print(f"[BEFORE] Tabelas novas: {tabs_existentes or 'nenhuma'}")
    return cols_existentes, tabs_existentes


def executar_migration():
    """Executa a migration — idempotente via IF NOT EXISTS."""
    # 1. ALTER carvia_subcontratos
    db.session.execute(db.text("""
        ALTER TABLE carvia_subcontratos
            ADD COLUMN IF NOT EXISTS valor_pago        NUMERIC(15, 2),
            ADD COLUMN IF NOT EXISTS valor_pago_em     TIMESTAMP,
            ADD COLUMN IF NOT EXISTS valor_pago_por    VARCHAR(100),
            ADD COLUMN IF NOT EXISTS requer_aprovacao  BOOLEAN NOT NULL DEFAULT FALSE
    """))

    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_sub_requer_aprovacao
            ON carvia_subcontratos (requer_aprovacao)
            WHERE requer_aprovacao = TRUE
    """))

    # 2. CREATE TABLE carvia_aprovacoes_subcontrato
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_aprovacoes_subcontrato (
            id                       SERIAL PRIMARY KEY,
            subcontrato_id           INTEGER NOT NULL REFERENCES carvia_subcontratos(id),
            status                   VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
            solicitado_por           VARCHAR(100) NOT NULL,
            solicitado_em            TIMESTAMP NOT NULL DEFAULT NOW(),
            motivo_solicitacao       TEXT,
            valor_cotado_snap        NUMERIC(15, 2),
            valor_considerado_snap   NUMERIC(15, 2),
            valor_pago_snap          NUMERIC(15, 2),
            diferenca_snap           NUMERIC(15, 2),
            aprovador                VARCHAR(100),
            aprovado_em              TIMESTAMP,
            observacoes_aprovacao    TEXT,
            lancar_diferenca         BOOLEAN DEFAULT FALSE,
            criado_em                TIMESTAMP NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_carvia_aprov_status
                CHECK (status IN ('PENDENTE', 'APROVADO', 'REJEITADO'))
        )
    """))

    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_subcontrato_id
            ON carvia_aprovacoes_subcontrato (subcontrato_id)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_status
            ON carvia_aprovacoes_subcontrato (status)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_aprov_sub_solicitado_em
            ON carvia_aprovacoes_subcontrato (solicitado_em)
    """))

    # 3. CREATE TABLE carvia_conta_corrente_transportadoras
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_conta_corrente_transportadoras (
            id                          SERIAL PRIMARY KEY,
            transportadora_id           INTEGER NOT NULL REFERENCES transportadoras(id),
            subcontrato_id              INTEGER NOT NULL REFERENCES carvia_subcontratos(id),
            fatura_transportadora_id    INTEGER REFERENCES carvia_faturas_transportadora(id),
            tipo_movimentacao           VARCHAR(20) NOT NULL,
            valor_diferenca             NUMERIC(15, 2) NOT NULL,
            valor_debito                NUMERIC(15, 2) NOT NULL DEFAULT 0,
            valor_credito               NUMERIC(15, 2) NOT NULL DEFAULT 0,
            descricao                   VARCHAR(255) NOT NULL,
            observacoes                 TEXT,
            status                      VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
            compensado_em               TIMESTAMP,
            compensado_por              VARCHAR(100),
            compensacao_subcontrato_id  INTEGER REFERENCES carvia_subcontratos(id),
            criado_em                   TIMESTAMP NOT NULL DEFAULT NOW(),
            criado_por                  VARCHAR(100) NOT NULL,
            CONSTRAINT ck_carvia_cc_tipo
                CHECK (tipo_movimentacao IN ('DEBITO', 'CREDITO', 'COMPENSACAO')),
            CONSTRAINT ck_carvia_cc_dif
                CHECK (valor_diferenca >= 0),
            CONSTRAINT ck_carvia_cc_status
                CHECK (status IN ('ATIVO', 'COMPENSADO', 'DESCONSIDERADO'))
        )
    """))

    for stmt in (
        "CREATE INDEX IF NOT EXISTS ix_carvia_cc_transp ON carvia_conta_corrente_transportadoras (transportadora_id)",
        "CREATE INDEX IF NOT EXISTS ix_carvia_cc_sub ON carvia_conta_corrente_transportadoras (subcontrato_id)",
        "CREATE INDEX IF NOT EXISTS ix_carvia_cc_fatura ON carvia_conta_corrente_transportadoras (fatura_transportadora_id)",
        "CREATE INDEX IF NOT EXISTS ix_carvia_cc_status ON carvia_conta_corrente_transportadoras (status)",
        "CREATE INDEX IF NOT EXISTS ix_carvia_cc_criado_em ON carvia_conta_corrente_transportadoras (criado_em)",
    ):
        db.session.execute(db.text(stmt))

    db.session.commit()
    print("[OK] DDL executado: 4 colunas + 2 tabelas + indices")


def verificar_depois():
    """Verifica estado apos a migration."""
    # Colunas em carvia_subcontratos
    cols = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'carvia_subcontratos'
          AND column_name = ANY(:cols)
        ORDER BY column_name
    """), {'cols': list(COLS_SUBCONTRATO)}).fetchall()

    encontradas = {c[0] for c in cols}
    faltando = set(COLS_SUBCONTRATO) - encontradas
    assert not faltando, f"Colunas faltando em carvia_subcontratos: {faltando}"

    for c in cols:
        print(f"[AFTER] carvia_subcontratos.{c[0]} ({c[1]}, nullable={c[2]}, default={c[3]})")

    # Tabelas novas
    tabs = db.session.execute(db.text("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name = ANY(:tabs)
        ORDER BY table_name
    """), {'tabs': list(TABELAS_NOVAS)}).fetchall()
    encontradas_tabs = {t[0] for t in tabs}
    faltando_tabs = set(TABELAS_NOVAS) - encontradas_tabs
    assert not faltando_tabs, f"Tabelas faltando: {faltando_tabs}"

    for t in TABELAS_NOVAS:
        cnt = db.session.execute(db.text(f"SELECT COUNT(*) FROM {t}")).scalar()
        print(f"[AFTER] {t}: {cnt} registros (esperado: 0)")

    # Indices criticos
    idx_esperados = {
        'ix_carvia_sub_requer_aprovacao',
        'ix_carvia_aprov_sub_subcontrato_id',
        'ix_carvia_aprov_sub_status',
        'ix_carvia_aprov_sub_solicitado_em',
        'ix_carvia_cc_transp',
        'ix_carvia_cc_sub',
        'ix_carvia_cc_fatura',
        'ix_carvia_cc_status',
        'ix_carvia_cc_criado_em',
    }
    idx_existentes = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE indexname = ANY(:idx)
    """), {'idx': list(idx_esperados)}).fetchall()
    encontrados_idx = {i[0] for i in idx_existentes}
    faltando_idx = idx_esperados - encontrados_idx
    assert not faltando_idx, f"Indices faltando: {faltando_idx}"
    print(f"[AFTER] {len(encontrados_idx)} indices criados/validados")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        cols_antes, tabs_antes = verificar_antes()
        ja_completo = (
            len(cols_antes) == len(COLS_SUBCONTRATO)
            and len(tabs_antes) == len(TABELAS_NOVAS)
        )
        if ja_completo:
            print("[SKIP] Migration ja aplicada — pulando DDL")
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration carvia_aprovacao_conta_corrente concluida")
