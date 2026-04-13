"""Migration: adicionar auditoria de conferencia a CarviaFaturaCliente.

Espelha os campos de CarviaFaturaTransportadora, adicionando um eixo
de conferencia gerencial manual ao dominio venda:
- status_conferencia: PENDENTE | CONFERIDO (binario, manual)
- conferido_por: email do conferente
- conferido_em: timestamp da conferencia
- observacoes_conferencia: texto livre (aprovacao + historico de reaberturas)

Refator 2.1 do plano shiny-wiggling-harbor. Gate de aprovacao e MANUAL PURO
(sem validacao automatica de soma — decisao do usuario confirmada em
sequential-wibbling-kahn.md Secao 6). Pagamento (`status='PAGA'`) permanece
independente desta auditoria.

Referencia do padrao: CarviaFaturaTransportadora em
app/carvia/models/faturas.py:251-389 (GAP-32 ja resolvido).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    colunas = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name IN ('status_conferencia', 'conferido_por',
                              'conferido_em', 'observacoes_conferencia')
        ORDER BY column_name
    """)).fetchall()
    existentes = [c[0] for c in colunas]
    print(f"[BEFORE] Colunas ja existentes: {existentes or 'nenhuma'}")
    return existentes


def executar_migration():
    """Executa a migration — idempotente via IF NOT EXISTS."""
    db.session.execute(db.text("""
        ALTER TABLE carvia_faturas_cliente
            ADD COLUMN IF NOT EXISTS status_conferencia VARCHAR(20)
                NOT NULL DEFAULT 'PENDENTE',
            ADD COLUMN IF NOT EXISTS conferido_por VARCHAR(100),
            ADD COLUMN IF NOT EXISTS conferido_em TIMESTAMP,
            ADD COLUMN IF NOT EXISTS observacoes_conferencia TEXT
    """))

    # Indice parcial para filtrar rapidamente faturas pendentes de aprovacao
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_faturas_cliente_status_conferencia
            ON carvia_faturas_cliente (status_conferencia)
    """))

    db.session.commit()
    print("[OK] 4 colunas + indice adicionados a carvia_faturas_cliente")


def verificar_depois():
    """Verifica estado apos a migration."""
    colunas = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name IN ('status_conferencia', 'conferido_por',
                              'conferido_em', 'observacoes_conferencia')
        ORDER BY column_name
    """)).fetchall()

    esperados = {
        'conferido_em', 'conferido_por',
        'observacoes_conferencia', 'status_conferencia',
    }
    encontrados = {c[0] for c in colunas}
    faltando = esperados - encontrados
    assert not faltando, f"Colunas faltando apos migration: {faltando}"

    for c in colunas:
        print(f"[AFTER] {c[0]} ({c[1]}, nullable={c[2]}, default={c[3]})")

    # Verificar indice
    idx = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_faturas_cliente'
          AND indexname = 'ix_carvia_faturas_cliente_status_conferencia'
    """)).scalar()
    assert idx is not None, "Indice ix_carvia_faturas_cliente_status_conferencia nao criado"
    print(f"[AFTER] Indice criado: {idx}")

    # Verificar dados existentes — todas as faturas devem comecar em PENDENTE
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_faturas_cliente"
    )).scalar()
    pendentes = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_faturas_cliente WHERE status_conferencia = 'PENDENTE'"
    )).scalar()
    print(f"[DATA] {pendentes}/{total} faturas em status_conferencia=PENDENTE (esperado: todas)")
    assert pendentes == total, (
        f"Esperado todas PENDENTE apos migration, mas {pendentes}/{total}"
    )


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        existentes = verificar_antes()
        if len(existentes) == 4:
            print("[SKIP] Todas as 4 colunas ja existem — pulando DDL")
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration carvia_fatura_cliente_auditoria concluida")
