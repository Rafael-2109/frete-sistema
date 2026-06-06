#!/usr/bin/env bash
# pre-commit hook (FASE 5 governanca): GATILHO DE PODA do prompt do Agente Web.
# Dispara SO se o commit toca um dos 3 arquivos do system prompt estatico; entao
# roda --check-delta (bloqueia se o prompt CRESCEU vs baseline -> forca decisao
# consciente principio-vs-procedimento). Reducao (poda) nunca bloqueia.
# Bypass emergencial: git commit --no-verify
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Os 3 arquivos concatenados em _build_full_system_prompt() (client.py).
VIGIADOS="app/agente/prompts/preset_operacional.md app/agente/prompts/system_prompt.md app/agente/config/empresa_briefing.md"

STAGED="$(git diff --cached --name-only)"
TOCOU=0
for f in $VIGIADOS; do
    if echo "$STAGED" | grep -qxF "$f"; then
        TOCOU=1
        break
    fi
done

if [ "$TOCOU" -eq 0 ]; then
    exit 0  # commit nao toca o prompt -> nada a checar
fi

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python3 scripts/audits/prompt_size_audit.py --check-delta
