"""Migration: criar tabela carvia_historico_match_extrato.

Feature "Historico de Match Extrato <-> Pagador" — log append-only de
eventos de conciliacao fatura_cliente. A cada conciliacao criada, o hook
em CarviaConciliacaoService.conciliar() grava UMA linha com a chave
(tokens_normalizados_descricao_linha_de_cima, cnpj_pagador).

Nao ha UNIQUE constraint: uma descricao pode fazer match com N CNPJs
legitimamente (ex: "PIX RECEBIDO" pode vir de varios pagadores). Cada
conciliacao e um evento individual. Contagem de ocorrencias e via
COUNT(*) GROUP BY cnpj_pagador na consulta.

Tabela usada por pontuar_documentos() em carvia_sugestao_service.py
para aplicar boost multiplicativo 1.4x no score quando o doc sugerido
tem o mesmo cnpj_cliente de um padrao aprendido.

Colunas:
- id (PK)
- descricao_linha_raw (VARCHAR 500, snapshot da linha de cima — audit)
- descricao_tokens (VARCHAR 500, tokens normalizados ordenados — chave)
- cnpj_pagador (VARCHAR 20, CarviaFaturaCliente.cnpj_cliente)
- tipo_documento (VARCHAR 30, default 'fatura_cliente')
- conciliacao_id (INTEGER nullable, ponteiro solto para audit)
- registrado_em (TIMESTAMP, default NOW)

Indices:
- descricao_tokens (consulta principal)
- cnpj_pagador (consultas auxiliares)
- (descricao_tokens, tipo_documento) (consulta principal completa)
- conciliacao_id WHERE NOT NULL (idempotencia de backfill)
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
            WHERE table_name = 'carvia_historico_match_extrato'
        )
    """)).scalar()
    print(f"[BEFORE] Tabela carvia_historico_match_extrato existe: {existe}")
    return bool(existe)


def executar_migration():
    """Executa a migration — idempotente via IF NOT EXISTS."""
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_historico_match_extrato (
            id SERIAL PRIMARY KEY,
            descricao_linha_raw VARCHAR(500) NOT NULL,
            descricao_tokens VARCHAR(500) NOT NULL,
            cnpj_pagador VARCHAR(20) NOT NULL,
            tipo_documento VARCHAR(30) NOT NULL DEFAULT 'fatura_cliente',
            conciliacao_id INTEGER,
            registrado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))

    # FIX M4: remover indice standalone redundante. O composto
    # (descricao_tokens, tipo_documento) ja cobre queries so por tokens
    # via prefix rule do PostgreSQL. DROP IF EXISTS limpa instancias
    # onde este script ja rodou com a versao antiga.
    db.session.execute(db.text("""
        DROP INDEX IF EXISTS ix_carvia_histmatch_tokens
    """))

    # Indices (IF NOT EXISTS nativo em CREATE INDEX)
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_cnpj
            ON carvia_historico_match_extrato (cnpj_pagador)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_tokens_tipo
            ON carvia_historico_match_extrato (descricao_tokens, tipo_documento)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_carvia_histmatch_conciliacao_id
            ON carvia_historico_match_extrato (conciliacao_id)
            WHERE conciliacao_id IS NOT NULL
    """))

    db.session.commit()
    print("[OK] Tabela carvia_historico_match_extrato criada + 3 indices")


def verificar_depois():
    """Verifica estado apos a migration."""
    # Tabela existe
    existe = db.session.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_name = 'carvia_historico_match_extrato'
        )
    """)).scalar()
    assert existe, "Tabela carvia_historico_match_extrato nao foi criada"
    print(f"[AFTER] Tabela existe: {existe}")

    # Colunas esperadas
    colunas = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'carvia_historico_match_extrato'
        ORDER BY ordinal_position
    """)).fetchall()

    esperadas = {
        'id', 'descricao_linha_raw', 'descricao_tokens',
        'cnpj_pagador', 'tipo_documento', 'conciliacao_id',
        'registrado_em',
    }
    encontradas = {c[0] for c in colunas}
    faltando = esperadas - encontradas
    assert not faltando, f"Colunas faltando: {faltando}"
    print(f"[AFTER] {len(encontradas)} colunas criadas")

    # Indices
    indices = db.session.execute(db.text("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'carvia_historico_match_extrato'
        ORDER BY indexname
    """)).fetchall()
    nomes_indices = {i[0] for i in indices}
    # FIX M4: ix_carvia_histmatch_tokens removido — redundante com o composto
    esperados_i = {
        'ix_carvia_histmatch_cnpj',
        'ix_carvia_histmatch_tokens_tipo',
        'ix_carvia_histmatch_conciliacao_id',
    }
    faltando_i = esperados_i - nomes_indices
    assert not faltando_i, f"Indices faltando: {faltando_i}"
    # ix_carvia_histmatch_tokens NAO deve existir (removido em FIX M4)
    assert 'ix_carvia_histmatch_tokens' not in nomes_indices, (
        "Indice redundante ix_carvia_histmatch_tokens ainda existe — "
        "DROP INDEX IF EXISTS falhou"
    )
    print(f"[AFTER] Indices: {len(nomes_indices)} ({sorted(nomes_indices)})")

    # Tabela vazia (esperado apos criacao)
    total = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_historico_match_extrato"
    )).scalar()
    print(f"[DATA] {total} registros (esperado: 0 na primeira execucao)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe = verificar_antes()
        if ja_existe:
            print("[INFO] Tabela ja existe — aplicando indices idempotentemente")
        executar_migration()
        verificar_depois()
        print("[DONE] Migration add_carvia_historico_match_extrato concluida")
