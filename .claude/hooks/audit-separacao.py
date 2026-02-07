#!/usr/bin/env python3
"""
Hook de Auditoria para Separacoes

Este hook e executado apos operacoes Write/Edit que envolvem separacoes,
registrando todas as alteracoes para fins de auditoria e rastreabilidade.

PERSISTENCIA:
- Opcao 1: Banco de dados PostgreSQL (recomendado para producao)
- Opcao 2: Arquivo local (apenas desenvolvimento)

O hook tenta gravar no banco primeiro, se falhar usa arquivo local.

Uso: Configurado em .claude/settings.local.json como PostToolUse hook
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Palavras-chave que identificam operacoes de separacao
SEPARACAO_KEYWORDS = [
    "separacao",
    "separacoes",
    "criando_separacao",
    "separacao_lote_id",
]


def is_separacao_operation(tool_input: dict) -> bool:
    """Verifica se a operacao envolve separacoes."""
    file_path = tool_input.get("file_path", "").lower()
    for keyword in SEPARACAO_KEYWORDS:
        if keyword in file_path:
            return True

    content = tool_input.get("content", "").lower()
    new_string = tool_input.get("new_string", "").lower()

    for keyword in SEPARACAO_KEYWORDS:
        if keyword in content or keyword in new_string:
            return True

    return False


def save_to_database(audit_entry: dict) -> bool:
    """
    Tenta salvar no banco de dados PostgreSQL.

    Usa a tabela audit_log existente ou cria se necessario.
    Requer DATABASE_URL configurado.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return False

    try:
        import psycopg2
        from psycopg2.extras import Json

        conn = psycopg2.connect(database_url)
        cur = conn.cursor()

        # Cria tabela se nao existir
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

            CREATE INDEX IF NOT EXISTS idx_claude_audit_file_path
            ON claude_audit_log(file_path);
        """)

        # Insere registro
        cur.execute(
            """
            INSERT INTO claude_audit_log
            (timestamp, tool, file_path, user_name, session_id, operation_type, details)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                audit_entry["timestamp"],
                audit_entry["tool"],
                audit_entry["file_path"],
                audit_entry["user"],
                audit_entry["session_id"],
                "separacao",
                Json(audit_entry.get("operation_details", {})),
            ),
        )

        conn.commit()
        cur.close()
        conn.close()
        return True

    except ImportError:
        # psycopg2 nao instalado
        return False
    except Exception as e:
        print(f"[AUDIT] Erro ao salvar no banco: {e}", file=sys.stderr)
        return False


def save_to_file(audit_entry: dict) -> None:
    """Fallback: salva em arquivo local (apenas desenvolvimento)."""
    audit_dir = Path(__file__).parent.parent.parent / "logs" / "audit"
    audit_file = audit_dir / "separacoes_audit.jsonl"

    audit_dir.mkdir(parents=True, exist_ok=True)

    with open(audit_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(audit_entry, ensure_ascii=False) + "\n")


def main():
    """
    Processa o evento do hook.

    O hook recebe dados via stdin no formato JSON:
    {
        "tool_name": "Write" | "Edit",
        "tool_input": { ... parametros da ferramenta ... },
        "tool_output": { ... resultado da ferramenta ... }
    }
    """
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        if not is_separacao_operation(tool_input):
            return

        # Cria entrada de auditoria
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "tool": tool_name,
            "file_path": tool_input.get("file_path", ""),
            "user": os.environ.get("USER", "unknown"),
            "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
            "operation_details": {
                "old_string": tool_input.get("old_string", "")[:200] if tool_input.get("old_string") else None,
                "new_string": tool_input.get("new_string", "")[:200] if tool_input.get("new_string") else None,
                "content_preview": tool_input.get("content", "")[:200] if tool_input.get("content") else None,
            },
        }

        # Remove campos None
        audit_entry["operation_details"] = {
            k: v for k, v in audit_entry["operation_details"].items() if v is not None
        }

        # Tenta salvar no banco, senao usa arquivo
        if not save_to_database(audit_entry):
            save_to_file(audit_entry)
            print(f"[AUDIT] Separacao registrada em arquivo local", file=sys.stderr)
        else:
            print(f"[AUDIT] Separacao registrada no banco de dados", file=sys.stderr)

    except json.JSONDecodeError:
        print("[AUDIT] Erro: Input nao e JSON valido", file=sys.stderr)
    except Exception as e:
        print(f"[AUDIT] Erro: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
