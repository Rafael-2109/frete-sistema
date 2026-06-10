#!/usr/bin/env bash
# pre-commit hook (FASE 5 governanca + F1.3 PAD-CTX):
# 1. GATILHO DE PODA: se o commit toca um dos 3 arquivos do system prompt estatico,
#    roda --check-delta (bloqueia se o prompt CRESCEU vs baseline -> forca decisao
#    consciente principio-vs-procedimento). Reducao (poda) nunca bloqueia.
# 2. CONSISTENCIA DE SUBAGENTES/SKILLS: se o commit toca .claude/agents/, as
#    skills_whitelist, o CLAUDE.md raiz ou o system_prompt, roda --check-consistency
#    (bloqueia divergencia entre as 3 projecoes de subagentes e skill orfa na
#    deny-list). Padrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md.
# 3. ORCAMENTO DO LISTING (F2.5): SKILL.md/whitelist tocados -> skills_listing_audit.
# 4. ORCAMENTO DO HOOK (F6): pipeline de injecao tocado -> test_hook_budget.py.
# Cobertura dos 5 checks PAD-CTX: (1)+(4) via --check-consistency; (2) listing;
# (3) hook budget; (5) checklist de admissao = doc (R-EXEC-5 no CLAUDE.md do agente).
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

# F6 PAD-CTX: orcamento do hook dinamico por bloco (check 3 do padrao).
# Tocar o pipeline de injecao exige a suite test_hook_budget.py verde
# (ordem-alvo, caps Tier2/tier1/user_rules, overflow, teto 15KB).
TOCOU_HOOK=0
if echo "$STAGED" | grep -qE '^app/agente/sdk/(memory_injection(_rules)?|hooks)\.py$'; then
    TOCOU_HOOK=1
fi

# F2.5 PAD-CTX: orcamento do listing de skills (soma das descriptions <= 8K).
TOCOU_LISTING=0
if echo "$STAGED" | grep -qE '^(\.claude/skills/[^/]+/SKILL\.md|app/agente/config/skills_whitelist\.py)$'; then
    TOCOU_LISTING=1
fi

if [ "$TOCOU_PROMPT" -eq 0 ] && [ "$TOCOU_CONSISTENCIA" -eq 0 ] && [ "$TOCOU_LISTING" -eq 0 ] && [ "$TOCOU_HOOK" -eq 0 ]; then
    exit 0  # commit nao toca prompt, projecoes, listing nem hook -> nada a checar
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

if [ "$TOCOU_LISTING" -eq 1 ]; then
    python3 scripts/audits/skills_listing_audit.py --check
fi

if [ "$TOCOU_HOOK" -eq 1 ]; then
    python3 -m pytest tests/agente/sdk/test_hook_budget.py -q --tb=line -p no:cacheprovider
fi
