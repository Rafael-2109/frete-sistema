"""Fase 3 (Task 6): helpers _aplicar_header/_aplicar_pagamentos sao flush-only (sem commit)."""
import inspect
from app.hora.services import venda_service


def test_helpers_existem_e_nao_comitam(db):
    for nome in ('_aplicar_header', '_aplicar_pagamentos'):
        fn = getattr(venda_service, nome, None)
        assert fn is not None, f'helper {nome} ausente'
        src = inspect.getsource(fn)
        assert 'commit()' not in src, f'{nome} nao pode comitar (flush-only)'
