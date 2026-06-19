"""Testes do status de portaria AGREGADO por embarque (considera os 2 CDs).

Espelha o padrao puro de tests/fretes/test_frete_ultima_saida.py (SimpleNamespace).
"""
from datetime import date
from types import SimpleNamespace

from app.utils.local_cd import (
    LOCAL_CD_VICTORIO_MARCHEZINE as VM,
    LOCAL_CD_TENENTE_MARQUES as TM,
    status_portaria_agregado,
)


def _item(local_cd, status='ativo'):
    return SimpleNamespace(local_cd=local_cd, status=status)


def _reg(local_cd, status, data_saida=None):
    return SimpleNamespace(local_cd=local_cd, status=status, data_saida=data_saida)


def _emb(itens, registros):
    return SimpleNamespace(itens=itens, registros_portaria=registros)


def test_sem_registro():
    assert status_portaria_agregado(_emb([_item(VM)], [])) == 'SEM_REGISTRO'


def test_embarque_none():
    assert status_portaria_agregado(None) == 'SEM_REGISTRO'


def test_um_cd_saiu():
    emb = _emb([_item(VM)], [_reg(VM, 'SAIU', date(2026, 1, 10))])
    assert status_portaria_agregado(emb) == 'SAIU'


def test_um_cd_dentro():
    emb = _emb([_item(VM)], [_reg(VM, 'DENTRO')])
    assert status_portaria_agregado(emb) == 'DENTRO'


def test_misto_parcial_vm_saiu_tm_dentro():
    """O caso critico: VM saiu, TM ainda dentro -> PARCIAL (nao 'SAIU')."""
    emb = _emb(
        [_item(VM), _item(TM)],
        [_reg(VM, 'SAIU', date(2026, 1, 10)), _reg(TM, 'DENTRO')],
    )
    assert status_portaria_agregado(emb) == 'PARCIAL'


def test_misto_parcial_vm_saiu_tm_sem_registro():
    """VM saiu, TM ainda nem tem registro -> PARCIAL (falta TM)."""
    emb = _emb([_item(VM), _item(TM)], [_reg(VM, 'SAIU', date(2026, 1, 10))])
    assert status_portaria_agregado(emb) == 'PARCIAL'


def test_misto_completo_ambos_sairam():
    emb = _emb(
        [_item(VM), _item(TM)],
        [_reg(VM, 'SAIU', date(2026, 1, 10)), _reg(TM, 'SAIU', date(2026, 1, 11))],
    )
    assert status_portaria_agregado(emb) == 'SAIU'


def test_misto_nenhum_saiu_pega_mais_avancado():
    """Misto VM dentro + TM aguardando, nenhum saiu -> DENTRO (mais avancado)."""
    emb = _emb([_item(VM), _item(TM)], [_reg(VM, 'DENTRO'), _reg(TM, 'AGUARDANDO')])
    assert status_portaria_agregado(emb) == 'DENTRO'
