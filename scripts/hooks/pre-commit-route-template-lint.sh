#!/usr/bin/env bash
# pre-commit hook (B2): bloqueia commit que introduz render_template -> template
# inexistente. Baseline (scripts/audits/route_template_baseline.json) congela rotas
# legadas ja quebradas; so achado NOVO em .py staged bloqueia.
# Bypass emergencial: git commit --no-verify
#
# NOTA (WSL2): este audit e' ESTATICO/leve (regex + rglob; NAO importa `app` nem
# libs nativas — verificado: o import carrega 0 modulos pesados e roda 5/5 EXIT=0).
# Um Segmentation fault (exit 139) aqui e' crash PONTUAL de ambiente, NAO defeito
# do audit; mas com `set -e` aborta o commit sem violacao real. Se acontecer:
# RE-TENTE o commit (nao se reproduz); --no-verify so' em ultimo caso e quando o
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
