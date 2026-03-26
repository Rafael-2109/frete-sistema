#!/usr/bin/env python3
"""
Hook PostToolUse: Rodar testes automaticamente apos editar Python.

Detecta edicoes em arquivos .py (exceto /tmp/) e roda pytest
para feedback imediato de regressao.

Ethismos computacional: cada erro detectado imediatamente refina a proxima edicao.

Exit 0 sempre — falha nos testes nao deve bloquear o fluxo.
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

        if tool_name not in ("Edit", "Write"):
            return

        file_path = tool_input.get("file_path", "")
        if not file_path.endswith(".py"):
            return

        # Ignorar arquivos em /tmp/
        if file_path.startswith("/tmp/") or file_path.startswith("/tmp\\"):
            return

        # Descobrir diretorio do projeto
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            d = os.path.dirname(os.path.abspath(file_path))
            for _ in range(10):
                if os.path.isdir(os.path.join(d, ".claude")):
                    project_dir = d
                    break
                d = os.path.dirname(d)

        if not project_dir:
            return

        tests_dir = os.path.join(project_dir, "tests")
        if not os.path.isdir(tests_dir):
            return

        venv_python = os.path.join(project_dir, ".venv", "bin", "python")
        python_bin = venv_python if os.path.isfile(venv_python) else sys.executable

        result = subprocess.run(
            [python_bin, "-m", "pytest", "tests/", "--tb=short", "-q", "--timeout=30"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=45,
        )

        # Mostrar apenas ultimas linhas (resumo)
        output_lines = (result.stdout or "").strip().split("\n")
        summary = "\n".join(output_lines[-8:]) if len(output_lines) > 8 else result.stdout

        if result.returncode == 0:
            print(
                f"Hook: testes passaram apos editar {os.path.basename(file_path)}",
                file=sys.stderr,
            )
        else:
            print(
                f"Hook: TESTES FALHARAM apos editar {os.path.basename(file_path)}\n"
                f"{summary[:500]}",
                file=sys.stderr,
            )

    except subprocess.TimeoutExpired:
        print("Hook: timeout ao rodar testes (>45s)", file=sys.stderr)
    except Exception as e:
        print(f"Hook: erro inesperado: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
