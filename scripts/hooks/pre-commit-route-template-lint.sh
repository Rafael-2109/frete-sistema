#!/usr/bin/env bash
# pre-commit hook (B2): bloqueia commit que introduz render_template -> template
# inexistente. Baseline (scripts/audits/route_template_baseline.json) congela rotas
# legadas ja quebradas; so achado NOVO em .py staged bloqueia.
# Bypass emergencial: git commit --no-verify
#
# NOTA (WSL2): route_template_audit.py importa `app` e carrega libs nativas
# (numpy/pandas/lxml/rapidfuzz). Nesse ambiente isso pode dar Segmentation fault
# (exit 139) INTERMITENTE que, com `set -e`, aborta o commit sem violacao real.
# Se acontecer: RE-TENTE o commit (e' intermitente); use --no-verify SO quando o
# commit NAO tocar rota/template, validando depois com:
#   python3 scripts/audits/route_template_audit.py
# Detalhes: .claude/references/REGRAS_DEV_LOCAL.md (REGRAS DEV ADICIONAIS, item 6).
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python3 scripts/audits/route_template_audit.py --staged
