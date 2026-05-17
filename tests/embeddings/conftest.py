"""Fixtures para eval de embeddings.

Skips automaticos:
- Sem `VOYAGE_API_KEY` configurada -> testes que chamam Voyage sao skipped
- Sem conexao ao banco com tabela populada -> abort com instrucao
"""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Marca todos os testes do diretorio como `voyage_api` quando aplicavel."""
    if not os.environ.get("VOYAGE_API_KEY"):
        skip_voyage = pytest.mark.skip(
            reason="VOYAGE_API_KEY nao configurada — eval offline"
        )
        for item in items:
            if "voyage_api" in item.keywords:
                item.add_marker(skip_voyage)


@pytest.fixture(scope="session")
def app():
    """Flask app + DB session para queries em sped_ecd_rule_embeddings."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from app import create_app

    app = create_app()
    with app.app_context():
        yield app


@pytest.fixture(scope="session")
def chunk_count_baseline(app):
    """Conta chunks indexados; aborta se tabela estiver vazia."""
    from app import db
    from sqlalchemy import text

    n = db.session.execute(
        text("SELECT COUNT(*) FROM sped_ecd_rule_embeddings")
    ).scalar()
    if not n:
        pytest.skip(
            "Tabela sped_ecd_rule_embeddings vazia. "
            "Rode: python -m app.embeddings.indexers.sped_ecd_rules_indexer"
        )
    return n
