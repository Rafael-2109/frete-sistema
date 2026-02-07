#!/usr/bin/env python3
"""
Hook de Notificacao para Alteracoes Importantes

Este hook registra alteracoes importantes para fins de auditoria.

PERSISTENCIA:
- Opcao 1: Banco de dados PostgreSQL (recomendado para producao)
- Opcao 2: Arquivo local (apenas desenvolvimento)

Uso: Configurado em .claude/settings.local.json como PostToolUse hook
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Categorias de alteracoes importantes
CATEGORIAS = {
    "separacao": {
        "keywords": ["separacao", "separacoes", "criar_separacao"],
        "nivel": "INFO",
        "descricao": "Operacao de separacao",
    },
    "pedido": {
        "keywords": ["pedido", "num_pedido", "carteira"],
        "nivel": "INFO",
        "descricao": "Alteracao em pedido",
    },
    "frete": {
        "keywords": ["frete", "cotacao", "embarque"],
        "nivel": "INFO",
        "descricao": "Operacao de frete",
    },
    "odoo": {
        "keywords": ["odoo", "lancamento", "integracao"],
        "nivel": "WARNING",
        "descricao": "Integracao com Odoo",
    },
    "modelo": {
        "keywords": ["models.py", "migration", "alter table"],
        "nivel": "CRITICAL",
        "descricao": "Alteracao em modelo de dados",
    },
}


def categorize_operation(tool_input: dict) -> list[dict]:
    """Categoriza a operacao com base no conteudo."""
    content = json.dumps(tool_input).lower()
    categorias_encontradas = []

    for cat_name, cat_info in CATEGORIAS.items():
        for keyword in cat_info["keywords"]:
            if keyword in content:
                categorias_encontradas.append(
                    {
                        "categoria": cat_name,
                        "nivel": cat_info["nivel"],
                        "descricao": cat_info["descricao"],
                    }
                )
                break

    return categorias_encontradas


def save_to_database(notification: dict) -> bool:
    """
    Tenta salvar no banco de dados PostgreSQL.
    Usa a mesma tabela claude_audit_log com operation_type diferente.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return False

    try:
        import psycopg2
        from psycopg2.extras import Json

        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Cria tabela se nao existir (mesma do audit-separacao)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS claude_audit_log (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMPTZ DEFAULT NOW(),
                tool VARCHAR(50),
                file_path TEXT,
                user_name VARCHAR(100),
                session_id VARCHAR(100),
                operation_type VARCHAR(50),
                details JSONB,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_claude_audit_timestamp
            ON claude_audit_log(timestamp DESC);

            CREATE INDEX IF NOT EXISTS idx_claude_audit_operation_type
            ON claude_audit_log(operation_type);
        """)

        # Insere registro
        cur.execute(
            """
            INSERT INTO claude_audit_log
            (timestamp, tool, file_path, user_name, session_id, operation_type, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                notification["timestamp"],
                notification["tool"],
                notification["file_path"],
                notification["user"],
                os.environ.get("CLAUDE_SESSION_ID", "unknown"),
                f"notificacao_{notification['nivel'].lower()}",
                Json({
                    "categorias": notification["categorias"],
                    "descricao": notification["descricao"],
                    "nivel": notification["nivel"],
                }),
            ),
        )

        conn.commit()
        cur.close()
        conn.close()
        return True

    except ImportError:
        return False
    except Exception as e:
        print(f"[NOTIFICACAO] Erro ao salvar no banco: {e}", file=sys.stderr)
        return False


def save_to_file(notification: dict) -> None:
    """Fallback: salva em arquivo local (apenas desenvolvimento)."""
    notifications_dir = Path(__file__).parent.parent.parent / "logs" / "notifications"
    notifications_file = notifications_dir / "alteracoes.jsonl"

    notifications_dir.mkdir(parents=True, exist_ok=True)

    with open(notifications_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(notification, ensure_ascii=False) + "\n")


def main():
    """Processa o evento do hook e registra notificacoes."""
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Categoriza a operacao
        categorias = categorize_operation(tool_input)

        if not categorias:
            return

        # Determina o nivel mais critico
        niveis = {"INFO": 1, "WARNING": 2, "CRITICAL": 3}
        nivel_max = max(categorias, key=lambda x: niveis.get(x["nivel"], 0))

        # Cria notificacao
        notification = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "nivel": nivel_max["nivel"],
            "tool": tool_name,
            "file_path": tool_input.get("file_path", ""),
            "categorias": [c["categoria"] for c in categorias],
            "descricao": nivel_max["descricao"],
            "user": os.environ.get("USER", "unknown"),
        }

        # Tenta salvar no banco, senao usa arquivo
        saved_to_db = save_to_database(notification)

        if not saved_to_db:
            save_to_file(notification)

        # Output visual baseado no nivel (independente de onde salvou)
        if nivel_max["nivel"] == "CRITICAL":
            print(
                f"\n🔴 ALTERACAO CRITICA: {nivel_max['descricao']}\n"
                f"   Arquivo: {tool_input.get('file_path', 'N/A')}\n",
                file=sys.stderr,
            )
        elif nivel_max["nivel"] == "WARNING":
            print(
                f"\n🟡 ATENCAO: {nivel_max['descricao']}\n",
                file=sys.stderr,
            )

    except Exception as e:
        print(f"[NOTIFICACAO] Erro: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
