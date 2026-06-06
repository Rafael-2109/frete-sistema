#!/usr/bin/env bash
# pre-commit hook: GATILHO DE DRIFT das stats dos CLAUDE.md de modulo.
# Roda --check-drift --staged: checa SO os modulos cujos .py o commit toca. Bloqueia se
# o tamanho REAL afastou-se do baseline alem do limite (LOC +-15% / arquivos +-5 / tpl +-5)
# -> forca atualizar o cabecalho "~XK LOC, N arquivos" do CLAUDE.md afetado + re-armar baseline.
# No-op se o commit nao toca .py de modulo com CLAUDE.md, ou se o baseline ainda nao existe.
# Bypass emergencial: git commit --no-verify
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Script ausente nesta worktree -> no-op (preserva worktrees sem PAD-A/auditoria).
[ -f scripts/audits/claude_md_stats_audit.py ] || exit 0

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python3 scripts/audits/claude_md_stats_audit.py --check-drift --staged
