#!/usr/bin/env python3
"""Migration 32 — Adiciona coluna `import_resumo` (JSONB) em assai_pedido_venda.

Origem: IMP-2026-06-18-001. O parser determinístico perdia lojas no match
(zero-padding divergente) mas gravava parsing_confianca=1.00 — silent data loss.
`import_resumo` registra o balanço do import (lojas/itens extraídos vs gravados +
pulados) para exibição na tela, e marca edicao_manual quando há edição manual
(IMP-2026-06-18-003/-004).

Idempotente. NÃO consta no build.sh: aplicada MANUALMENTE em produção via
DATABASE_URL_PROD (2026-06-18) e no banco local via este script standalone.
Mantido como registro versionado do DDL.
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
ALTER TABLE assai_pedido_venda
    ADD COLUMN IF NOT EXISTS import_resumo JSONB;
"""


def main():
    app = create_app()
    with app.app_context():
        print('Migration 32: adicionando coluna import_resumo em assai_pedido_venda...')
        db.session.execute(text(SQL))
        db.session.commit()
        print('✅ Migration 32 aplicada')


if __name__ == '__main__':
    main()
