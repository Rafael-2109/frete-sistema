"""Migration: modulo WhatsApp (canal alternativo via OpenClaw + Baileys).

1. Adiciona `usuarios.whatsapp_autorizado` (BOOLEAN, opt-in explicito).
2. Cria index parcial `ix_usuarios_telefone_whatsapp` para lookup rapido.
3. Cria tabela `whatsapp_tasks` (lifecycle async, espelha `teams_tasks`).

Idempotente: usa IF NOT EXISTS em todas as DDL.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db


# ─── Verificacoes ────────────────────────────────────────────────────────

def _column_exists(table: str, column: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :t AND column_name = :c
    """), {"t": table, "c": column}).scalar())


def _index_exists(table: str, index: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM pg_indexes
        WHERE tablename = :t AND indexname = :i
    """), {"t": table, "i": index}).scalar())


def _table_exists(table: str) -> bool:
    return bool(db.session.execute(db.text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_name = :t
    """), {"t": table}).scalar())


def verificar_antes():
    print("=== ANTES ===")
    print(f"  usuarios.whatsapp_autorizado existe: "
          f"{_column_exists('usuarios', 'whatsapp_autorizado')}")
    print(f"  index ix_usuarios_telefone_whatsapp existe: "
          f"{_index_exists('usuarios', 'ix_usuarios_telefone_whatsapp')}")
    print(f"  tabela whatsapp_tasks existe: {_table_exists('whatsapp_tasks')}")


# ─── Migration ───────────────────────────────────────────────────────────

def executar_migration():
    print("=== EXECUTANDO ===")

    # 1. Coluna whatsapp_autorizado
    db.session.execute(db.text("""
        ALTER TABLE usuarios
            ADD COLUMN IF NOT EXISTS whatsapp_autorizado BOOLEAN NOT NULL DEFAULT FALSE
    """))
    db.session.execute(db.text("""
        COMMENT ON COLUMN usuarios.whatsapp_autorizado IS
            'Opt-in explicito do usuario para receber/enviar mensagens via WhatsApp Bot.'
    """))
    print("[OK] usuarios.whatsapp_autorizado adicionada")

    # 2. Index parcial
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_usuarios_telefone_whatsapp
            ON usuarios (telefone)
            WHERE whatsapp_autorizado = TRUE
              AND telefone IS NOT NULL
              AND telefone <> ''
    """))
    print("[OK] index ix_usuarios_telefone_whatsapp criado")

    # 3. Tabela whatsapp_tasks
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS whatsapp_tasks (
            id VARCHAR(36) PRIMARY KEY,
            peer_jid VARCHAR(120) NOT NULL,
            conversation_jid VARCHAR(120) NOT NULL,
            is_group BOOLEAN NOT NULL DEFAULT FALSE,
            sender_name VARCHAR(200),
            user_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            mensagem TEXT NOT NULL,
            resposta TEXT,
            pending_questions JSON,
            pending_question_session_id VARCHAR(255),
            openclaw_message_id VARCHAR(120),
            openclaw_session_key VARCHAR(255),
            created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
            completed_at TIMESTAMP WITHOUT TIME ZONE
        )
    """))
    print("[OK] tabela whatsapp_tasks criada")

    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_peer_jid
            ON whatsapp_tasks (peer_jid)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_status
            ON whatsapp_tasks (status)
    """))
    db.session.execute(db.text("""
        CREATE INDEX IF NOT EXISTS ix_whatsapp_tasks_conversation_jid
            ON whatsapp_tasks (conversation_jid)
    """))
    print("[OK] indexes whatsapp_tasks criados")

    db.session.commit()


# ─── Verificacoes pos ────────────────────────────────────────────────────

def verificar_depois():
    print("=== DEPOIS ===")
    coluna = _column_exists('usuarios', 'whatsapp_autorizado')
    idx_user = _index_exists('usuarios', 'ix_usuarios_telefone_whatsapp')
    tabela = _table_exists('whatsapp_tasks')
    idx_peer = _index_exists('whatsapp_tasks', 'ix_whatsapp_tasks_peer_jid')
    idx_status = _index_exists('whatsapp_tasks', 'ix_whatsapp_tasks_status')

    print(f"  usuarios.whatsapp_autorizado: {coluna}")
    print(f"  index usuarios telefone whatsapp: {idx_user}")
    print(f"  tabela whatsapp_tasks: {tabela}")
    print(f"  index whatsapp_tasks peer_jid: {idx_peer}")
    print(f"  index whatsapp_tasks status: {idx_status}")

    assert coluna, "usuarios.whatsapp_autorizado nao foi criado"
    assert idx_user, "index ix_usuarios_telefone_whatsapp nao foi criado"
    assert tabela, "tabela whatsapp_tasks nao foi criada"
    assert idx_peer and idx_status, "indexes whatsapp_tasks faltando"


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("\n[DONE] Migration whatsapp_module concluida com sucesso")
