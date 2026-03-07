"""
Migration: Sanitizacao de Memorias do Agente Web

Corrige 4 problemas identificados na auditoria de 07/03/2026:
1. Deleta 42 diretorios vazios (is_directory=true, sem uso)
2. Deleta meta-junk empresa (memorias sobre o proprio sistema de IA)
3. Deleta duplicatas empresa (regras que duplicam outras com wording diferente)
4. Migra admin corrections de broadcast (N copias por user) para escopo empresa (1 copia, user_id=0)
5. Limpa embeddings orfaos (memory_id inexistente)

Ref: Auditoria Sistema de Memoria v5.0 — 07/03/2026
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


# =====================================================================
# IDs a deletar (confirmados na auditoria de 07/03/2026)
# =====================================================================

# Meta-junk: memorias sobre o proprio sistema de IA (nao conhecimento operacional)
META_JUNK_IDS = [
    113, 114, 116, 117, 118, 119, 120, 121,  # termos meta (escopo, hook, prd, etc.)
    126, 127, 128,                              # mais termos meta
    130, 131, 132,                              # correcoes meta (sobre PRD/RAG/hook)
    133,                                        # GR = exemplo de teste, confirmado pelo usuario
    134, 135,                                   # regras meta
    140,                                        # termo meta
    144, 147, 148,                              # correcoes Gilberto (pessoa ficticia de teste)
]

# Duplicatas: regras que duplicam outras com wording diferente
DUPLICATE_IDS = [
    142,  # duplica 111 (regra Assai)
    143,  # duplica 112 (regra Assai)
    145,  # duplica 110
    146,  # duplica 139 (Atacadao NF)
]

# Admin corrections: paths que foram broadcast para N usuarios
# Serao migrados para user_id=0/escopo='empresa' e copias individuais deletadas
ADMIN_CORRECTION_PATHS = [
    '/memories/corrections/agent-sdk-production-scope.xml',
    '/memories/corrections/capacidade-caminhoes-consultar-veiculos.xml',
    '/memories/corrections/confirmar-para-pedido-odoo.xml',
]


def check_before(conn):
    """Verifica estado antes da sanitizacao."""
    print("=== BEFORE ===")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories"))
    print(f"  Total memorias: {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE is_directory = true"))
    print(f"  Diretorios vazios: {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE user_id = 0"))
    print(f"  Memorias empresa (user_id=0): {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE escopo = 'empresa'"))
    print(f"  Memorias escopo empresa: {result.scalar()}")

    # Admin corrections broadcast
    for path in ADMIN_CORRECTION_PATHS:
        result = conn.execute(text(
            "SELECT COUNT(*) FROM agent_memories WHERE path = :path"
        ), {"path": path})
        count = result.scalar()
        print(f"  Correction '{path.split('/')[-1]}': {count} copias")

    # Embeddings
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM agent_memory_embeddings"))
        print(f"  Embeddings total: {result.scalar()}")
    except Exception:
        print("  Embeddings: tabela nao existe")

    # KG
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM agent_memory_entities"))
        print(f"  KG entities: {result.scalar()}")
    except Exception:
        print("  KG entities: tabela nao existe")

    print()


def run_migration(conn):
    """Executa sanitizacao."""

    # 1. Deletar diretorios vazios
    result = conn.execute(text(
        "DELETE FROM agent_memories WHERE is_directory = true"
    ))
    print(f"[1/5] Diretorios vazios deletados: {result.rowcount}")

    # 2. Deletar meta-junk
    if META_JUNK_IDS:
        result = conn.execute(text(
            "DELETE FROM agent_memories WHERE id = ANY(:ids)"
        ), {"ids": META_JUNK_IDS})
        print(f"[2/5] Meta-junk deletado: {result.rowcount} (IDs: {META_JUNK_IDS})")
    else:
        print("[2/5] Nenhum meta-junk para deletar")

    # 3. Deletar duplicatas
    if DUPLICATE_IDS:
        result = conn.execute(text(
            "DELETE FROM agent_memories WHERE id = ANY(:ids)"
        ), {"ids": DUPLICATE_IDS})
        print(f"[3/5] Duplicatas deletadas: {result.rowcount} (IDs: {DUPLICATE_IDS})")
    else:
        print("[3/5] Nenhuma duplicata para deletar")

    # 4. Migrar admin corrections para escopo empresa
    for path in ADMIN_CORRECTION_PATHS:
        # Pegar conteudo de uma copia existente (qualquer user)
        result = conn.execute(text(
            "SELECT content, created_at FROM agent_memories "
            "WHERE path = :path ORDER BY id LIMIT 1"
        ), {"path": path})
        row = result.fetchone()

        if not row:
            print(f"  [4/5] Correction '{path.split('/')[-1]}': nao encontrado, skip")
            continue

        content = row[0]
        created_at = row[1]

        # Deletar TODAS as copias individuais (qualquer user_id)
        result = conn.execute(text(
            "DELETE FROM agent_memories WHERE path = :path"
        ), {"path": path})
        deleted = result.rowcount

        # Criar versao empresa (user_id=0)
        conn.execute(text("""
            INSERT INTO agent_memories (user_id, path, content, is_directory, escopo, created_by,
                                        importance_score, category, created_at, updated_at)
            VALUES (0, :path, :content, false, 'empresa', NULL,
                    0.9, 'permanent', :created_at, :created_at)
        """), {
            "path": path,
            "content": content,
            "created_at": created_at,
        })
        print(f"  [4/5] Correction '{path.split('/')[-1]}': {deleted} copias → 1 empresa")

    # 5. Limpar embeddings orfaos
    try:
        result = conn.execute(text("""
            DELETE FROM agent_memory_embeddings
            WHERE memory_id IS NOT NULL
              AND memory_id NOT IN (SELECT id FROM agent_memories)
        """))
        print(f"[5/5] Embeddings orfaos deletados: {result.rowcount}")
    except Exception as e:
        print(f"[5/5] Embeddings orfaos: erro (ignorado): {e}")


def check_after(conn):
    """Verifica estado apos sanitizacao."""
    print("\n=== AFTER ===")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories"))
    print(f"  Total memorias: {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE is_directory = true"))
    print(f"  Diretorios vazios: {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE user_id = 0"))
    print(f"  Memorias empresa (user_id=0): {result.scalar()}")

    result = conn.execute(text("SELECT COUNT(*) FROM agent_memories WHERE escopo = 'empresa'"))
    print(f"  Memorias escopo empresa: {result.scalar()}")

    # Verificar que admin corrections tem apenas 1 copia cada
    for path in ADMIN_CORRECTION_PATHS:
        result = conn.execute(text(
            "SELECT COUNT(*), "
            "       COALESCE(MIN(user_id), -1) "
            "FROM agent_memories WHERE path = :path"
        ), {"path": path})
        row = result.fetchone()
        print(f"  Correction '{path.split('/')[-1]}': {row[0]} copia(s), user_id={row[1]}")

    try:
        result = conn.execute(text("SELECT COUNT(*) FROM agent_memory_embeddings"))
        print(f"  Embeddings total: {result.scalar()}")
    except Exception:
        pass

    try:
        result = conn.execute(text("SELECT COUNT(*) FROM agent_memory_entities"))
        print(f"  KG entities: {result.scalar()}")
    except Exception:
        pass


def main():
    app = create_app()

    with app.app_context():
        with db.engine.begin() as conn:
            check_before(conn)
            run_migration(conn)
            check_after(conn)

    print("\n=== SANITIZACAO CONCLUIDA ===")


if __name__ == '__main__':
    main()
