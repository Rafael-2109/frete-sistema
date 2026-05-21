"""
Migration: VIEW pedidos v6 — projeta agendamento_confirmado real para CarVia
Data: 2026-05-21

Recria a VIEW pedidos identica a v5 (alterar_view_pedidos_union_carvia_v5.sql),
alterando APENAS a projecao de agendamento_confirmado nas Partes 2A e 2B (CarVia):
    ANTES (v5):  FALSE AS agendamento_confirmado
    DEPOIS (v6): cot.agendamento_confirmado AS agendamento_confirmado

Motivo: a projecao FALSE era uma regressao herdada das recriacoes v4/v5
(a migration add_agendamento_confirmado_carvia.sql de 2026-03-30 ja projetava
cot.agendamento_confirmado). Com a v6, lista_pedidos (Pedido.agendamento_confirmado)
reflete o checkbox "Confirmacao de Agendamento" da cotacao comercial CarVia
(carvia_cotacoes.agendamento_confirmado).

Parte 1 (Nacom) e INALTERADA. Idempotente via DROP + CREATE. Executar no Render Shell.
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

    # Dependencia: funcao f_unaccent (usada no JOIN sub_rota herdado da v5)
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

    # Diagnostico: na v5 a VIEW retorna FALSE hardcoded -> esperado 0
    try:
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND agendamento_confirmado = TRUE"
        ))
        print(f"[ANTES] Pedidos CarVia com agendamento_confirmado=TRUE: {result.scalar()}")
    except Exception:
        pass


def executar_migration(conn):
    """Executa DDL — recria VIEW projetando cot.agendamento_confirmado para CarVia."""
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'alterar_view_pedidos_union_carvia_v6.sql'
    )
    with open(sql_path, 'r') as f:
        sql = f.read()

    conn.execute(db.text(sql))
    print("[OK] VIEW pedidos recriada (v6 — cot.agendamento_confirmado para CarVia)")


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

        # Diagnostico: agora a VIEW deve projetar o valor real da cotacao
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND agendamento_confirmado = TRUE"
        ))
        print(f"[DEPOIS] Pedidos CarVia com agendamento_confirmado=TRUE: {result.scalar()}")

        # Cross-check contra a tabela fonte
        result = conn.execute(db.text(
            "SELECT COUNT(*) FROM carvia_cotacoes "
            "WHERE status = 'APROVADO' AND agendamento_confirmado = TRUE"
        ))
        print(f"[DEPOIS] carvia_cotacoes APROVADO com agendamento_confirmado=TRUE: {result.scalar()}")
    except Exception as e:
        print(f"[DEPOIS] Erro ao verificar: {e}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: VIEW pedidos v6 (agendamento_confirmado CarVia)")
            print("=" * 60)

            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)

            print("=" * 60)
            print("Migration concluida com sucesso!")
