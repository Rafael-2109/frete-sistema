"""Migration: Adicionar agendamento_confirmado em carvia_cotacoes + atualizar VIEW pedidos.

1. Novo campo boolean para toggle de confirmacao de agendamento CarVia.
2. VIEW pedidos atualizada para projetar campo real (antes era FALSE hardcoded).
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    result = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'agendamento_confirmado'
    """)).scalar()
    existe = 'SIM' if result else 'NAO'
    print(f"[BEFORE] carvia_cotacoes.agendamento_confirmado existe = {existe}")
    return result is not None


def executar_migration():
    """Executa a migration: adiciona coluna + recria VIEW."""
    # Passo 1: Adicionar coluna
    db.session.execute(db.text(
        "ALTER TABLE carvia_cotacoes ADD COLUMN IF NOT EXISTS "
        "agendamento_confirmado BOOLEAN NOT NULL DEFAULT FALSE"
    ))
    db.session.commit()
    print("[OK] agendamento_confirmado adicionado em carvia_cotacoes")

    # Passo 2: Recriar VIEW (ler do arquivo SQL)
    sql_path = os.path.join(os.path.dirname(__file__), 'add_agendamento_confirmado_carvia.sql')
    with open(sql_path, 'r') as f:
        sql = f.read()

    # Extrair apenas o DROP VIEW + CREATE VIEW (a partir do DROP)
    idx = sql.find('DROP VIEW IF EXISTS pedidos')
    if idx >= 0:
        view_sql = sql[idx:]
        db.session.execute(db.text(view_sql))
        db.session.commit()
        print("[OK] VIEW pedidos recriada com agendamento_confirmado de carvia_cotacoes")
    else:
        print("[WARN] SQL da VIEW nao encontrado no arquivo — executar manualmente")


def verificar_depois():
    """Verifica estado apos a migration."""
    # Verificar coluna
    result = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'carvia_cotacoes' AND column_name = 'agendamento_confirmado'
    """)).scalar()
    assert result is not None, "Campo agendamento_confirmado NAO encontrado em carvia_cotacoes"
    print(f"[AFTER] carvia_cotacoes.agendamento_confirmado existe = SIM")

    # Verificar VIEW projeta o campo
    result = db.session.execute(db.text("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'pedidos' AND column_name = 'agendamento_confirmado'
    """)).scalar()
    print(f"[AFTER] VIEW pedidos.agendamento_confirmado existe = {'SIM' if result else 'NAO'}")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
