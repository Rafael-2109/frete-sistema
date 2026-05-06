#!/usr/bin/env bash
# pre-commit hook: bloqueia commit com violacoes de UI policy em arquivos NOVOS
# ou linhas TOCADAS no diff vs HEAD.
#
# Instalacao:
#   ln -sf ../../scripts/hooks/pre-commit-ui-lint.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Bypass (apenas em emergencia):
#   git commit --no-verify

set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# Ativar venv se existir
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Compara contra HEAD (linhas modificadas + arquivos novos staged)
# Para staged-only: --base-ref HEAD --cached precisaria mais lógica. Usamos
# HEAD que captura unstaged + staged (suficiente para pre-commit).

python scripts/audits/ui_policy_lint.py --enforce-new --base-ref HEAD || {
    echo ""
    echo "❌ UI policy lint failed. Veja regras em:"
    echo "   .claude/references/design/GUIA_COMPONENTES_UI.md (secao 6, V15-V17)"
    echo ""
    echo "Para bypass de emergencia: git commit --no-verify"
    exit 1
}

exit 0
