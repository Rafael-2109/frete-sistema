"""
Migration: VIEW pedidos v7 — adiciona coluna horario_agendamento (CarVia)
Data: 2026-05-21

Recria a VIEW pedidos identica a v6, ADICIONANDO a coluna horario_agendamento
(TIME) apos `agendamento` nas 3 partes do UNION:
    Parte 1 (Nacom):  NULL::time
    Parte 2A/2B (CarVia): cot.horario_agenda

DEPENDENCIA: requer carvia_cotacoes.horario_agenda (rodar
add_horario_agendamento_carvia.py ANTES). Idempotente via DROP + CREATE.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes(conn):
    """Verifica estado e dependencias antes da migration."""
    result = conn.execute(db.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'pedidos')"
    ))
    print(f"[ANTES] VIEW pedidos existe: {result.scalar()}")

    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[ANTES] Registros na VIEW: {result.scalar()}")
    except Exception:
        print("[ANTES] VIEW nao acessivel")

    # Dependencia 1: f_unaccent (JOIN sub_rota herdado da v5/v6)
    tem_f_unaccent = conn.execute(db.text(
        "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'f_unaccent')"
    )).scalar()
    print(f"[ANTES] f_unaccent existe: {tem_f_unaccent}")
    if not tem_f_unaccent:
        raise RuntimeError(
            "f_unaccent nao encontrada. Execute remover_extensao_unaccent.sql primeiro."
        )

    # Dependencia 2: coluna carvia_cotacoes.horario_agenda (usada pela VIEW)
    tem_coluna = conn.execute(db.text(
        "SELECT EXISTS ("
        "  SELECT 1 FROM information_schema.columns "
        "  WHERE table_name = 'carvia_cotacoes' AND column_name = 'horario_agenda'"
        ")"
    )).scalar()
    print(f"[ANTES] carvia_cotacoes.horario_agenda existe: {tem_coluna}")
    if not tem_coluna:
        raise RuntimeError(
            "carvia_cotacoes.horario_agenda nao existe. Execute "
            "add_horario_agendamento_carvia.py ANTES desta migration."
        )


def executar_migration(conn):
    """Executa DDL — recria VIEW com a coluna horario_agendamento."""
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'alterar_view_pedidos_union_carvia_v7.sql'
    )
    with open(sql_path, 'r') as f:
        sql = f.read()
    conn.execute(db.text(sql))
    print("[OK] VIEW pedidos recriada (v7 — coluna horario_agendamento)")


def verificar_depois(conn):
    """Verifica estado apos migration."""
    result = conn.execute(db.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.views WHERE table_name = 'pedidos')"
    ))
    print(f"[DEPOIS] VIEW pedidos existe: {result.scalar()}")

    try:
        result = conn.execute(db.text("SELECT COUNT(*) FROM pedidos"))
        print(f"[DEPOIS] Total registros: {result.scalar()}")

        # Coluna nova presente na VIEW?
        tem_coluna = conn.execute(db.text(
            "SELECT EXISTS ("
            "  SELECT 1 FROM information_schema.columns "
            "  WHERE table_name = 'pedidos' AND column_name = 'horario_agendamento'"
            ")"
        )).scalar()
        print(f"[DEPOIS] VIEW pedidos.horario_agendamento existe: {tem_coluna}")
        if not tem_coluna:
            raise RuntimeError("Coluna horario_agendamento nao foi criada na VIEW!")

        # Nacom deve ter horario_agendamento sempre NULL
        nacom_com_hora = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE (separacao_lote_id NOT LIKE 'CARVIA%' OR separacao_lote_id IS NULL) "
            "  AND horario_agendamento IS NOT NULL"
        )).scalar()
        print(f"[DEPOIS] Nacom com horario (esperado 0): {nacom_com_hora}")

        carvia_com_hora = conn.execute(db.text(
            "SELECT COUNT(*) FROM pedidos "
            "WHERE separacao_lote_id LIKE 'CARVIA%' AND horario_agendamento IS NOT NULL"
        )).scalar()
        print(f"[DEPOIS] CarVia com horario preenchido: {carvia_com_hora}")
    except Exception as e:
        print(f"[DEPOIS] Erro ao verificar: {e}")
        raise


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            print("=" * 60)
            print("Migration: VIEW pedidos v7 (coluna horario_agendamento)")
            print("=" * 60)
            verificar_antes(conn)
            print("-" * 60)
            executar_migration(conn)
            print("-" * 60)
            verificar_depois(conn)
            print("=" * 60)
            print("Migration concluida com sucesso!")
