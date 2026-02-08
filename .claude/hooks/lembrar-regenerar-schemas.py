#!/usr/bin/env python3
"""
Hook PostToolUse: Lembrete de Regenerar Schemas

Detecta edicoes em arquivos models.py e imprime aviso para regenerar
os schemas JSON usados pelo agente SQL.

Nao bloqueia (exit 0 sempre). Apenas imprime aviso em stderr.
"""

import json
import sys


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Detecta Write ou Edit em arquivos models.py
        if tool_name not in ("Write", "Edit"):
            return

        file_path = tool_input.get("file_path", "")
        if not file_path.endswith("models.py"):
            return

        print(
            "\n"
            "================================================\n"
            "  MODELO ALTERADO — Regenerar schemas do agente\n"
            "================================================\n"
            f"  Arquivo: {file_path}\n"
            "\n"
            "  Executar:\n"
            "  source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py\n"
            "================================================\n",
            file=sys.stderr,
        )

    except Exception:
        pass  # Hook nao deve bloquear nunca


if __name__ == "__main__":
    main()
