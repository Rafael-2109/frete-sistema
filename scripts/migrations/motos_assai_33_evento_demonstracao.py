#!/usr/bin/env python3
"""Migration 33 — Adiciona DEMONSTRACAO ao CHECK constraint de assai_moto_evento.tipo.

Origem: skill corrigindo-dados-assai (backfill manual) + IMP-2026-06-19-001 item 3
(3 motos em DEMONSTRACAO na planilha da Rayssa). DEMONSTRACAO conta como
EVENTOS_FORA_ESTOQUE (nao e estoque disponivel). Idempotente; roda em build.sh
apos migration 32.
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
ALTER TABLE assai_moto_evento
    DROP CONSTRAINT IF EXISTS ck_assai_moto_evento_tipo;

ALTER TABLE assai_moto_evento
    ADD CONSTRAINT ck_assai_moto_evento_tipo
    CHECK (tipo IN (
        'ESTOQUE', 'MONTADA', 'PENDENTE', 'PENDENCIA_RESOLVIDA',
        'DISPONIVEL', 'REVERTIDA_PARA_MONTADA',
        'SEPARADA', 'CARREGADA', 'FATURADA', 'CANCELADA', 'MOTO_FALTANDO',
        'DEMONSTRACAO'
    ));
"""


def main():
    app = create_app()
    with app.app_context():
        print('Migration 33: adicionando DEMONSTRACAO ao CHECK constraint...')
        db.session.execute(text(SQL))
        db.session.commit()
        print('✅ Migration 33 aplicada')


if __name__ == '__main__':
    main()
