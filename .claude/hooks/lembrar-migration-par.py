#!/usr/bin/env python3
"""
Hook PostToolUse: Lembrete de Migration Par (.py + .sql)

Detecta criacao/edicao de arquivos em scripts/migrations/ e avisa
se o par correspondente (.py <-> .sql) nao existe.

Nao bloqueia (exit 0 sempre). Apenas imprime aviso em stderr.
"""

import json
import os
import sys


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        if tool_name not in ("Write", "Edit"):
            return

        file_path = tool_input.get("file_path", "")

        # So interessa arquivos em scripts/migrations/
        if "scripts/migrations/" not in file_path:
            return

        base, ext = os.path.splitext(file_path)

        if ext == ".py":
            par = base + ".sql"
            tipo_faltante = "SQL"
        elif ext == ".sql":
            par = base + ".py"
            tipo_faltante = "Python"
        else:
            return

        if not os.path.exists(par):
            nome_base = os.path.basename(base)
            print(
                "\n"
                "================================================\n"
                f"  MIGRATION: par {tipo_faltante} NAO encontrado\n"
                "================================================\n"
                f"  Criado:   {os.path.basename(file_path)}\n"
                f"  Faltando: {nome_base}{'.sql' if ext == '.py' else '.py'}\n"
                "\n"
                "  Regra: DDL requer DOIS artefatos (.py + .sql).\n"
                "  Excecao: data fixes (UPDATE/INSERT) podem ser so .py.\n"
                "================================================\n",
                file=sys.stderr,
            )

    except Exception:
        pass  # Hook nao deve bloquear nunca


if __name__ == "__main__":
    main()
