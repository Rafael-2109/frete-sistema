#!/usr/bin/env python3
"""
Hook PostToolUse: Auto-regenerar Schemas apos editar models.py

Detecta edicoes em arquivos models.py e EXECUTA automaticamente
o generate_schemas.py para manter os schemas JSON atualizados.

Exit 0 sempre — falha na regeneracao nao deve bloquear o fluxo.
"""

import json
import os
import subprocess
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
        if not file_path.endswith("models.py"):
            return

        # Descobrir diretorio do projeto
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            # Fallback: subir a partir do file_path ate encontrar .claude/
            d = os.path.dirname(os.path.abspath(file_path))
            for _ in range(10):
                if os.path.isdir(os.path.join(d, ".claude")):
                    project_dir = d
                    break
                d = os.path.dirname(d)

        if not project_dir:
            print("Hook: nao encontrou project_dir, pulando regeneracao", file=sys.stderr)
            return

        script = os.path.join(
            project_dir, ".claude", "skills", "consultando-sql", "scripts", "generate_schemas.py"
        )
        venv_python = os.path.join(project_dir, ".venv", "bin", "python")

        if not os.path.isfile(script):
            print(f"Hook: script nao encontrado: {script}", file=sys.stderr)
            return

        python_bin = venv_python if os.path.isfile(venv_python) else sys.executable

        # Executar regeneracao (timeout 30s, silencioso em sucesso)
        result = subprocess.run(
            [python_bin, script],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(
                f"Hook: schemas regenerados automaticamente apos editar {os.path.basename(file_path)}",
                file=sys.stderr,
            )
        else:
            print(
                f"Hook: ERRO ao regenerar schemas (exit {result.returncode})\n"
                f"  stderr: {result.stderr[:300]}",
                file=sys.stderr,
            )

    except subprocess.TimeoutExpired:
        print("Hook: timeout ao regenerar schemas (>30s)", file=sys.stderr)
    except Exception as e:
        print(f"Hook: erro inesperado: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
