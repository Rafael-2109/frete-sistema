#!/usr/bin/env bash
# pre-commit hook (FASE 5 governanca + F1.3 PAD-CTX):
# 1. GATILHO DE PODA: se o commit toca um dos 3 arquivos do system prompt estatico,
#    roda --check-delta (bloqueia se o prompt CRESCEU vs baseline -> forca decisao
#    consciente principio-vs-procedimento). Reducao (poda) nunca bloqueia.
# 2. CONSISTENCIA DE SUBAGENTES/SKILLS: se o commit toca .claude/agents/, as
#    skills_whitelist, o CLAUDE.md raiz ou o system_prompt, roda --check-consistency
#    (bloqueia divergencia entre as 3 projecoes de subagentes e skill orfa na
#    deny-list). Padrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md.
# Bypass emergencial: git commit --no-verify
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Os 3 arquivos concatenados em _build_full_system_prompt() (client.py).
VIGIADOS="app/agente/prompts/preset_operacional.md app/agente/prompts/system_prompt.md app/agente/config/empresa_briefing.md"

STAGED="$(git diff --cached --name-only)"

TOCOU_PROMPT=0
for f in $VIGIADOS; do
    if echo "$STAGED" | grep -qxF "$f"; then
        TOCOU_PROMPT=1
        break
    fi
done

TOCOU_CONSISTENCIA=0
if echo "$STAGED" | grep -qE '^(\.claude/agents/.*\.md|app/agente/config/skills_whitelist\.py|app/agente_lojas/config/skills_whitelist\.py|CLAUDE\.md|app/agente/prompts/system_prompt\.md)$'; then
    TOCOU_CONSISTENCIA=1
fi

if [ "$TOCOU_PROMPT" -eq 0 ] && [ "$TOCOU_CONSISTENCIA" -eq 0 ]; then
    exit 0  # commit nao toca prompt nem projecoes de subagentes -> nada a checar
fi

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

if [ "$TOCOU_PROMPT" -eq 1 ]; then
    python3 scripts/audits/prompt_size_audit.py --check-delta
fi

if [ "$TOCOU_CONSISTENCIA" -eq 1 ]; then
    python3 scripts/audits/prompt_size_audit.py --check-consistency
fi
