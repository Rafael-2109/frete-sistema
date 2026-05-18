#!/usr/bin/env python3
"""Migration 31 — Adiciona CHASSI_FATURADO_SEM_RECIBO ao CHECK constraint.

Idempotente. Roda em build.sh apos migration 30.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL = """
ALTER TABLE assai_divergencia
    DROP CONSTRAINT IF EXISTS ck_assai_divergencia_tipo;

ALTER TABLE assai_divergencia
    ADD CONSTRAINT ck_assai_divergencia_tipo
    CHECK (tipo IN (
        'NF_CHASSI_FORA_CARREGAMENTO',
        'CARREGAMENTO_CHASSI_FORA_NF',
        'CHASSI_NAO_CADASTRADO',
        'CHASSI_OUTRA_LOJA',
        'LOJA_DIVERGENTE',
        'VALOR_DIVERGENTE',
        'MODELO_DIVERGENTE',
        'CHASSI_SEM_SEPARACAO',
        'CHASSI_FATURADO_SEM_RECIBO'
    ));
"""


def main():
    app = create_app()
    with app.app_context():
        print('Migration 31: adicionando CHASSI_FATURADO_SEM_RECIBO ao CHECK constraint...')
        db.session.execute(text(SQL))
        db.session.commit()
        print('✅ Migration 31 aplicada')


if __name__ == '__main__':
    main()
