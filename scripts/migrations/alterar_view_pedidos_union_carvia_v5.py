"""
Migration: VIEW pedidos v5 — sub_rota CarVia tolerante a acento/caixa
Data: 2026-05-13

Recria a VIEW pedidos identica a v4 (alterar_view_pedidos_union_carvia.sql),
alterando APENAS o JOIN com cadastro_sub_rota nas Partes 2A e 2B (CarVia):
    ANTES: UPPER(dest.fisico_cidade) LIKE '%' || UPPER(csr.nome_cidade) || '%'
    DEPOIS: lower(f_unaccent(dest.fisico_cidade)) LIKE
            '%' || lower(f_unaccent(csr.nome_cidade)) || '%'

Motivo: UPPER nao remove acentos, entao 'SÃO PAULO' nunca batia com 'SAO PAULO'.
f_unaccent (funcao SQL pura criada em remover_extensao_unaccent.sql) alinha
o match com a busca canonica em Python (`buscar_sub_rota_por_uf_cidade`).

Idempotente via DROP + CREATE. Executar no Render Shell.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado antes da migration."""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.views "
        "  WHERE table_name = 'pedidos'"
        ")"
    ))
    print(f"[ANTES] VIEW pedidos existe: {result.scalar()}")

    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[ANTES] Registros na VIEW: {result.scalar()}")
    except Exception:
        print("[ANTES] VIEW nao acessivel")

    # Verificar dependencia: funcao f_unaccent
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM pg_proc WHERE proname = 'f_unaccent'"
        ")"
    ))
    tem_f_unaccent = result.scalar()
    print(f"[ANTES] f_unaccent existe: {tem_f_unaccent}")
    if not tem_f_unaccent:
        raise RuntimeError(
            "f_unaccent nao encontrada. Execute scripts/migrations/"
            "remover_extensao_unaccent.sql primeiro."
        )

    # Diagnostico: quantos pedidos CarVia tem sub_rota NULL hoje
    try:
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND sub_rota IS NULL"
        ))
        print(f"[ANTES] Pedidos CarVia com sub_rota NULL: {result.scalar()}")
    except Exception:
        pass


def executar_migration(conn):
    """Executa DDL — recria VIEW com UNION ALL e f_unaccent."""
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'alterar_view_pedidos_union_carvia_v5.sql'
    )
    with open(sql_path, 'r') as f:
        sql = f.read()

    conn.execute(db.text(sql))
    print("[OK] VIEW pedidos recriada (v5 — f_unaccent no match cidade x sub_rota)")


def verificar_depois(conn):
    """Verifica estado apos migration."""
    result = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.views "
        "  WHERE table_name = 'pedidos'"
        ")"
    ))
    print(f"[DEPOIS] VIEW pedidos existe: {result.scalar()}")

    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[DEPOIS] Total registros: {result.scalar()}")

        # CarVia pode aparecer com prefixo CARVIA-... ou CARVIA-PED-...
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%'"
        ))
        print(f"[DEPOIS] Registros CarVia: {result.scalar()}")

        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id NOT LIKE 'CARVIA%' OR separacao_lote_id IS NULL"
        ))
        print(f"[DEPOIS] Registros Nacom: {result.scalar()}")

        # Diagnostico: quantos pedidos CarVia ainda estao sem sub_rota
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND sub_rota IS NULL"
        ))
        print(f"[DEPOIS] Pedidos CarVia com sub_rota NULL: {result.scalar()}")

        # Diagnostico: quantos pedidos CarVia agora tem sub_rota
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND sub_rota IS NOT NULL"
        ))
        print(f"[DEPOIS] Pedidos CarVia com sub_rota preenchida: {result.scalar()}")
    except Exception as e:
        print(f"[DEPOIS] Erro ao verificar: {e}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: VIEW pedidos v5 (f_unaccent no JOIN CarVia)")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
