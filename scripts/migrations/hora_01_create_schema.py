"""Migration HORA 01: cria schema inicial (13 tabelas hora_*).

Contrato de design: docs/hora/INVARIANTES.md.
Convencoes do modulo: app/hora/CLAUDE.md.

Modo de uso:
    python scripts/migrations/hora_01_create_schema.py

Idempotente: pode rodar multiplas vezes sem erro.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS_HORA = [
    'hora_loja',
    'hora_modelo',
    'hora_tabela_preco',
    'hora_moto',
    'hora_pedido',
    'hora_pedido_item',
    'hora_nf_entrada',
    'hora_nf_entrada_item',
    'hora_recebimento',
    'hora_recebimento_conferencia',
    'hora_venda',
    'hora_venda_item',
    'hora_moto_evento',
]


def contar_tabelas_existentes():
    """Retorna set com nomes das tabelas hora_* que ja existem no banco."""
    result = db.session.execute(
        db.text(
            """
            SELECT tablename FROM pg_catalog.pg_tables
            WHERE schemaname = 'public' AND tablename LIKE 'hora\\_%' ESCAPE '\\'
            """
        )
    ).fetchall()
    return {row[0] for row in result}


def verificar_antes():
    existentes = contar_tabelas_existentes()
    faltantes = [t for t in TABELAS_HORA if t not in existentes]
    print(f"[BEFORE] Tabelas hora_* existentes: {len(existentes)}/{len(TABELAS_HORA)}")
    if existentes:
        for t in sorted(existentes):
            print(f"  - {t}")
    if faltantes:
        print(f"[BEFORE] Tabelas a criar: {len(faltantes)}")
        for t in faltantes:
            print(f"  + {t}")


def executar_migration():
    sql_path = os.path.join(os.path.dirname(__file__), 'hora_01_create_schema.sql')
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Executar como um unico bloco (todas CREATE TABLE IF NOT EXISTS).
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] Script SQL executado (CREATE TABLE IF NOT EXISTS x 13 + indices)")


def verificar_depois():
    existentes = contar_tabelas_existentes()
    faltantes = [t for t in TABELAS_HORA if t not in existentes]
    print(f"[AFTER] Tabelas hora_* existentes: {len(existentes)}/{len(TABELAS_HORA)}")
    if faltantes:
        raise AssertionError(f"Tabelas faltando apos migration: {faltantes}")
    # Checar alguns indices criticos (chassi em tabelas transacionais).
    indices_criticos = [
        ('hora_moto_evento', 'ix_hora_moto_evento_chassi'),
        ('hora_venda_item', 'ix_hora_venda_item_chassi'),
        ('hora_recebimento_conferencia', 'ix_hora_recebimento_conferencia_chassi'),
        ('hora_nf_entrada_item', 'ix_hora_nf_entrada_item_chassi'),
        ('hora_pedido_item', 'ix_hora_pedido_item_chassi'),
    ]
    for tabela, indice in indices_criticos:
        result = db.session.execute(
            db.text(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = :tabela AND indexname = :indice
                """
            ),
            {'tabela': tabela, 'indice': indice},
        ).scalar()
        assert result is not None, f"Indice {indice} em {tabela} nao encontrado"
    print("[AFTER] Indices criticos em numero_chassi validados (invariante 2)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 01 concluida com sucesso")
