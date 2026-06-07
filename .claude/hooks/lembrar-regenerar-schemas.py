#!/usr/bin/env python3
"""
Hook PostToolUse: Auto-regenerar Schemas apos editar modelos.

Detecta edicoes em models.py, models/<x>.py e models_<x>.py e EXECUTA
o generate_schemas.py (agora idempotente: so grava o que mudou, sem poluir
o git). NUNCA apaga schemas orfaos automaticamente — apenas loga
(remocao exige --prune-orphans manual; ver generate_schemas.py).

Exit 0 sempre — falha na regeneracao nao deve bloquear o fluxo.
"""

import json
import os
import subprocess
import sys


def _is_model_file(file_path: str) -> bool:
    """True se `file_path` for um arquivo de modelo SQLAlchemy.

    Medido empiricamente sobre os 122 arquivos com __tablename__ em app/:
    cobre models.py, models_*.py, *_models.py (email_models.py, frota_models.py)
    e o diretorio models/. Tambem cobre model.py, model_*.py e o diretorio model/
    (singular). Ampla de proposito: como o gerador agora e idempotente, um disparo
    extra (falso-positivo) e inocuo (0 escritos, git limpo); perder um modelo real,
    nao. Exclui test_*.py para reduzir ruido.
    """
    path_l = file_path.lower()
    base = os.path.basename(path_l)
    return (
        path_l.endswith(".py")
        and not base.startswith("test_")
        and ("model" in base or "/models/" in path_l or "/model/" in path_l)
    )


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
        if not _is_model_file(file_path):
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
                f"Hook: schemas regenerados (idempotente — so grava o que mudou) "
                f"apos editar {os.path.basename(file_path)}",
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
