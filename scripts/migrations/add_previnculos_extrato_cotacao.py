"""Migration: criar tabela carvia_previnculos_extrato_cotacao.

Feature "Pre-vinculo de Linha de Extrato a Cotacao" — resolve conciliacao
de fretes CarVia pre-pagos pelo cliente (linha do extrato chega antes da
fatura ser emitida).

Tabela nova, SEM alterar CarviaConciliacao/CarviaCotacao/CarviaExtratoLinha.
Pre-vinculo e estado 'intencional' lateral: linha do extrato permanece
PENDENTE ate a fatura chegar; quando chega, trigger em fatura_routes.py
percorre a cadeia FaturaItem.nf_id -> NF.numero_nf -> PedidoItem.numero_nf
-> Pedido.cotacao_id e cria CarviaConciliacao real, marcando o pre-vinculo
como RESOLVIDO (preserva audit trail via conciliacao_id + fatura_cliente_id).

Colunas:
- id (PK)
- extrato_linha_id (FK carvia_extrato_linhas.id ON DELETE CASCADE)
- cotacao_id (FK carvia_cotacoes.id ON DELETE CASCADE)
- valor_alocado (NUMERIC(15,2), > 0)
- status (VARCHAR(20), default 'ATIVO', CHECK IN 'ATIVO'/'RESOLVIDO'/'CANCELADO')
- conciliacao_id (FK carvia_conciliacoes.id ON DELETE SET NULL, nullable)
- fatura_cliente_id (FK carvia_faturas_cliente.id ON DELETE SET NULL, nullable)
- resolvido_em (TIMESTAMP, nullable)
- resolvido_automatico (BOOLEAN default FALSE)
- cancelado_em, cancelado_por, motivo_cancelamento (cancelamento manual)
- observacao (TEXT, nullable)
- criado_por (VARCHAR(100))
- criado_em (TIMESTAMP default NOW)

Constraints:
- CHECK valor_alocado > 0 — ck_previnculo_valor_positivo
- CHECK status IN (...) — ck_previnculo_status

Indices:
- extrato_linha_id
- cotacao_id
- status (geral)
- (cotacao_id, status) — ix_previnculo_ativo
- (status, resolvido_em) — ix_previnculo_resolvido
- UNIQUE PARCIAL (extrato_linha_id, cotacao_id) WHERE status='ATIVO'
  — uq_previnculo_linha_cotacao_ativo
  (permite recriar pre-vinculo apos cancelamento; apenas 1 ATIVO por par)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    existe = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_previnculos_extrato_cotacao'
        )
    """)).scalar()
    print(f"[BEFORE] Tabela carvia_previnculos_extrato_cotacao existe: {existe}")
    return bool(existe)


def executar_migration():
    """Executa a migration — idempotente via IF NOT EXISTS."""
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_previnculos_extrato_cotacao (
            id SERIAL PRIMARY KEY,
            extrato_linha_id INTEGER NOT NULL
                REFERENCES carvia_extrato_linhas(id) ON DELETE CASCADE,
            cotacao_id INTEGER NOT NULL
                REFERENCES carvia_cotacoes(id) ON DELETE CASCADE,
            valor_alocado NUMERIC(15, 2) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
            conciliacao_id INTEGER
                REFERENCES carvia_conciliacoes(id) ON DELETE SET NULL,
            fatura_cliente_id INTEGER
                REFERENCES carvia_faturas_cliente(id) ON DELETE SET NULL,
            resolvido_em TIMESTAMP,
            resolvido_automatico BOOLEAN NOT NULL DEFAULT FALSE,
            cancelado_em TIMESTAMP,
            cancelado_por VARCHAR(100),
            motivo_cancelamento TEXT,
            observacao TEXT,
            criado_por VARCHAR(100) NOT NULL,
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # CHECK constraints (ADD IF NOT EXISTS via DO block — ALTER TABLE ADD
    # CONSTRAINT nao suporta IF NOT EXISTS diretamente em PG < 16)
    db.session.execute(db.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_previnculo_valor_positivo'
            ) THEN
                ALTER TABLE carvia_previnculos_extrato_cotacao
                    ADD CONSTRAINT ck_previnculo_valor_positivo
                    CHECK (valor_alocado > 0);
            END IF;
        END $$;
    """))

    db.session.execute(db.text("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_previnculo_status'
            ) THEN
                ALTER TABLE carvia_previnculos_extrato_cotacao
                    ADD CONSTRAINT ck_previnculo_status
                    CHECK (status IN ('ATIVO', 'RESOLVIDO', 'CANCELADO'));
            END IF;
        END $$;
    """))

    # Indices (IF NOT EXISTS nativo em CREATE INDEX)
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_previnculo_extrato_linha_id
            ON carvia_previnculos_extrato_cotacao (extrato_linha_id)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_previnculo_cotacao_id
            ON carvia_previnculos_extrato_cotacao (cotacao_id)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_previnculo_status
            ON carvia_previnculos_extrato_cotacao (status)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_previnculo_ativo
            ON carvia_previnculos_extrato_cotacao (cotacao_id, status)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_previnculo_resolvido
            ON carvia_previnculos_extrato_cotacao (status, resolvido_em)
    """))
    # UNIQUE PARCIAL: apenas 1 pre-vinculo ATIVO por (linha, cotacao).
    # Permite recriar apos CANCELADO, e coexistir com RESOLVIDO historico.
    db.session.execute(db.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_previnculo_linha_cotacao_ativo
            ON carvia_previnculos_extrato_cotacao (extrato_linha_id, cotacao_id)
            WHERE status = 'ATIVO'
    """))

    db.session.commit()
    print("[OK] Tabela carvia_previnculos_extrato_cotacao criada + 2 check constraints + 6 indices")


def verificar_depois():
    """Verifica estado apos a migration."""
    # Tabela existe
    existe = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_previnculos_extrato_cotacao'
        )
    """)).scalar()
    assert existe, "Tabela carvia_previnculos_extrato_cotacao nao foi criada"
    print(f"[AFTER] Tabela existe: {existe}")

    # Colunas esperadas
    colunas = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'carvia_previnculos_extrato_cotacao'
        ORDER BY ordinal_position
    """)).fetchall()

    esperadas = {
        'id', 'extrato_linha_id', 'cotacao_id', 'valor_alocado',
        'status', 'conciliacao_id', 'fatura_cliente_id',
        'resolvido_em', 'resolvido_automatico',
        'cancelado_em', 'cancelado_por', 'motivo_cancelamento',
        'observacao', 'criado_por', 'criado_em',
    }
    encontradas = {c[0] for c in colunas}
    faltando = esperadas - encontradas
    assert not faltando, f"Colunas faltando: {faltando}"
    print(f"[AFTER] {len(encontradas)} colunas criadas")

    # CHECK constraints
    constraints = db.session.execute(db.text("""
        SELECT conname FROM pg_constraint
        WHERE conrelid = 'carvia_previnculos_extrato_cotacao'::regclass
        ORDER BY conname
    """)).fetchall()
    nomes_constraints = {c[0] for c in constraints}
    esperadas_c = {
        'ck_previnculo_valor_positivo',
        'ck_previnculo_status',
    }
    faltando_c = esperadas_c - nomes_constraints
    assert not faltando_c, f"Constraints faltando: {faltando_c}"
    print(f"[AFTER] CHECK constraints: {sorted(nomes_constraints & esperadas_c)}")

    # Indices (inclui UNIQUE parcial)
    indices = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_previnculos_extrato_cotacao'
        ORDER BY indexname
    """)).fetchall()
    nomes_indices = {i[0] for i in indices}
    esperados_i = {
        'ix_previnculo_extrato_linha_id',
        'ix_previnculo_cotacao_id',
        'ix_previnculo_status',
        'ix_previnculo_ativo',
        'ix_previnculo_resolvido',
        'uq_previnculo_linha_cotacao_ativo',
    }
    faltando_i = esperados_i - nomes_indices
    assert not faltando_i, f"Indices faltando: {faltando_i}"
    print(f"[AFTER] Indices: {len(nomes_indices)} ({sorted(nomes_indices)})")

    # Tabela vazia (esperado apos criacao)
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_previnculos_extrato_cotacao"
    )).scalar()
    print(f"[DATA] {total} registros (esperado: 0)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe = verificar_antes()
        if ja_existe:
            print("[INFO] Tabela ja existe — aplicando constraints/indices idempotentemente")
        executar_migration()
        verificar_depois()
        print("[DONE] Migration add_previnculos_extrato_cotacao concluida")
