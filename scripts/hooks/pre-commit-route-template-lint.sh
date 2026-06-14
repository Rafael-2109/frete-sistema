#!/usr/bin/env bash
# pre-commit hook (B2): bloqueia commit que introduz render_template -> template
# inexistente. Baseline (scripts/audits/route_template_baseline.json) congela rotas
# legadas ja quebradas; so achado NOVO em .py staged bloqueia.
# Bypass emergencial: git commit --no-verify
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python3 scripts/audits/route_template_audit.py --staged
