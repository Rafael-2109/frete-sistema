"""Migration: adiciona coluna TeamsTask.resposta_card JSONB.

Permite ao agente retornar cards Adaptive estruturados (nao apenas texto).
A Azure Function (azure-functions/frete-bot/bot.py) detecta este campo
durante o polling de /bot/status e renderiza via card builders.

Parte da Fase 1 do projeto de melhorias do bot Teams.
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


def verificar_antes():
    """Verifica estado antes da migration."""
    col = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'teams_tasks' AND column_name = 'resposta_card'
    """)).fetchone()
    if col:
        print(f"[BEFORE] teams_tasks.resposta_card ja existe: type={col[1]} nullable={col[2]}")
        return True
    print("[BEFORE] teams_tasks.resposta_card NAO existe")
    return False


def executar_migration():
    """Executa a migration."""
    db.session.execute(db.text("""
        ALTER TABLE teams_tasks
        ADD COLUMN IF NOT EXISTS resposta_card JSONB
    """))
    print("[OK] Coluna teams_tasks.resposta_card adicionada (JSONB, nullable)")
    db.session.commit()


def verificar_depois():
    """Verifica estado apos a migration."""
    col = db.session.execute(db.text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'teams_tasks' AND column_name = 'resposta_card'
    """)).fetchone()

    assert col is not None, "resposta_card nao foi criada"
    assert col[1] == 'jsonb', f"Esperado jsonb, obtido {col[1]}"
    assert col[2] == 'YES', f"Esperado nullable YES, obtido {col[2]}"

    print(f"[AFTER] teams_tasks.resposta_card OK: type={col[1]} nullable={col[2]}")

    total_tasks = db.session.execute(db.text(
        "SELECT COUNT(*) FROM teams_tasks"
    )).scalar()
    print(f"[DATA] {total_tasks} tasks existentes (nenhuma backfill necessario, nullable)")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        ja_existe = verificar_antes()
        if ja_existe:
            print("[SKIP] Coluna ja existe — nada a fazer")
        else:
            executar_migration()
        verificar_depois()
        print("[DONE] Migration concluida com sucesso")
