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


def test_listar_lotes_cd_estoque(service, odoo_mock):
    service.resolver_produto = MagicMock(return_value={'product_id': 27749})
    odoo_mock.search_read.return_value = [
        {'id': 1, 'lot_id': [56426, '135/26'], 'quantity': 290.0, 'reserved_quantity': 0.0},
        {'id': 2, 'lot_id': [30856, 'MIGRAÇÃO'], 'quantity': 100.0, 'reserved_quantity': 40.0},
        {'id': 3, 'lot_id': False, 'quantity': 5.0, 'reserved_quantity': 0.0},
    ]
    lotes = service.listar_lotes_cd_estoque('4729198')
    assert lotes[0] == {'lote_nome': '135/26', 'lot_id': 56426, 'quantidade': 290.0,
                        'reservado': 0.0, 'disponivel': 290.0, 'is_migracao': False}
    assert lotes[1]['is_migracao'] is True
    assert lotes[1]['disponivel'] == 60.0
    assert lotes[2]['lote_nome'] is None and lotes[2]['lot_id'] is None
    # domain filtra company 4 e loc 32
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['company_id', '=', 4] in domain
    assert ['location_id', '=', 32] in domain


# fixture `app` (conftest, session scope) garante que app.estoque.models é importável
def test_descobrir_destinos_bidirecional(service, app):
    service.resolver_produto = MagicMock(side_effect=[
        {'product_id': 27735, 'name': 'SOJA'},
    ])
    with patch('app.estoque.models.UnificacaoCodigos.get_todos_codigos_relacionados',
               return_value=['4729198', '4759198']):
        destinos = service.descobrir_destinos('4729198')
    assert destinos == [{'codigo': '4759198', 'nome': 'SOJA'}]


def test_descobrir_destinos_vazio(service, app):
    with patch('app.estoque.models.UnificacaoCodigos.get_todos_codigos_relacionados',
               return_value=['4729198']):
        assert service.descobrir_destinos('4729198') == []
