#!/usr/bin/env python3
"""
Hook PostToolUse: Lembrete de Sincronizar References

Detecta edicoes em references criticos e imprime lembrete de quais
outros arquivos devem ser verificados para manter consistencia.

Nao bloqueia (exit 0 sempre). Apenas imprime aviso em stderr.
"""

import json
import sys

# Mapeamento: arquivo editado -> arquivos que dependem dele
SYNC_MAP = {
    "REGRAS_P1_P7.md": [
        "app/agente/prompts/system_prompt.md",
        ".claude/agents/analista-carteira.md",
    ],
    "REGRAS_CARTEIRA_SEPARACAO.md": [
        ".claude/skills/gerindo-expedicao/SKILL.md",
    ],
    "REGRAS_MODELOS.md": [
        ".claude/skills/gerindo-expedicao/SKILL.md",
        ".claude/skills/monitorando-entregas/SKILL.md",
    ],
    "REGRAS_NEGOCIO.md": [
        "app/agente/prompts/system_prompt.md",
    ],
    "INFRAESTRUTURA.md": [
        ".claude/settings.local.json",
    ],
    "ROUTING_SKILLS.md": [
        "CLAUDE.md",
    ],
    "FRETE_REAL_VS_TEORICO.md": [
        ".claude/skills/cotando-frete/SKILL.md",
    ],
}


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Detecta Write ou Edit em references
        if tool_name not in ("Write", "Edit"):
            return

        file_path = tool_input.get("file_path", "")

        # Verifica se algum reference critico foi editado
        for ref_file, dependents in SYNC_MAP.items():
            if file_path.endswith(ref_file):
                deps_list = "\n".join(f"    - {d}" for d in dependents)
                print(
                    "\n"
                    "================================================\n"
                    "  REFERENCE CRITICO EDITADO — Verificar dependentes\n"
                    "================================================\n"
                    f"  Editado: {ref_file}\n"
                    "\n"
                    "  Verificar tambem:\n"
                    f"{deps_list}\n"
                    "================================================\n",
                    file=sys.stderr,
                )
                return  # Apenas um match por arquivo

    except Exception:
        pass  # Hook nao deve bloquear nunca


if __name__ == "__main__":
    main()
