#!/usr/bin/env python3
"""
Script: generate_debug_schemas.py
Gera schemas JSON para tabelas bloqueadas (uso exclusivo do Debug Mode admin).

Reutiliza a mesma logica do generate_schemas.py mas gera schemas apenas
para as tabelas listadas em BLOCKED_TABLES do generate_schemas.py.

Saida: .claude/skills/consultando-sql/schemas/debug_tables/{tabela}.json

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/generate_debug_schemas.py
    python scripts/generate_debug_schemas.py --dry-run  # apenas lista tabelas
"""
import sys
import os
import json
import argparse

# Adicionar raiz do projeto ao path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

# Diretorio de output
SCHEMAS_DIR = os.path.join(
    PROJECT_ROOT, '.claude', 'skills', 'consultando-sql', 'schemas'
)
DEBUG_TABLES_DIR = os.path.join(SCHEMAS_DIR, 'debug_tables')

# Tabelas bloqueadas — mesma lista do generate_schemas.py
# Fonte: .claude/skills/consultando-sql/scripts/generate_schemas.py:36-51
BLOCKED_TABLES = {
    # Auth / Permissoes
    'usuarios', 'permission_category', 'permission_module',
    'permission_submodule', 'user_permission', 'permission_template',
    'permission_cache', 'permission_log', 'batch_operation',
    'perfil_usuario', 'vendedor_permission', 'equipe_permission',
    # Agente (tabelas internas)
    'agent_sessions', 'agent_memories', 'agent_memory_versions',
    'agent_memory_embeddings', 'session_turn_embeddings',
    # Alembic
    'alembic_version',
    # Sessoes web
    'portal_sessoes',
    # Tokens/OAuth
    'tagplus_oauth_token',
}


def generate_table_schema(inspector, table_name: str) -> dict:
    """
    Gera schema JSON para uma tabela usando SQLAlchemy inspect.

    Args:
        inspector: SQLAlchemy Inspector instance
        table_name: Nome da tabela

    Returns:
        Dict com schema da tabela
    """
    try:
        columns = inspector.get_columns(table_name)
    except Exception:
        return None

    schema = {
        "name": table_name,
        "description": f"[DEBUG] Tabela interna: {table_name}",
        "columns": [],
        "primary_key": [],
        "foreign_keys": [],
        "indexes": [],
    }

    # Colunas
    for col in columns:
        col_info = {
            "name": col["name"],
            "type": str(col["type"]),
            "nullable": col.get("nullable", True),
        }
        if col.get("default") is not None:
            col_info["default"] = str(col["default"])
        if col.get("comment"):
            col_info["description"] = col["comment"]
        schema["columns"].append(col_info)

    # Primary key
    try:
        pk = inspector.get_pk_constraint(table_name)
        if pk and pk.get("constrained_columns"):
            schema["primary_key"] = pk["constrained_columns"]
    except Exception:
        pass

    # Foreign keys
    try:
        fks = inspector.get_foreign_keys(table_name)
        for fk in fks:
            schema["foreign_keys"].append({
                "columns": fk.get("constrained_columns", []),
                "referred_table": fk.get("referred_table", ""),
                "referred_columns": fk.get("referred_columns", []),
            })
    except Exception:
        pass

    # Indexes
    try:
        indexes = inspector.get_indexes(table_name)
        for idx in indexes:
            schema["indexes"].append({
                "name": idx.get("name", ""),
                "columns": idx.get("column_names", []),
                "unique": idx.get("unique", False),
            })
    except Exception:
        pass

    return schema


def main():
    parser = argparse.ArgumentParser(description="Gera schemas JSON para tabelas bloqueadas (Debug Mode)")
    parser.add_argument("--dry-run", action="store_true", help="Lista tabelas sem gerar schemas")
    args = parser.parse_args()

    print(f"=== Generate Debug Schemas ===")
    print(f"Tabelas bloqueadas: {len(BLOCKED_TABLES)}")
    print(f"Output: {DEBUG_TABLES_DIR}")
    print()

    if args.dry_run:
        for t in sorted(BLOCKED_TABLES):
            print(f"  - {t}")
        print(f"\nTotal: {len(BLOCKED_TABLES)} tabelas")
        return

    # Criar app context para acessar banco
    from app import create_app
    app = create_app()

    with app.app_context():
        from sqlalchemy import inspect
        from app import db

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())

        # Criar diretorio de output
        os.makedirs(DEBUG_TABLES_DIR, exist_ok=True)

        generated = 0
        skipped = 0

        for table_name in sorted(BLOCKED_TABLES):
            if table_name not in existing_tables:
                print(f"  SKIP {table_name} (nao existe no banco)")
                skipped += 1
                continue

            schema = generate_table_schema(inspector, table_name)
            if schema is None:
                print(f"  ERRO {table_name} (falha ao inspecionar)")
                skipped += 1
                continue

            output_path = os.path.join(DEBUG_TABLES_DIR, f"{table_name}.json")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schema, f, ensure_ascii=False, indent=2)

            col_count = len(schema.get("columns", []))
            print(f"  OK   {table_name} ({col_count} colunas)")
            generated += 1

        print(f"\nResultado: {generated} gerados, {skipped} ignorados")
        print(f"Schemas em: {DEBUG_TABLES_DIR}")


if __name__ == '__main__':
    main()
