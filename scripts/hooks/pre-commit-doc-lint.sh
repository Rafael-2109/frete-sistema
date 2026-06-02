#!/usr/bin/env bash
# pre-commit hook: bloqueia commit que ADICIONA doc gerenciado nao-conforme (PAD-A).
# Modo added-only: NAO trava edicao de doc legado (migracao gradual Ondas 1-4).
# Bypass emergencial: git commit --no-verify
set -e

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

python3 scripts/audits/doc_audit.py --enforce-added
