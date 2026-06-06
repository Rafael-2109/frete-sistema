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


def _info(pid, cod, name, use_exp=True):
    return {'product_id': pid, 'cod': cod, 'name': name,
            'tracking': 'lot', 'uom': 'CAIXAS', 'use_expiration_date': use_exp}


def test_transferir_feliz(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},
        {'status': 'EXECUTADO', 'qty_antes': 2.0, 'qty_apos': 7.0},
    ]
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'EXECUTADO'
    assert r['origem_apos'] == 285.0 and r['destino_apos'] == 7.0
    # validade do origem replicada ao criar lote destino
    assert lot_mock.criar_se_nao_existe.call_args.kwargs['expiration_date'] == '2028-05-15 00:00:00'
    service._registrar_movimentacao_local.assert_called_once()


def test_transferir_par_invalido(service):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '999', 'nome': 'X'}])
    with pytest.raises(ValueError, match='nao e par'):
        service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')


def test_transferir_qty_invalida(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir('4729198', '4759198', '135/26', 0, 'rafael')


def test_transferir_reducao_falha_nao_aumenta(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    adj_mock.ajustar_quant.return_value = {'status': 'FALHA_RESERVADO', 'erro': 'reservado'}
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'FALHA_REDUCAO'
    assert adj_mock.ajustar_quant.call_count == 1  # não tentou aumentar


def test_transferir_aumento_falha_compensa(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},  # reduz ok
        {'status': 'FALHA_ODOO', 'erro': 'boom'},                        # aumento falha
        {'status': 'EXECUTADO', 'qty_antes': 285.0, 'qty_apos': 290.0},  # compensa
    ]
    r = service.transferir('4729198', '4759198', '135/26', 5.0, 'rafael')
    assert r['status'] == 'FALHA_AUMENTO_COMPENSADO'
    assert adj_mock.ajustar_quant.call_count == 3  # reduz + aumenta + compensa


def test_registrar_movimentacao_local(service, app):
    criados = []

    class FakeMov:
        def __init__(self):
            criados.append(self)

    fake_session = MagicMock()
    with patch('app.estoque.models.MovimentacaoEstoque', FakeMov), \
         patch('app.odoo.services.transferencia_saldo_codigo_service._get_db_session',
               return_value=fake_session):
        service._registrar_movimentacao_local(
            '4729198', 'AZEITE', '4759198', 'SOJA', '135/26', 5.0, 'rafael')

    assert len(criados) == 2
    saida, entrada = criados
    assert saida.tipo_movimentacao == 'SAIDA' and saida.cod_produto == '4729198'
    assert entrada.tipo_movimentacao == 'ENTRADA' and entrada.cod_produto == '4759198'
    assert saida.local_movimentacao == 'AJUSTE' and saida.tipo_origem == 'MANUAL'
    assert saida.lote_nome == '135/26'
    # Convenção do sistema: saldo = SUM(qtd_movimentacao) puro → SAIDA negativa, ENTRADA positiva
    assert saida.qtd_movimentacao == -5.0
    assert entrada.qtd_movimentacao == 5.0
    assert saida.criado_por == 'rafael'
    assert fake_session.add.call_count == 2
    fake_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# transferir_v2 — genérico (empresa/local/lote parametrizáveis) + dry-run
# ---------------------------------------------------------------------------

def test_transferir_v2_feliz_lf_locais_distintos(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    lot_mock.criar_se_nao_existe.return_value = (58503, True)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 290.0, 'qty_apos': 285.0},
        {'status': 'EXECUTADO', 'qty_antes': 0.0, 'qty_apos': 5.0},
    ]
    r = service.transferir_v2(
        company_id=5, cod_origem='4729198', location_id_origem=42,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=53,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['origem_apos'] == 285.0 and r['destino_apos'] == 5.0
    assert r['lote_criado'] is True
    assert r['aviso_par'] is False
    # company/local propagados ao ajustar_quant
    red_kwargs = adj_mock.ajustar_quant.call_args_list[0].kwargs
    assert red_kwargs['company_id'] == 5 and red_kwargs['location_id'] == 42
    aum_kwargs = adj_mock.ajustar_quant.call_args_list[1].kwargs
    assert aum_kwargs['company_id'] == 5 and aum_kwargs['location_id'] == 53
    service._registrar_movimentacao_local.assert_called_once()


def test_transferir_v2_aviso_par_nao_bloqueia(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[])  # nenhum par cadastrado
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '9999', 'OUTRO')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    lot_mock.criar_se_nao_existe.return_value = (58503, False)
    adj_mock.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'qty_antes': 100.0, 'qty_apos': 90.0},
        {'status': 'EXECUTADO', 'qty_antes': 0.0, 'qty_apos': 10.0},
    ]
    r = service.transferir_v2(
        company_id=1, cod_origem='4729198', location_id_origem=8,
        lote_nome_origem='135/26', cod_destino='9999', location_id_destino=8,
        lote_nome_destino='135/26', qty=10.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'EXECUTADO'
    assert r['aviso_par'] is True  # avisou, mas executou


def test_transferir_v2_dry_run_nao_escreve_nem_cria_lote(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    service._registrar_movimentacao_local = MagicMock()
    lot_mock.buscar_por_nome.side_effect = [56426, None]  # origem existe, destino NÃO
    odoo_mock.read.return_value = [{'expiration_date': '2028-05-15 00:00:00'}]
    adj_mock.ajustar_quant.return_value = {
        'status': 'DRY_RUN_OK', 'qty_antes': 290.0, 'qty_apos': 285.0}
    r = service.transferir_v2(
        company_id=5, cod_origem='4729198', location_id_origem=42,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=42,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'
    assert r['origem_apos'] == 285.0
    assert r['destino_antes'] == 0.0 and r['destino_apos'] == 5.0
    assert r['lote_criado'] is True  # será criado no executar
    lot_mock.criar_se_nao_existe.assert_not_called()   # NÃO cria em dry-run
    service._registrar_movimentacao_local.assert_not_called()  # NÃO espelha em dry-run
    # só 1 ajustar_quant (reduz origem dry); destino é preview manual (lote novo)
    assert adj_mock.ajustar_quant.call_count == 1


def test_transferir_v2_reducao_falha(service, odoo_mock, adj_mock, lot_mock):
    service.descobrir_destinos = MagicMock(return_value=[{'codigo': '4759198', 'nome': 'SOJA'}])
    service.resolver_produto = MagicMock(side_effect=[
        _info(27749, '4729198', 'AZEITE'), _info(27735, '4759198', 'SOJA')])
    lot_mock.buscar_por_nome.return_value = 56426
    odoo_mock.read.return_value = [{'expiration_date': False}]
    adj_mock.ajustar_quant.return_value = {'status': 'FALHA_RESERVADO', 'erro': 'reservado'}
    r = service.transferir_v2(
        company_id=1, cod_origem='4729198', location_id_origem=8,
        lote_nome_origem='135/26', cod_destino='4759198', location_id_destino=8,
        lote_nome_destino='135/26', qty=5.0, usuario='rafael', dry_run=False)
    assert r['status'] == 'FALHA_REDUCAO'
    assert adj_mock.ajustar_quant.call_count == 1
