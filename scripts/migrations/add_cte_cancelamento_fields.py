"""Migration: Cancelamento de CTe via XML do Outlook 365.

Adiciona:
1. 5 colunas em `conhecimento_transporte`:
   - cancelado (BOOLEAN)
   - data_cancelamento (TIMESTAMP)
   - protocolo_cancelamento (VARCHAR(50))
   - motivo_cancelamento (TEXT)
   - cancelamento_origem (VARCHAR(30))
   + indice em `cancelado`

2. Tabela `cte_pendencia_cancelamento` com FKs e indices.

Data: 2026-04-09
Referencia: .claude/plans/temporal-exploring-biscuit.md
"""
import sys
import os

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
)

from app import create_app, db


CAMPOS_NOVOS_CTE = [
    'cancelado',
    'data_cancelamento',
    'protocolo_cancelamento',
    'motivo_cancelamento',
    'cancelamento_origem',
]


def verificar_antes():
    """Verifica estado antes da migration."""
    print("=" * 70)
    print("[BEFORE] Verificando estado atual...")
    print("=" * 70)

    # 1. Checar campos novos em conhecimento_transporte
    campos_existentes = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'conhecimento_transporte'
          AND column_name = ANY(:campos)
    """), {'campos': CAMPOS_NOVOS_CTE}).scalars().all()

    campos_ausentes = set(CAMPOS_NOVOS_CTE) - set(campos_existentes)
    print(f"[BEFORE] Campos ja presentes: {sorted(campos_existentes) or '(nenhum)'}")
    print(f"[BEFORE] Campos a adicionar : {sorted(campos_ausentes) or '(nenhum — migration ja aplicada?)'}")

    # 2. Checar tabela cte_pendencia_cancelamento
    tabela_existe = db.session.execute(db.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'cte_pendencia_cancelamento'
    """)).scalar()
    print(f"[BEFORE] Tabela cte_pendencia_cancelamento existe: {'SIM' if tabela_existe else 'NAO'}")

    return {
        'campos_ausentes': campos_ausentes,
        'tabela_existe': bool(tabela_existe),
    }


def executar_migration():
    """Executa a migration idempotente."""
    print("=" * 70)
    print("[EXEC] Aplicando migration...")
    print("=" * 70)

    # Passo 1: Adicionar colunas em conhecimento_transporte
    ddl_colunas = [
        "ALTER TABLE conhecimento_transporte "
        "ADD COLUMN IF NOT EXISTS cancelado BOOLEAN NOT NULL DEFAULT FALSE",

        "ALTER TABLE conhecimento_transporte "
        "ADD COLUMN IF NOT EXISTS data_cancelamento TIMESTAMP",

        "ALTER TABLE conhecimento_transporte "
        "ADD COLUMN IF NOT EXISTS protocolo_cancelamento VARCHAR(50)",

        "ALTER TABLE conhecimento_transporte "
        "ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT",

        "ALTER TABLE conhecimento_transporte "
        "ADD COLUMN IF NOT EXISTS cancelamento_origem VARCHAR(30)",

        "CREATE INDEX IF NOT EXISTS ix_conhecimento_transporte_cancelado "
        "ON conhecimento_transporte (cancelado)",
    ]

    for sql in ddl_colunas:
        db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] Colunas de cancelamento adicionadas em conhecimento_transporte")

    # Passo 2: Criar tabela cte_pendencia_cancelamento
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS cte_pendencia_cancelamento (
            id SERIAL PRIMARY KEY,
            chave_acesso VARCHAR(44) NOT NULL,
            cte_id INTEGER REFERENCES conhecimento_transporte(id) ON DELETE SET NULL,
            frete_id INTEGER REFERENCES fretes(id) ON DELETE SET NULL,
            status VARCHAR(40) NOT NULL,
            mensagem TEXT,
            xml_raw TEXT,
            email_message_id VARCHAR(255),
            email_subject VARCHAR(500),
            criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TIMESTAMP,
            resolvido_por VARCHAR(100)
        )
    """))
    db.session.commit()
    print("[OK] Tabela cte_pendencia_cancelamento criada")

    # Passo 3: Indices da tabela nova
    ddl_indices = [
        "CREATE INDEX IF NOT EXISTS ix_cte_pendencia_chave "
        "ON cte_pendencia_cancelamento (chave_acesso)",

        "CREATE INDEX IF NOT EXISTS ix_cte_pendencia_status "
        "ON cte_pendencia_cancelamento (status)",

        "CREATE INDEX IF NOT EXISTS ix_cte_pendencia_criado_em "
        "ON cte_pendencia_cancelamento (criado_em)",

        "CREATE INDEX IF NOT EXISTS ix_cte_pendencia_cte_id "
        "ON cte_pendencia_cancelamento (cte_id)",

        "CREATE INDEX IF NOT EXISTS ix_cte_pendencia_frete_id "
        "ON cte_pendencia_cancelamento (frete_id)",
    ]

    for sql in ddl_indices:
        db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] Indices de cte_pendencia_cancelamento criados")


def verificar_depois():
    """Verifica estado apos a migration."""
    print("=" * 70)
    print("[AFTER] Verificando resultado...")
    print("=" * 70)

    # 1. Todos os campos devem existir
    campos_existentes = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'conhecimento_transporte'
          AND column_name = ANY(:campos)
    """), {'campos': CAMPOS_NOVOS_CTE}).scalars().all()

    for campo in CAMPOS_NOVOS_CTE:
        assert campo in campos_existentes, (
            f"Campo {campo!r} NAO foi criado em conhecimento_transporte"
        )
        print(f"[AFTER] conhecimento_transporte.{campo}: OK")

    # 2. Tabela deve existir com todas as colunas
    colunas_pendencia = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'cte_pendencia_cancelamento'
        ORDER BY ordinal_position
    """)).scalars().all()

    esperadas = {
        'id', 'chave_acesso', 'cte_id', 'frete_id', 'status',
        'mensagem', 'xml_raw', 'email_message_id', 'email_subject',
        'criado_em', 'resolvido_em', 'resolvido_por',
    }
    faltando = esperadas - set(colunas_pendencia)
    assert not faltando, f"Colunas faltando em cte_pendencia_cancelamento: {faltando}"
    print(f"[AFTER] cte_pendencia_cancelamento: {len(colunas_pendencia)} colunas OK")

    # 3. Indice cancelado deve existir
    idx_cancelado = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'conhecimento_transporte'
          AND indexname = 'ix_conhecimento_transporte_cancelado'
    """)).scalar()
    assert idx_cancelado, "Indice ix_conhecimento_transporte_cancelado NAO foi criado"
    print("[AFTER] Indice ix_conhecimento_transporte_cancelado: OK")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        estado_antes = verificar_antes()
        if not estado_antes['campos_ausentes'] and estado_antes['tabela_existe']:
            print("[SKIP] Migration ja aplicada anteriormente. Nada a fazer.")
        else:
            executar_migration()
        verificar_depois()
        print("=" * 70)
        print("[DONE] Migration concluida com sucesso")
        print("=" * 70)
