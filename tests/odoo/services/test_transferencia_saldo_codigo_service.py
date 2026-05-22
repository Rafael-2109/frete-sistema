"""Tests para TransferenciaSaldoCodigoService.

Cenarios:
- resolver_produto: ok / inexistente / ambiguo
- listar_lotes_cd_estoque: qtd/reservado/disponivel/migracao, filtro company/loc
- descobrir_destinos: bidirecional / vazio
- transferir: feliz / par invalido / qty invalida / reducao falha / compensacao
- _registrar_movimentacao_local: SAIDA + ENTRADA AJUSTE/MANUAL

Mock puro do Odoo + dependencias injetadas (padrao
tests/odoo/services/test_stock_internal_transfer_service.py).
"""
from unittest.mock import MagicMock, patch

import pytest

from app.odoo.services.transferencia_saldo_codigo_service import (
    TransferenciaSaldoCodigoService,
)


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def adj_mock():
    return MagicMock()


@pytest.fixture
def lot_mock():
    return MagicMock()


@pytest.fixture
def service(odoo_mock, adj_mock, lot_mock):
    return TransferenciaSaldoCodigoService(
        odoo=odoo_mock, adjustment_svc=adj_mock, lot_svc=lot_mock)


def test_resolver_produto_ok(service, odoo_mock):
    odoo_mock.search_read.return_value = [{
        'id': 27749, 'default_code': '4729198', 'name': 'AZEITE',
        'active': True, 'tracking': 'lot',
        'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True,
    }]
    info = service.resolver_produto('4729198')
    assert info['product_id'] == 27749
    assert info['uom'] == 'CAIXAS'
    assert info['use_expiration_date'] is True
    assert info['tracking'] == 'lot'


def test_resolver_produto_inexistente(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    with pytest.raises(ValueError, match='nao encontrado'):
        service.resolver_produto('999999')


def test_resolver_produto_ambiguo(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 1, 'default_code': '4729198', 'name': 'A', 'active': True,
         'tracking': 'lot', 'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True},
        {'id': 2, 'default_code': '4729198', 'name': 'B', 'active': True,
         'tracking': 'lot', 'uom_id': [12, 'CAIXAS'], 'use_expiration_date': True},
    ]
    with pytest.raises(ValueError, match='ambiguo'):
        service.resolver_produto('4729198')
