"""
Migration: Adicionar coluna sdk_session_transcript na tabela agent_sessions.

Motivacao:
    O SDK `resume` depende de arquivos JSONL no disco (~/.claude/projects/...).
    Quando o worker Render recicla, esses arquivos se perdem e o resume falha
    silenciosamente — o agente perde todo o contexto da conversa.

    Este campo TEXT armazena o conteudo completo do JSONL para restore posterior.
    Separado do campo JSONB `data` para evitar overhead de reescrita JSONB.

Operacao NAO-DESTRUTIVA: apenas adiciona coluna nullable (sem default).

Uso:
    source .venv/bin/activate
    python scripts/migration_add_sdk_session_transcript.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from sqlalchemy import text


def executar_migration():
    """Adiciona coluna sdk_session_transcript TEXT na tabela agent_sessions."""
    app = create_app()

    with app.app_context():
        # Verifica se coluna ja existe
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'agent_sessions'
              AND column_name = 'sdk_session_transcript'
        """))
        if result.fetchone():
            print("[OK] Coluna sdk_session_transcript ja existe — nada a fazer.")
            return

        # Adiciona coluna
        print("[MIGRATION] Adicionando coluna sdk_session_transcript...")
        db.session.execute(text("""
            ALTER TABLE agent_sessions
            ADD COLUMN sdk_session_transcript TEXT
        """))
        db.session.commit()
        print("[OK] Coluna sdk_session_transcript adicionada com sucesso.")

        # Verificacao
        result = db.session.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'agent_sessions'
              AND column_name = 'sdk_session_transcript'
        """))
        row = result.fetchone()
        if row:
            print(f"[VERIFICACAO] {row[0]} — tipo: {row[1]}")
        else:
            print("[ERRO] Coluna nao encontrada apos migration!")


if __name__ == '__main__':
    executar_migration()
