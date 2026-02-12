#!/usr/bin/env python3
"""
Hook PostToolUse: Proibir datetime.now() em codigo Python

Detecta Write/Edit em arquivos .py que introduzem datetime.now().
Emite aviso em stderr (nao bloqueia).

Excecoes:
- app/utils/timezone.py (funcoes core)
- Patterns de TIMING (inicio = datetime.now(), etc.)
- datetime.now() com argumentos de TZ: datetime.now(BRASIL_TZ), etc.
"""

import json
import re
import sys


TIMING_PATTERNS = [
    r"^\s*(inicio|fim|start|end|t[01]|tempo_inicio|tempo_fim|start_time|end_time|hora_inicio|hora_fim)\w*\s*=\s*datetime\.now\(\)",
    r"\(datetime\.now\(\)\s*-\s*(inicio|start|t0|tempo_inicio|hora_inicio)",
    r"(duracao|elapsed|tempo_decorrido)\s*=.*datetime\.now\(\)",
    r"total_seconds\(\)",
]


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
        if not file_path.endswith(".py"):
            return

        # Excecoes
        if file_path.endswith("timezone.py"):
            return
        if file_path.endswith("audit_datetime_now.py"):
            return

        # Para Edit, verificar o new_string
        if tool_name == "Edit":
            new_string = tool_input.get("new_string", "")
            check_text(new_string, file_path)
        elif tool_name == "Write":
            content = tool_input.get("content", "")
            check_text(content, file_path)

    except Exception:
        pass  # Hook nao deve bloquear nunca


def check_text(text: str, file_path: str):
    """Verifica se o texto contem datetime.now() proibido."""
    violations = []

    for i, line in enumerate(text.splitlines(), 1):
        if "datetime.now()" not in line:
            continue

        # Ignorar datetime.now() com argumentos
        if re.search(r"datetime\.now\([^)]+\)", line) and "datetime.now()" not in line:
            continue

        # Ignorar patterns de timing
        is_timing = False
        for pattern in TIMING_PATTERNS:
            if re.search(pattern, line):
                is_timing = True
                break

        if not is_timing:
            violations.append((i, line.strip()))

    if violations:
        msg = (
            "\n"
            "==================================================\n"
            "  PROIBIDO: datetime.now() detectado!\n"
            "==================================================\n"
            f"  Arquivo: {file_path}\n"
        )
        for lineno, line_text in violations:
            msg += f"  Linha {lineno}: {line_text}\n"
        msg += (
            "\n"
            "  Use agora_utc_naive() (horario Brasil)\n"
            "  ou agora_utc() (para queries Odoo write_date)\n"
            "  from app.utils.timezone import agora_utc_naive\n"
            "==================================================\n"
        )
        print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
