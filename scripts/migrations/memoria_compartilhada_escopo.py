"""
Migration: Memoria Compartilhada por Escopo

Adiciona infraestrutura para memorias empresa (user_id=0):
1. Usuario Sistema (id=0) na tabela usuarios
2. Coluna escopo em agent_memories ('pessoal' ou 'empresa')
3. Coluna created_by em agent_memories (auditoria)
4. Indice parcial para escopo='empresa'

Ref: PRD v2.1 — Sistema de Memorias do Agent SDK
Data: 2026-03-06
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def check_before(conn):
    """Verifica estado antes da migration."""
    print("=== BEFORE ===")

    # Usuario id=0
    result = conn.execute(text("SELECT id, nome FROM usuarios WHERE id = 0"))
    row = result.fetchone()
    print(f"  Usuario id=0: {'EXISTS - ' + row[1] if row else 'NAO EXISTE'}")

    # Colunas em agent_memories
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('agent_memories')}
    print(f"  Coluna escopo: {'EXISTS' if 'escopo' in columns else 'NAO EXISTE'}")
    print(f"  Coluna created_by: {'EXISTS' if 'created_by' in columns else 'NAO EXISTE'}")

    # Indice
    indexes = {idx['name'] for idx in inspector.get_indexes('agent_memories')}
    print(f"  Indice escopo_empresa: {'EXISTS' if 'idx_agent_memories_escopo_empresa' in indexes else 'NAO EXISTE'}")


def run_migration(conn):
    """Executa a migration."""
    print("\n=== MIGRATION ===")

    # 1. Criar usuario Sistema (id=0)
    result = conn.execute(text("SELECT id FROM usuarios WHERE id = 0"))
    if not result.fetchone():
        conn.execute(text("""
            INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status, criado_em)
            VALUES (0, 'Sistema', 'sistema@nacom.com.br', 'NOLOGIN', 'sistema', 'ativo', NOW())
        """))
        print("  [OK] Usuario Sistema (id=0) criado")
    else:
        print("  [SKIP] Usuario Sistema (id=0) ja existe")

    # 2. Coluna escopo
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('agent_memories')}

    if 'escopo' not in columns:
        conn.execute(text(
            "ALTER TABLE agent_memories ADD COLUMN escopo VARCHAR(20) NOT NULL DEFAULT 'pessoal'"
        ))
        print("  [OK] Coluna escopo adicionada")
    else:
        print("  [SKIP] Coluna escopo ja existe")

    # 3. Coluna created_by
    if 'created_by' not in columns:
        conn.execute(text(
            "ALTER TABLE agent_memories ADD COLUMN created_by INTEGER"
        ))
        print("  [OK] Coluna created_by adicionada")
    else:
        print("  [SKIP] Coluna created_by ja existe")

    # 4. FK created_by
    result = conn.execute(text("""
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_memory_created_by'
    """))
    if not result.fetchone():
        conn.execute(text("""
            ALTER TABLE agent_memories
                ADD CONSTRAINT fk_memory_created_by
                FOREIGN KEY (created_by) REFERENCES usuarios(id) ON DELETE SET NULL
        """))
        print("  [OK] FK fk_memory_created_by criada")
    else:
        print("  [SKIP] FK fk_memory_created_by ja existe")

    # 5. Indice parcial
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_agent_memories_escopo_empresa
            ON agent_memories (user_id, escopo) WHERE escopo = 'empresa'
    """))
    print("  [OK] Indice idx_agent_memories_escopo_empresa criado/verificado")


def check_after(conn):
    """Verifica estado apos a migration."""
    print("\n=== AFTER ===")

    # Usuario id=0
    result = conn.execute(text("SELECT id, nome, perfil FROM usuarios WHERE id = 0"))
    row = result.fetchone()
    if row:
        print(f"  Usuario id=0: {row[1]} (perfil={row[2]})")
    else:
        print("  [ERRO] Usuario id=0 NAO encontrado!")

    # Colunas
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('agent_memories')}
    assert 'escopo' in columns, "Coluna escopo NAO encontrada!"
    assert 'created_by' in columns, "Coluna created_by NAO encontrada!"
    print(f"  Colunas escopo e created_by: OK")

    # Contagem de memorias
    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories"))
    total = result.scalar()
    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE escopo = 'empresa'"))
    empresa = result.scalar()
    print(f"  Total memorias: {total} (empresa: {empresa})")


def main():
    app = create_app()
    with app.app_context():
        with db.engine.begin() as conn:
            check_before(conn)
            run_migration(conn)
            check_after(conn)
    print("\n[DONE] Migration concluida com sucesso.")


if __name__ == '__main__':
    main()
