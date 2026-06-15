"""Fixtures compartilhadas dos testes de custeio."""
import pytest

from app import db as _db


@pytest.fixture(autouse=True)
def _cleanup_custeio_residuo(db):  # noqa: ARG001 (db forca o fixture global)
    """Remove residuo de custo_considerado de testes antes de cada execucao.

    O ServicoCusteio.alterar_tipo_custo faz db.session.commit() diretamente
    (custeio_service.py:848,864), escapando o nested transaction do fixture
    `db`. Sem este cleanup, registros com cod_produto 'TEST_C2_*' persistem
    entre runs e colidem na UniqueConstraint uq_custo_considerado_versao
    (cod_produto, versao) — causa raiz de ERROR ambiental reincidente.
    """
    _db.session.execute(_db.text(
        "DELETE FROM custo_considerado WHERE cod_produto LIKE 'TEST_C2_%'"
    ))
    _db.session.commit()
    yield
    _db.session.rollback()
