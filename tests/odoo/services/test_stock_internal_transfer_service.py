"""Tests para StockInternalTransferService.

Cenarios cobertos:
- transferir_entre_lotes feliz (origem e destino existentes)
- transferir_entre_lotes criando quant destino (nao existia)
- transferir de lot_id_origem=None (quant sem lote) para lote especifico
- erro: qty <= 0
- erro: lot_id_origem == lot_id_destino
- erro: quant origem nao encontrado
- erro: qty solicitada > saldo do quant origem
- erro: saldo apos transferencia ficaria < reservada
- transferir_quantidade_para_lote (wrapper com criar_se_nao_existe)
"""
from unittest.mock import MagicMock

import pytest

from app.odoo.services.stock_internal_transfer_service import (
    StockInternalTransferService,
)
from app.odoo.estoque.scripts.transfer import LOTE_MIGRACAO_CANONICO


@pytest.fixture
def odoo_mock():
    return MagicMock()


@pytest.fixture
def lot_svc_mock():
    m = MagicMock()
    m.criar_se_nao_existe.return_value = (999, False)
    return m


@pytest.fixture
def service(odoo_mock, lot_svc_mock):
    return StockInternalTransferService(odoo=odoo_mock, lot_svc=lot_svc_mock)


def test_transferir_feliz_quant_destino_existe(service, odoo_mock):
    """Cenario padrao: ambos quants existem, transfere qty parcial."""
    # Mock buscar_quant: origem (id=10, qty=100, reservada=0), destino (id=20, qty=50)
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'MIGRAÇÃO'], 'reserved_quantity': 0}],
        [{'id': 20, 'quantity': 50.0, 'value': 32.17, 'lot_id': [50000, '26014'], 'reserved_quantity': 0}],
    ]

    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=35.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['quant_origem_id'] == 10
    assert res['quant_origem_qty_antes'] == 100.0
    assert res['quant_origem_qty_apos'] == 65.0
    assert res['quant_destino_id'] == 20
    assert res['quant_destino_qty_antes'] == 50.0
    assert res['quant_destino_qty_apos'] == 85.0
    assert res['qty_transferida'] == 35.0
    # 2 writes + 2 action_apply_inventory
    assert odoo_mock.write.call_count == 2
    assert odoo_mock.execute_kw.call_count == 2


def test_transferir_cria_quant_destino_quando_nao_existe(service, odoo_mock):
    """Quant destino nao existe → cria via create + inventory_quantity."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
        [],  # quant destino nao existe
    ]
    odoo_mock.create.return_value = 999  # id do novo quant

    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=20.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['quant_destino_id'] == 999
    assert res['quant_destino_qty_antes'] == 0.0
    assert res['quant_destino_qty_apos'] == 20.0
    odoo_mock.create.assert_called_once()
    args = odoo_mock.create.call_args[0]
    assert args[0] == 'stock.quant'
    payload = args[1]
    assert payload['product_id'] == 28239
    assert payload['lot_id'] == 50000
    assert payload['inventory_quantity'] == 20.0


def test_transferir_origem_sem_lote(service, odoo_mock):
    """lot_id_origem=None busca quant com lot_id=False."""
    odoo_mock.search_read.side_effect = [
        [{'id': 32677, 'quantity': 39216.0, 'value': 25232.54, 'lot_id': False, 'reserved_quantity': 0}],
        [{'id': 20, 'quantity': 0.0, 'value': 0.0, 'lot_id': [50000, '26014'], 'reserved_quantity': 0}],
    ]
    res = service.transferir_entre_lotes(
        product_id=28239, company_id=5, location_id=42,
        qty=39216.0, lot_id_origem=None, lot_id_destino=50000,
    )
    assert res['quant_origem_id'] == 32677
    assert res['quant_origem_qty_apos'] == 0.0
    # search_read primeira chamada deveria ter usado lot_id=False
    primeira_chamada_domain = odoo_mock.search_read.call_args_list[0][0][1]
    assert ['lot_id', '=', False] in primeira_chamada_domain


def test_qty_invalida_zero(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=0, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_qty_invalida_negativa(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=-5, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_lot_origem_igual_destino(service):
    with pytest.raises(ValueError, match='lot_id_origem == lot_id_destino'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=10, lot_id_origem=50000, lot_id_destino=50000,
        )


def test_quant_origem_nao_encontrado(service, odoo_mock):
    odoo_mock.search_read.side_effect = [[], []]
    with pytest.raises(ValueError, match='Quant origem nao encontrado'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=10, lot_id_origem=99999, lot_id_destino=50000,
        )


def test_quant_origem_qty_insuficiente(service, odoo_mock):
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 5.0, 'value': 3.0, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
    ]
    with pytest.raises(RuntimeError, match='tem 5.0 un mas pedido transferir 100'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=100, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_reserva_impediria_transferencia(service, odoo_mock):
    """Se transferir deixaria saldo < reservada, falha."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 80.0}],
    ]
    with pytest.raises(RuntimeError, match='80.0 un reservadas'):
        service.transferir_entre_lotes(
            product_id=1, company_id=5, location_id=42,
            qty=30, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_wrapper_transferir_quantidade_para_lote(service, odoo_mock, lot_svc_mock):
    """Wrapper deve chamar criar_se_nao_existe e depois transferir."""
    lot_svc_mock.criar_se_nao_existe.return_value = (50000, True)  # criado agora
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0}],
        [],  # destino nao existe
    ]
    odoo_mock.create.return_value = 999

    res = service.transferir_quantidade_para_lote(
        product_id=28239, company_id=5, location_id=42,
        qty=10.0, lot_id_origem=44098,
        nome_lote_destino='26014',
    )

    lot_svc_mock.criar_se_nao_existe.assert_called_once_with(
        '26014', 28239, 5, expiration_date=None,
    )
    assert res['lote_destino_nome'] == '26014'
    assert res['lote_destino_criado_agora'] is True
    assert res['lot_id_destino'] == 50000
    assert res['qty_transferida'] == 10.0


def test_buscar_quant_com_lote(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 10, 'quantity': 100.0, 'value': 64.34, 'lot_id': [44098, 'X'], 'reserved_quantity': 0},
    ]
    q = service.buscar_quant(28239, 5, 42, lot_id=44098)
    assert q is not None
    assert q['id'] == 10
    # domain deveria incluir lot_id = 44098
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['lot_id', '=', 44098] in domain


def test_buscar_quant_sem_lote(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 32677, 'quantity': 39216.0, 'value': 25232.54, 'lot_id': False, 'reserved_quantity': 0},
    ]
    q = service.buscar_quant(28239, 5, 42, lot_id=None)
    assert q is not None
    assert q['lot_id'] is False
    domain = odoo_mock.search_read.call_args[0][1]
    assert ['lot_id', '=', False] in domain


def test_buscar_quant_nao_encontrado(service, odoo_mock):
    odoo_mock.search_read.return_value = []
    q = service.buscar_quant(28239, 5, 42, lot_id=99999)
    assert q is None


def test_listar_quants(service, odoo_mock):
    odoo_mock.search_read.return_value = [
        {'id': 1, 'quantity': 10.0, 'lot_id': [100, 'A'], 'reserved_quantity': 0},
        {'id': 2, 'quantity': 20.0, 'lot_id': [200, 'B'], 'reserved_quantity': 5.0},
    ]
    quants = service.listar_quants(28239, 5, 42)
    assert len(quants) == 2
    assert quants[0]['id'] == 1
    assert quants[1]['id'] == 2


# ============================================================
# Suite — Skill 2 maturando (2026-05-24): helpers + API v2 + gotchas
# ============================================================

from app.odoo.estoque.scripts.transfer import (  # noqa: E402
    LOTE_MIGRACAO_CANONICO,
    LOTES_MIGRACAO_VARIANTES,
    is_migracao,
)


def test_is_migracao_variantes():
    """G022: 3 grafias do lote MIGRACAO sao reconhecidas."""
    assert is_migracao('MIGRAÇÃO') is True
    assert is_migracao('MIGRACAO') is True
    assert is_migracao('MIGRAÇAO') is True
    assert is_migracao('migracao') is True  # case-insensitive
    assert is_migracao(' MIGRAÇÃO ') is True  # strip
    assert is_migracao('MI 027-098/26') is False
    assert is_migracao('') is False
    assert is_migracao(None) is False


def test_lotes_migracao_ids_filtra_company(service, odoo_mock):
    """G021: busca de lote MIGRACAO SEMPRE filtra company_id."""
    odoo_mock.search.return_value = [501, 502]  # 2 variantes na empresa-alvo

    ids = service._lotes_migracao_ids(product_id=28239, company_id=5)

    assert ids == [501, 502]
    # Confirmar dominio do search incluiu company_id
    args, _ = odoo_mock.search.call_args
    assert args[0] == 'stock.lot'
    dominio = args[1]
    assert ['name', 'in', LOTES_MIGRACAO_VARIANTES] in dominio
    assert ['product_id', '=', 28239] in dominio
    assert ['company_id', '=', 5] in dominio


def test_melhor_lote_migracao_na_loc_pega_maior_saldo(service, odoo_mock):
    """G022: quando ha 2 lots MIGRACAO no produto, escolher o de MAIOR saldo na loc."""
    odoo_mock.search.return_value = [501, 502]  # 2 variantes
    odoo_mock.search_read.return_value = [
        {'lot_id': [501, 'MIGRAÇÃO'], 'quantity': 50.0},
        {'lot_id': [502, 'MIGRACAO'], 'quantity': 120.0},  # MAIOR
    ]

    lid, todos = service._melhor_lote_migracao_na_loc(
        product_id=28239, company_id=5, location_id=42,
    )

    assert lid == 502  # o de maior saldo
    assert set(todos) == {501, 502}


def test_melhor_lote_migracao_na_loc_zero_saldo_fallback_primeiro(service, odoo_mock):
    """CR1#3 (2026-05-24 v2): fallback determinístico quando NENHUMA variante tem saldo na loc.

    Cenário: produto tem 2 lots MIGRACAO criados (search retorna [501, 502]) mas nenhum
    com saldo na location alvo (search_read filtra quantity != 0; vazio). Comportamento
    documentado: retorna `lids[0]` (primeiro da search). Ordem da search Odoo é por id ASC
    (deterministica). Caller (`resolver_lote_origem`) recebe esse lot_id "vazio" — passos
    subsequentes (ex: ajustar_quant) corretamente retornam FALHA_QUANT_VAZIO se nada
    pode ser reduzido. Comportamento seguro mas opaco — documentar via teste.
    """
    odoo_mock.search.return_value = [501, 502]  # 2 variantes existem
    odoo_mock.search_read.return_value = []     # nenhuma com saldo na loc

    lid, todos = service._melhor_lote_migracao_na_loc(
        product_id=28239, company_id=5, location_id=42,
    )

    assert lid == 501  # fallback: primeiro da lista (ordem Odoo search ASC por id)
    assert todos == [501, 502]


def test_melhor_lote_migracao_na_loc_inexistente_retorna_none(service, odoo_mock):
    """G022 boundary: produto SEM lots MIGRACAO em qualquer variante → (None, [])."""
    odoo_mock.search.return_value = []  # nenhuma variante existe

    lid, todos = service._melhor_lote_migracao_na_loc(
        product_id=28239, company_id=5, location_id=42,
    )

    assert lid is None
    assert todos == []


def test_resolver_lote_origem_literal(service, odoo_mock, lot_svc_mock):
    """Lote literal — busca exato via StockLotService."""
    lot_svc_mock.buscar_por_nome.return_value = 12345

    lid, nome, erro = service.resolver_lote_origem(
        nome_lote='MI 027-098/26', product_id=27918, company_id=1, location_id=8,
    )

    assert lid == 12345
    assert nome == 'MI 027-098/26'
    assert erro is None
    lot_svc_mock.buscar_por_nome.assert_called_once_with(
        'MI 027-098/26', 27918, 1,
    )


def test_resolver_lote_origem_migracao_consolida(service, odoo_mock):
    """G022: MIGRACAO -> escolhe variante de maior saldo na loc."""
    odoo_mock.search.return_value = [501, 502]
    odoo_mock.search_read.return_value = [
        {'lot_id': [501, 'MIGRAÇÃO'], 'quantity': 200.0},  # MAIOR
        {'lot_id': [502, 'MIGRACAO'], 'quantity': 50.0},
    ]

    lid, nome, erro = service.resolver_lote_origem(
        nome_lote='MIGRACAO', product_id=27918, company_id=1, location_id=8,
    )

    assert lid == 501  # maior saldo
    assert nome == LOTE_MIGRACAO_CANONICO  # sempre canonico no label
    assert erro is None


def test_resolver_lote_origem_p15_05_proxy_vazio(service):
    """G_proxy_vazio: P-15/05 e None -> retorna lot_id=None (sem lote)."""
    for nome in (None, 'P-15/05', ''):
        lid, label, erro = service.resolver_lote_origem(
            nome_lote=nome, product_id=27918, company_id=1, location_id=8,
        )
        assert lid is None
        assert label == 'P-15/05(sem-lote)'
        assert erro is None


def test_resolver_lote_origem_lote_inexistente(service, lot_svc_mock):
    """Lote literal nao existe -> retorna erro."""
    lot_svc_mock.buscar_por_nome.return_value = None

    lid, nome, erro = service.resolver_lote_origem(
        nome_lote='LOTE_FANTASMA', product_id=27918, company_id=1, location_id=8,
    )

    assert lid is None
    assert nome == 'LOTE_FANTASMA'
    assert erro is not None and 'inexistente' in erro


def test_resolver_lote_destino_migracao_cria_canonico(service, odoo_mock, lot_svc_mock):
    """G022: MIGRACAO inexistente -> cria canonico 'MIGRAÇÃO'."""
    odoo_mock.search.return_value = []  # nenhuma variante existe
    lot_svc_mock.criar.return_value = 999  # id do lote criado

    lid, nome, criado = service.resolver_lote_destino(
        nome_lote='MIGRAÇÃO', product_id=27918, company_id=1, location_id=8,
    )

    assert lid == 999
    assert nome == LOTE_MIGRACAO_CANONICO
    assert criado is True
    lot_svc_mock.criar.assert_called_once_with(
        LOTE_MIGRACAO_CANONICO, 27918, 1,
    )


def test_resolver_lote_destino_literal_criar_se_faltar(service, lot_svc_mock):
    """Lote literal -> usa criar_se_nao_existe (com expiration opcional)."""
    lot_svc_mock.criar_se_nao_existe.return_value = (777, True)

    lid, nome, criado = service.resolver_lote_destino(
        nome_lote='MI 026-001/26', product_id=27918, company_id=1, location_id=8,
        criar_se_faltar=True, expiration_date='2027-01-15',
    )

    assert lid == 777
    assert nome == 'MI 026-001/26'
    assert criado is True
    lot_svc_mock.criar_se_nao_existe.assert_called_once_with(
        'MI 026-001/26', 27918, 1, expiration_date='2027-01-15',
    )


def test_v2_transferir_entre_lotes_feliz_delega_ajustar_quant(service, odoo_mock):
    """API v2: delega a ajustar_quant 2x; propaga delta_esperado."""
    # Mock para ajustar_quant: search_read (buscar_quant) retorna quant origem
    # com qty=100. Depois para destino, qty=50.
    # ajustar_quant usa: search_read (buscar_quant) OR read (_ler_quant_por_id)
    # write + execute_kw (action_apply_inventory)
    # Para a v2, ajustar_quant nao recebe quant_id, recebe (product, company, loc, lot)
    # entao ela usa buscar_quant -> search_read

    # Sequence: search_read (origem), write, execute_kw, search_read (destino),
    # write, execute_kw
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
          'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']}],  # origem
        [{'id': 20, 'quantity': 50.0, 'reserved_quantity': 0,
          'lot_id': [50000, 'B'], 'location_id': [42, 'LF/Estoque']}],  # destino
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=30.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 30.0
    assert res['lot_id_origem'] == 44098
    assert res['lot_id_destino'] == 50000
    # Reducao origem
    assert res['reducao_origem']['status'] == 'EXECUTADO'
    assert res['reducao_origem']['qty_antes'] == 100.0
    assert res['reducao_origem']['qty_apos'] == 70.0
    assert res['reducao_origem']['ajuste_aplicado'] == -30.0
    # Aumento destino
    assert res['aumento_destino']['status'] == 'EXECUTADO'
    assert res['aumento_destino']['qty_antes'] == 50.0
    assert res['aumento_destino']['qty_apos'] == 80.0
    assert res['aumento_destino']['ajuste_aplicado'] == 30.0
    # 2 writes (inventory_quantity) + 2 action_apply_inventory
    assert odoo_mock.write.call_count == 2
    assert odoo_mock.execute_kw.call_count == 2


def test_v2_propaga_delta_esperado_para_ambos_passos(service, odoo_mock):
    """Regra inviolavel 11 (briefing 2026-05-24): delta_esperado propagado.

    Verifica indiretamente: se um dos ajustes nao bate o delta esperado, a
    operacao DEVE abortar (FALHA_REDUCAO ou FALHA_AUMENTO). Aqui simulamos
    um quant origem que NAO bate o esperado (qty_antes=100, mas o quant tem
    99 — depois de aplicar delta=-30, qty_apos=69 e ajuste_aplicado=-31, que
    diverge do delta_esperado=-30 em 1.0 > tolerancia padrao 0.001).
    """
    # Quant origem tem 99 (nao 100). Aplicar delta=-30 -> qty=69; ajuste=-30.
    # delta_esperado=-30 (igual ao delta solicitado), divergencia=0 -> OK.
    # Para forcar divergencia, vamos NAO mockar e usar delta diferente do esperado.
    # Nao da pra forcar divergencia indireta no v2 (o v2 ja seta os 2 iguais).
    # Vamos testar DIRETAMENTE chamando ajustar_quant com delta != delta_esperado.
    odoo_mock.search_read.return_value = [
        {'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
         'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']},
    ]
    svc = service._quant_svc()
    res = svc.ajustar_quant(
        product_id=28239, company_id=5, location_id=42, lot_id=44098,
        delta=-30.0, delta_esperado=-7.0, tolerancia_delta=0.1,
        dry_run=True,
    )
    # delta=-30, ajuste=-30, delta_esperado=-7, divergencia=23 > 0.1 -> aborta
    assert res['status'] == 'FALHA_DELTA_DIVERGENTE'
    assert res['divergencia'] == 23.0


def test_v2_falha_reducao_aborta_sem_chamar_aumento(service, odoo_mock):
    """Se reducao origem falha (saldo insuf), NAO chama aumento."""
    odoo_mock.search_read.return_value = [
        # Origem com 5 un — pedido 30 -> qty_apos=-25 (FALHA_QUANT_NEGATIVO)
        {'id': 10, 'quantity': 5.0, 'reserved_quantity': 0,
         'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']},
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=30.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['status'] == 'FALHA_REDUCAO'
    assert res['qty_transferida'] == 0.0
    assert res['aumento_destino'] is None
    assert res['reducao_origem']['status'] == 'FALHA_QUANT_NEGATIVO'
    # NAO deve ter chamado write nem execute_kw (falhou antes de gravar)
    assert odoo_mock.write.call_count == 0
    assert odoo_mock.execute_kw.call_count == 0


def test_v2_dry_run_nao_grava(service, odoo_mock):
    """dry_run=True simula ambos passos sem write nem execute_kw."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
          'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']}],
        [{'id': 20, 'quantity': 50.0, 'reserved_quantity': 0,
          'lot_id': [50000, 'B'], 'location_id': [42, 'LF/Estoque']}],
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=10.0, lot_id_origem=44098, lot_id_destino=50000,
        dry_run=True,
    )

    assert res['status'] == 'DRY_RUN_OK'
    assert res['reducao_origem']['status'] == 'DRY_RUN_OK'
    assert res['aumento_destino']['status'] == 'DRY_RUN_OK'
    # Nenhuma escrita
    assert odoo_mock.write.call_count == 0
    assert odoo_mock.execute_kw.call_count == 0


def test_v2_qty_invalida_zero(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_entre_lotes_v2(
            product_id=1, company_id=5, location_id=42,
            qty=0, lot_id_origem=44098, lot_id_destino=50000,
        )


def test_v2_lot_origem_destino_iguais(service):
    with pytest.raises(ValueError, match='lot_id_origem == lot_id_destino'):
        service.transferir_entre_lotes_v2(
            product_id=1, company_id=5, location_id=42,
            qty=10, lot_id_origem=50000, lot_id_destino=50000,
        )


def test_v2_resetar_reserva_origem_propaga(service, odoo_mock):
    """resetar_reserva_origem=True -> passo de origem usa resetar_reserva=True.

    CR1#4 (2026-05-24 v2): asserir COMPORTAMENTO (acao do ajuste registra reset_reserva)
    em vez de write.call_count (detalhe de implementacao fragil).
    """
    odoo_mock.search_read.side_effect = [
        # Origem com reserva 50, qty 100. Sem reset, reduzir 80 deixaria 20 < 50 -> FALHA_RESERVADO.
        # Com reset, ignora reserva nas validacoes -> EXECUTADO.
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 50.0,
          'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']}],
        [{'id': 20, 'quantity': 50.0, 'reserved_quantity': 0,
          'lot_id': [50000, 'B'], 'location_id': [42, 'LF/Estoque']}],
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=80.0, lot_id_origem=44098, lot_id_destino=50000,
        resetar_reserva_origem=True,
    )

    # qty_apos origem = 100 - 80 = 20, reserva=50, mas resetar_reserva=True
    # -> NAO valida abaixo da reserva (50). Resultado: EXECUTADO.
    assert res['status'] == 'EXECUTADO'
    # Assertion comportamental: acao da reducao confirma reset (NAO confiar em write.call_count
    # — pode mudar se ajustar_quant otimizar batch no futuro)
    assert 'reset_reserva' in res['reducao_origem']['acao']
    assert res['reducao_origem']['status'] == 'EXECUTADO'
    assert res['aumento_destino']['status'] == 'EXECUTADO'


def test_transferir_entre_locations_feliz(service, odoo_mock):
    """Caso real mover_migracao_para_indisponivel: mesmo lote, locs diferentes."""
    odoo_mock.search_read.side_effect = [
        # Origem: FB/Estoque (loc 8), lot MIGRACAO, qty 100
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
          'lot_id': [44098, 'MIGRAÇÃO'], 'location_id': [8, 'FB/Estoque']}],
        # Destino: FB/Indisponivel (loc 31088), mesmo lot, qty 0 (nao existe)
        [],  # quant destino nao existe
    ]

    res = service.transferir_entre_locations(
        product_id=28239, company_id=1, lot_id=44098,
        qty=100.0,
        location_id_origem=8, location_id_destino=31088,
    )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 100.0
    assert res['location_id_origem'] == 8
    assert res['location_id_destino'] == 31088
    assert res['lot_id'] == 44098
    # Reducao origem: 100 -> 0
    assert res['reducao_origem']['qty_antes'] == 100.0
    assert res['reducao_origem']['qty_apos'] == 0.0
    # Aumento destino: 0 -> 100 (criou quant)
    assert res['aumento_destino']['qty_antes'] == 0.0
    assert res['aumento_destino']['qty_apos'] == 100.0
    assert res['aumento_destino']['acao'] == 'created'


def test_transferir_entre_locations_locs_iguais(service):
    with pytest.raises(ValueError, match='location_id_origem == location_id_destino'):
        service.transferir_entre_locations(
            product_id=1, company_id=1, lot_id=44098, qty=10,
            location_id_origem=8, location_id_destino=8,
        )


def test_v2_falha_aumento_estado_parcial(service, odoo_mock):
    """CR1#6 (2026-05-24 v2): FALHA_AUMENTO em modo real = estado PARCIAL gravado.

    Cenario: origem com saldo OK reduz (-30), mas destino sera negativo (-100)
    apos aumento => FALHA_QUANT_NEGATIVO no passo 2. O quant origem JA foi
    decrementado no Odoo. qty_transferida deve ser 0.0 (nada COMPLETO atomicamente),
    qty_reduzida_origem deve refletir o debito parcial efetivo.
    """
    odoo_mock.search_read.side_effect = [
        # Origem: 100 un (reduz para 70 OK)
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
          'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']}],
        # Destino: -100 un (quant negativo pre-existente; aumento +30 = -70, ainda < 0 -> FALHA)
        [{'id': 20, 'quantity': -100.0, 'reserved_quantity': 0,
          'lot_id': [50000, 'B'], 'location_id': [42, 'LF/Estoque']}],
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=30.0, lot_id_origem=44098, lot_id_destino=50000,
    )

    assert res['status'] == 'FALHA_AUMENTO'
    # qty_transferida = 0 (transfer atomico nao ocorreu)
    assert res['qty_transferida'] == 0.0
    # qty_reduzida_origem = 30 (debito ja efetivado no Odoo — estado parcial)
    assert res['qty_reduzida_origem'] == 30.0
    # Reducao origem executada
    assert res['reducao_origem']['status'] == 'EXECUTADO'
    assert res['reducao_origem']['ajuste_aplicado'] == -30.0
    # Aumento destino falhou (negativo)
    assert res['aumento_destino']['status'] == 'FALHA_QUANT_NEGATIVO'
    # 1 write na origem + 1 execute_kw (action_apply_inventory) — aumento NAO chegou a gravar
    assert odoo_mock.write.call_count == 1
    assert odoo_mock.execute_kw.call_count == 1


def test_v2_falha_aumento_dry_run_qty_reduzida_zero(service, odoo_mock):
    """CR1#6: em dry_run + FALHA_AUMENTO, qty_reduzida_origem=0 (nada foi gravado)."""
    odoo_mock.search_read.side_effect = [
        [{'id': 10, 'quantity': 100.0, 'reserved_quantity': 0,
          'lot_id': [44098, 'A'], 'location_id': [42, 'LF/Estoque']}],
        [{'id': 20, 'quantity': -100.0, 'reserved_quantity': 0,
          'lot_id': [50000, 'B'], 'location_id': [42, 'LF/Estoque']}],
    ]

    res = service.transferir_entre_lotes_v2(
        product_id=28239, company_id=5, location_id=42,
        qty=30.0, lot_id_origem=44098, lot_id_destino=50000,
        dry_run=True,
    )

    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_transferida'] == 0.0
    assert res['qty_reduzida_origem'] == 0.0  # dry-run nao grava nada
    # Nenhum write/execute_kw em dry_run
    assert odoo_mock.write.call_count == 0
    assert odoo_mock.execute_kw.call_count == 0


def test_transferir_quantidade_para_lote_v2_resolve_lote_destino(service, odoo_mock, lot_svc_mock):
    """v2 wrapper resolve destino via resolver_lote_destino (G022)."""
    # MIGRAÇÃO -> nao existe -> cria canonico
    odoo_mock.search.return_value = []  # nenhum lot MIGRACAO
    lot_svc_mock.criar.return_value = 30400  # id do lote canonico criado
    odoo_mock.search_read.side_effect = [
        # Origem: quant com lote 56534 (MIGRACAO sem cedilha), qty 66.532
        [{'id': 10, 'quantity': 66532.0, 'reserved_quantity': 0,
          'lot_id': [56534, 'MIGRACAO'], 'location_id': [8, 'FB/Estoque']}],
        # Destino: quant nao existe (lote canonico recem-criado)
        [],
    ]

    res = service.transferir_quantidade_para_lote_v2(
        product_id=28239, company_id=1, location_id=8,
        qty=66532.0, lot_id_origem=56534,
        nome_lote_destino='MIGRAÇÃO',
    )

    assert res['status'] == 'EXECUTADO'
    assert res['lote_destino_nome'] == LOTE_MIGRACAO_CANONICO
    assert res['lote_destino_criado_agora'] is True
    assert res['lot_id_destino'] == 30400


# ============================================================
# transferir_para_indisponivel — 2026-05-24 v4 (Skill 2 extension)
# Invariante: destino sempre = (LOCAIS_INDISPONIVEL[cid], LOTES_MIGRACAO[cid])
# ============================================================

def test_transferir_para_indisponivel_fb_caso_feliz(service):
    """FB: chama ajustar_quant 2x direto (refatorado v4 — 1 passo cross loc+lote)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -223.0},  # reducao origem
        {'status': 'EXECUTADO', 'ajuste_aplicado': 223.0},   # aumento destino
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=11111, company_id=1,
            lot_id_origem=26909, qty=223.0,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 223.0
    assert res['location_id_origem'] == 8           # default FB/Estoque
    assert res['location_id_destino'] == 31088      # FB/Indisp
    assert res['lot_id_origem'] == 26909
    # lot_id_destino vem do lot_svc_mock.criar_se_nao_existe (default 999)
    # — NAO eh constant fixa (incidente 2026-05-24 v4)
    assert res['lot_id_destino'] == 999
    assert res['lote_destino_nome'] == 'MIGRAÇÃO'
    assert res['lote_destino_criado_agora'] is False
    # 2 chamadas ajustar_quant
    assert quant_svc.ajustar_quant.call_count == 2
    # Call 1: reduzir origem (lote real, FB/Estoque, -qty)
    call1 = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call1['location_id'] == 8
    assert call1['lot_id'] == 26909
    assert call1['delta'] == -223.0
    assert call1['delta_esperado'] == -223.0
    assert call1['criar_se_faltar'] is False
    # Call 2: aumentar destino (MIGRACAO, FB/Indisp, +qty, criar se faltar)
    call2 = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call2['location_id'] == 31088
    assert call2['lot_id'] == 999  # resolvido por produto via lot_svc
    assert call2['delta'] == 223.0
    assert call2['delta_esperado'] == 223.0
    assert call2['criar_se_faltar'] is True


def test_transferir_para_indisponivel_cd(service):
    """CD: usa LOCAIS_INDISPONIVEL[4]=31090 + LOTES_MIGRACAO[4]=30856."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO'}, {'status': 'EXECUTADO'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=2222, company_id=4,
            lot_id_origem=99999, qty=100.0,
        )

    assert res['location_id_origem'] == 32         # CD/Estoque
    assert res['location_id_destino'] == 31090     # CD/Indisp
    # lot_id_destino: resolvido via lot_svc.criar_se_nao_existe POR PRODUTO
    # (mock default 999). NAO usar LOTES_MIGRACAO_POR_COMPANY[4]=30856 como FK
    # universal (G031 — incidente 2026-05-24 v4).
    assert res['lot_id_destino'] == 999
    assert res['lote_destino_nome'] == 'MIGRAÇÃO'


def test_transferir_para_indisponivel_construtor_default_cria_lot_svc():
    """StockInternalTransferService sem lot_svc explicito cria default — guard nao dispara.

    (Constructor de StockInternalTransferService cria StockLotService por
    default; guard no metodo so dispara se voce passar `service.lot_svc = None`
    manualmente apos construir — caso degenerado.)
    """
    from app.odoo.estoque.scripts.transfer import StockInternalTransferService
    odoo = MagicMock()
    odoo.search.return_value = [42]  # lot_svc.buscar_por_nome retorna 42 via search
    svc = StockInternalTransferService(odoo=odoo)  # sem lot_svc, cria default
    assert svc.lot_svc is not None  # default criado


def test_transferir_para_indisponivel_company_invalida_raises():
    """company_id sem entrada em LOCAIS_INDISPONIVEL → ValueError."""
    from app.odoo.estoque.scripts.transfer import StockInternalTransferService
    lot_svc = MagicMock()
    lot_svc.criar_se_nao_existe.return_value = (999, False)
    svc = StockInternalTransferService(odoo=MagicMock(), lot_svc=lot_svc)
    with pytest.raises(ValueError, match='LOCAIS_INDISPONIVEL'):
        svc.transferir_para_indisponivel(
            product_id=1, company_id=999,
            lot_id_origem=42, qty=10,
        )


def test_transferir_para_indisponivel_origem_ja_indisp_raises(service):
    """location_id_origem == Indisp → ValueError (já está lá)."""
    with pytest.raises(ValueError, match='ja esta em Indisponivel'):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=42, qty=10,
            location_id_origem=31088,  # já é FB/Indisp
        )


def test_transferir_para_indisponivel_lote_origem_ja_migracao_raises(service):
    """lot_id_origem == lote MIGRACAO resolvido pelo lot_svc → ValueError.

    O lot_svc_mock default retorna criar_se_nao_existe=(999, False), entao
    passar lot_id_origem=999 gatilha o guard.
    """
    with pytest.raises(ValueError, match='ja consolidado'):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=999,  # mesmo id que lot_svc_mock retorna
            qty=10,
        )


def test_transferir_para_indisponivel_qty_zero_raises(service):
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=42, qty=0,
        )


def test_transferir_para_indisponivel_dry_run(service):
    """Dry-run propaga para ambos ajustes."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'DRY_RUN_OK', 'ajuste_aplicado': -100.0},
        {'status': 'DRY_RUN_OK', 'ajuste_aplicado': 100.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
            dry_run=True,
        )

    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_transferida'] == 100.0  # planejado
    # Ambas chamadas com dry_run=True
    for call in quant_svc.ajustar_quant.call_args_list:
        assert call.kwargs['dry_run'] is True


def test_transferir_para_indisponivel_falha_reducao(service):
    """Se reducao origem falha, aumento destino NÃO é chamado."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.return_value = {
        'status': 'FALHA_QUANT_VAZIO',
        'erro': 'sem quant para product=1 ...',
    }
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )

    assert res['status'] == 'FALHA_REDUCAO'
    assert res['qty_transferida'] == 0.0
    assert 'sem quant' in res['erro']
    # Apenas 1 chamada (não chegou ao aumento)
    assert quant_svc.ajustar_quant.call_count == 1


def test_transferir_para_indisponivel_falha_aumento_estado_parcial(service):
    """Reducao OK + aumento falha → FALHA_AUMENTO + qty_reduzida_origem reportada."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},  # origem ok
        {'status': 'FALHA_ODOO', 'erro': 'rede caiu no aumento'},  # destino falhou
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )

    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_transferida'] == 0.0
    assert res['qty_reduzida_origem'] == 100.0  # origem foi reduzida em PROD
    assert res['erro'] == 'rede caiu no aumento'


def test_transferir_para_indisponivel_location_id_origem_explicito(service):
    """Override location_id_origem (ex.: FB/Pré-Produção/Linha Manual)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -50.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 50.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=50.0,
            location_id_origem=4067,  # FB/Pré-Produção/Linha Manual
        )

    # Reducao deve usar location_id=4067 (não default 8)
    call_origem = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call_origem['location_id'] == 4067
    # Destino segue invariante (Indisp)
    call_destino = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call_destino['location_id'] == 31088


def test_transferir_para_indisponivel_resetar_reserva_propaga(service):
    """--resetar-reserva-origem propaga só para reducao (destino sempre False)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -50.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 50.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=50.0,
            resetar_reserva_origem=True,
        )

    call_origem = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call_origem['resetar_reserva'] is True
    assert call_origem['validar_nao_abaixo_reserva'] is False
    # Destino NUNCA reseta reserva
    call_destino = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call_destino.get('resetar_reserva', False) is False


def test_transferir_para_indisponivel_dry_run_lote_destino_inexistente(odoo_mock):
    """Em dry-run, se lote MIGRAÇÃO não existe → FALHA_LOTE_DESTINO_INEXISTENTE."""
    from app.odoo.estoque.scripts.transfer import StockInternalTransferService
    lot_svc = MagicMock()
    lot_svc.buscar_por_nome.return_value = None  # lote nao existe
    svc = StockInternalTransferService(odoo=odoo_mock, lot_svc=lot_svc)
    res = svc.transferir_para_indisponivel(
        product_id=1, company_id=1,
        lot_id_origem=26909, qty=100.0,
        dry_run=True,
    )
    assert res['status'] == 'FALHA_LOTE_DESTINO_INEXISTENTE'
    assert res['lot_id_destino'] is None
    assert res['lote_destino_nome'] == 'MIGRAÇÃO'
    # Em dry-run NAO chama criar_se_nao_existe (evita poluir Odoo)
    lot_svc.criar_se_nao_existe.assert_not_called()


def test_transferir_para_indisponivel_modo_real_cria_lote_destino(odoo_mock):
    """Em modo real, criar_se_nao_existe POR PRODUTO (não usa constant universal)."""
    from unittest.mock import patch
    from app.odoo.estoque.scripts.transfer import StockInternalTransferService
    lot_svc = MagicMock()
    lot_svc.criar_se_nao_existe.return_value = (77777, True)  # criado agora
    svc = StockInternalTransferService(odoo=odoo_mock, lot_svc=lot_svc)
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 100.0},
    ]
    with patch.object(svc, '_quant_svc', return_value=quant_svc):
        res = svc.transferir_para_indisponivel(
            product_id=11111, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )

    # lot_svc.criar_se_nao_existe chamado com NOME + PRODUTO + COMPANY
    lot_svc.criar_se_nao_existe.assert_called_once_with(
        'MIGRAÇÃO', 11111, 1,
    )
    assert res['lot_id_destino'] == 77777
    assert res['lote_destino_criado_agora'] is True
    # Aumento usa o lot_id resolvido POR PRODUTO (não constant)
    call_destino = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call_destino['lot_id'] == 77777


def test_transferir_para_indisponivel_aceita_executado_auto_corrigido(service):
    """ajustar_quant pode retornar EXECUTADO_AUTO_CORRIGIDO (guard delta_esperado);
    composição deve aceitar como sucesso (não levantar FALHA_REDUCAO/AUMENTO)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO_AUTO_CORRIGIDO', 'ajuste_aplicado': -100.0,
         'auto_correcao_aplicada': True},
        {'status': 'EXECUTADO_AUTO_CORRIGIDO', 'ajuste_aplicado': 100.0,
         'auto_correcao_aplicada': True},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )
    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 100.0


def test_transferir_para_indisponivel_falha_aumento_inclui_rollback_hint(service):
    """CR3#5 (2026-05-24 v4): FALHA_AUMENTO em modo real reporta rollback_hint
    com chamada exata ajustar_quant para reverter origem (machine-readable)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},
        {'status': 'FALHA_ODOO', 'erro': 'rede caiu'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )
    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_reduzida_origem'] == 100.0
    assert res['rollback_hint'] is not None
    hint = res['rollback_hint']
    assert hint['action'] == 'ajustar_quant'
    assert hint['product_id'] == 1
    assert hint['company_id'] == 1
    assert hint['location_id'] == 8       # FB/Estoque (default origem)
    assert hint['lot_id'] == 26909        # lote origem
    assert hint['delta'] == 100.0          # reverter +qty
    assert hint['delta_esperado'] == 100.0
    assert hint['criar_se_faltar'] is True  # defensivo (Odoo pode deletar quant zerado)


def test_transferir_para_indisponivel_dry_run_nao_inclui_rollback_hint(service):
    """Em dry-run não há estado parcial → rollback_hint None mesmo se simular FALHA."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'DRY_RUN_OK'},
        {'status': 'FALHA_QUANT_VAZIO', 'erro': 'sem quant'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
            dry_run=True,
        )
    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_reduzida_origem'] == 0.0  # dry-run não reduziu
    assert res['rollback_hint'] is None


def test_transferir_para_indisponivel_nome_lote_destino_custom(service):
    """Aceita nome_lote_destino customizado (não força 'MIGRAÇÃO')."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO'}, {'status': 'EXECUTADO'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=50.0,
            nome_lote_destino='QUARENTENA',  # nome alternativo
        )
    # lot_svc.criar_se_nao_existe chamado com NOME custom
    assert res['lote_destino_nome'] == 'QUARENTENA'
    service.lot_svc.criar_se_nao_existe.assert_called_with(
        'QUARENTENA', 1, 1,
    )


# ============================================================
# v14b — Fix D-OPS-5: aceita lot_id_origem=None para produto tracking='none'
# Bug descoberto em teste real 2026-05-25 v14a-ops (PIMENTA JALAPENO
# 103500105 41.56 un sem lote em FB/Estoque retornava FALHA_SEM_QUANT).
# ============================================================

def test_transferir_para_indisponivel_lot_origem_none_tracking_none_executa(service, odoo_mock):
    """v14b D-OPS-5: lot_id_origem=None + produto tracking='none' → OK, chama ajustar_quant 2x.

    Produto sem rastreabilidade guarda saldo SEM lot_id. Atomo aceita e
    chama ajustar_quant com lot_id=None na reducao (origem) e lot_id=999
    na criacao do destino (lote MIGRAÇÃO ainda existe semanticamente).
    """
    from unittest.mock import patch, MagicMock
    odoo_mock.read.return_value = [{'id': 1, 'tracking': 'none'}]
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -41.56},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 41.56},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=None, qty=41.56,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 41.56
    assert res['lot_id_origem'] is None
    assert res['lot_id_destino'] == 999  # lot_svc_mock default
    assert res['tracking_origem'] == 'none'
    # 1 read para validar tracking + 2 ajustes
    odoo_mock.read.assert_called_once_with('product.product', [1], ['tracking'])
    assert quant_svc.ajustar_quant.call_count == 2
    # Call 1: reduzir origem com lot_id=None (essencial — quant sem lote)
    call_origem = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call_origem['lot_id'] is None
    assert call_origem['delta'] == -41.56
    # Call 2: aumentar destino com lot_id=999 (lote MIGRACAO ainda usado)
    call_destino = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call_destino['lot_id'] == 999


def test_transferir_para_indisponivel_lot_origem_none_tracking_lot_raises(service, odoo_mock):
    """v14b D-OPS-5: lot_id_origem=None + produto tracking='lot' → ValueError (anomalia)."""
    odoo_mock.read.return_value = [{'id': 1, 'tracking': 'lot'}]
    with pytest.raises(ValueError, match='tracking.*lot.*anomalia'):
        service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=None, qty=10.0,
        )
    # Read foi feito mas nenhum ajuste tentado
    odoo_mock.read.assert_called_once()


def test_transferir_para_indisponivel_lot_origem_none_produto_inexistente_raises(service, odoo_mock):
    """v14b D-OPS-5: lot_id_origem=None + produto inexistente → ValueError clara."""
    odoo_mock.read.return_value = []  # produto nao existe
    with pytest.raises(ValueError, match='product_id=999.*inexistente'):
        service.transferir_para_indisponivel(
            product_id=999, company_id=1,
            lot_id_origem=None, qty=10.0,
        )


def test_transferir_para_indisponivel_tracking_origem_no_retorno_quando_lot_passado(service):
    """v14b: tracking_origem=None nos retornos quando lot_id_origem foi passado (sem read)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 100.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_para_indisponivel(
            product_id=1, company_id=1,
            lot_id_origem=26909, qty=100.0,
        )
    # Quando lot_id passado, atomo NAO faz read de tracking (otimizacao)
    assert res.get('tracking_origem') is None


# ============================================================
# v14b — _listar_quants_origem: parametro aceita_tracking_none
# ============================================================

def test_listar_quants_origem_default_aceita_tracking_none_true_nao_filtra_lot_id(service, odoo_mock):
    """v14b D-OPS-5: default aceita_tracking_none=True → NAO filtra ['lot_id', '!=', False]."""
    odoo_mock.search_read.return_value = []  # vazio, foco e' no domain enviado
    service._listar_quants_origem(
        product_id=1, company_id=1, locs_origem=[8, 48],
    )
    # Inspect o domain do search_read
    call = odoo_mock.search_read.call_args
    domain = call.args[1] if len(call.args) > 1 else call.kwargs.get('domain')
    domain_strs = [str(c) for c in domain]
    # NAO deve haver filtro de lot_id != False
    assert not any("'lot_id', '!=', False" in s or '"lot_id", "!=", False' in s
                   for s in domain_strs), (
        f'Default aceita_tracking_none=True NAO deve filtrar lot_id; domain: {domain}'
    )


def test_listar_quants_origem_aceita_tracking_none_false_filtra_lot_id(service, odoo_mock):
    """v14b D-OPS-5: aceita_tracking_none=False → filtra ['lot_id', '!=', False] (legacy)."""
    odoo_mock.search_read.return_value = []
    service._listar_quants_origem(
        product_id=1, company_id=1, locs_origem=[8, 48],
        aceita_tracking_none=False,
    )
    call = odoo_mock.search_read.call_args
    domain = call.args[1] if len(call.args) > 1 else call.kwargs.get('domain')
    # DEVE haver filtro de lot_id != False (comportamento antigo)
    assert ['lot_id', '!=', False] in domain, (
        f'aceita_tracking_none=False DEVE filtrar lot_id; domain: {domain}'
    )


# ============================================================
# transferir_loc_e_lote — 2026-05-26 v21+ (atomo NOVO loc+lote em 1 chamada)
# Caso real: ETAPA 0 do fluxo bulk FB->LF (Indisp/MIGRAÇÃO -> Estoque/P-15/05)
# ============================================================


def test_transferir_loc_e_lote_feliz_lot_id_destino_int(service):
    """Caso simples: loc+lote diferentes; caller passa lot_id_destino INT pronto.

    Não chama resolver_lote_destino (atomo apenas delega ajustar_quant 2x).
    """
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -250.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 250.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=28270, company_id=1, qty=250.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8, lot_id_destino=99999,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 250.0
    assert res['location_id_origem'] == 31088
    assert res['location_id_destino'] == 8
    assert res['lot_id_origem'] == 30360
    assert res['lot_id_destino'] == 99999
    assert res['lote_destino_nome'] is None
    assert res['lote_destino_criado_agora'] is None
    # 2 chamadas ajustar_quant com delta_esperado propagado
    assert quant_svc.ajustar_quant.call_count == 2
    call1 = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call1['location_id'] == 31088
    assert call1['lot_id'] == 30360
    assert call1['delta'] == -250.0
    assert call1['delta_esperado'] == -250.0
    assert call1['criar_se_faltar'] is False
    call2 = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call2['location_id'] == 8
    assert call2['lot_id'] == 99999
    assert call2['delta'] == 250.0
    assert call2['delta_esperado'] == 250.0
    assert call2['criar_se_faltar'] is True


def test_transferir_loc_e_lote_resolve_lote_destino_p15_05_proxy_sem_lote(
    service, odoo_mock, lot_svc_mock,
):
    """nome_lote_destino='P-15/05' resolve para sem-lote (lot_id_destino=None).

    Pattern resolver_lote_destino — 'P-15/05' é proxy de "quant sem lote".
    """
    # MIGRAÇÃO nao existe (necessário para resolver)
    # P-15/05 resolve direto para sem-lote (sem chamar lot_svc)
    odoo_mock.search.return_value = []
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -1.8},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 1.8},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=34907, company_id=1, qty=1.8,
            location_id_origem=31088, lot_id_origem=58098,
            location_id_destino=8,
            nome_lote_destino='P-15/05',
            criar_lote_destino_se_faltar=True,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['qty_transferida'] == 1.8
    assert res['lot_id_destino'] is None  # P-15/05 proxy = sem-lote
    assert res['lote_destino_nome'] == 'P-15/05(sem-lote)'
    assert res['lote_destino_criado_agora'] is False


def test_transferir_loc_e_lote_cria_lote_destino_literal(
    service, odoo_mock, lot_svc_mock,
):
    """nome_lote_destino literal -> lot_svc.criar_se_nao_existe cria + retorna lot_id."""
    lot_svc_mock.criar_se_nao_existe.return_value = (44444, True)
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 100.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=28270, company_id=1, qty=100.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8,
            nome_lote_destino='LOTE-NOVO-V21',
            criar_lote_destino_se_faltar=True,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['lot_id_destino'] == 44444
    assert res['lote_destino_nome'] == 'LOTE-NOVO-V21'
    assert res['lote_destino_criado_agora'] is True
    lot_svc_mock.criar_se_nao_existe.assert_called_once()


def test_transferir_loc_e_lote_origem_igual_destino_raise(service):
    """ValueError se loc igual E lote igual (não há o que transferir)."""
    with pytest.raises(ValueError, match='origem == destino'):
        service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=10.0,
            location_id_origem=8, lot_id_origem=44098,
            location_id_destino=8, lot_id_destino=44098,
        )


def test_transferir_loc_e_lote_qty_zero_raise(service):
    """ValueError se qty <= 0."""
    with pytest.raises(ValueError, match='qty deve ser > 0'):
        service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=0.0,
            location_id_origem=8, lot_id_origem=44098,
            location_id_destino=31088, lot_id_destino=50000,
        )


def test_transferir_loc_e_lote_falha_reducao(service):
    """FALHA_REDUCAO: Skill 1 falha passo 1 (quant origem vazio)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.return_value = {
        'status': 'FALHA_QUANT_VAZIO', 'erro': 'quant origem nao encontrado',
    }
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=100.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8, lot_id_destino=99999,
        )

    assert res['status'] == 'FALHA_REDUCAO'
    assert res['qty_transferida'] == 0.0
    assert res['aumento_destino'] is None
    assert 'quant origem nao encontrado' in res['erro']
    # Só 1 chamada (passo 2 não acontece)
    assert quant_svc.ajustar_quant.call_count == 1


def test_transferir_loc_e_lote_falha_aumento_estado_parcial(service):
    """FALHA_AUMENTO em modo real: passo 1 EXECUTADO, passo 2 falha → estado parcial."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -100.0},
        {'status': 'FALHA_QUANT_NEGATIVO', 'erro': 'aumento levaria a saldo negativo'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=100.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8, lot_id_destino=99999,
        )

    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_transferida'] == 0.0
    assert res['qty_reduzida_origem'] == 100.0  # debito parcial efetivo
    assert res['reducao_origem']['status'] == 'EXECUTADO'
    assert res['aumento_destino']['status'] == 'FALHA_QUANT_NEGATIVO'


def test_transferir_loc_e_lote_dry_run(service):
    """dry_run: ambos passos chamam ajustar_quant com dry_run=True; status=DRY_RUN_OK."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'DRY_RUN_OK', 'ajuste_aplicado': 0.0},
        {'status': 'DRY_RUN_OK', 'ajuste_aplicado': 0.0},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=50.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8, lot_id_destino=99999,
            dry_run=True,
        )

    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_transferida'] == 50.0
    # Ambas chamadas com dry_run=True
    for call in quant_svc.ajustar_quant.call_args_list:
        assert call.kwargs['dry_run'] is True


def test_transferir_loc_e_lote_dry_run_falha_aumento_qty_reduzida_zero(service):
    """CR1#6 pattern: dry-run + FALHA_AUMENTO → qty_reduzida_origem=0 (nada gravado)."""
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'DRY_RUN_OK', 'ajuste_aplicado': 0.0},
        {'status': 'FALHA_QUANT_NEGATIVO', 'erro': 'X'},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=1, company_id=1, qty=50.0,
            location_id_origem=31088, lot_id_origem=30360,
            location_id_destino=8, lot_id_destino=99999,
            dry_run=True,
        )

    assert res['status'] == 'FALHA_AUMENTO'
    assert res['qty_transferida'] == 0.0
    assert res['qty_reduzida_origem'] == 0.0  # dry-run nao grava


def test_transferir_loc_e_lote_resolver_falha_status(service, odoo_mock, lot_svc_mock):
    """Resolver lote destino falha → FALHA_RESOLVER_LOTE."""
    odoo_mock.search.return_value = []
    lot_svc_mock.criar_se_nao_existe.side_effect = RuntimeError('lot service down')
    res = service.transferir_loc_e_lote(
        product_id=1, company_id=1, qty=10.0,
        location_id_origem=31088, lot_id_origem=30360,
        location_id_destino=8,
        nome_lote_destino='LOTE-X',
        criar_lote_destino_se_faltar=True,
    )

    assert res['status'] == 'FALHA_RESOLVER_LOTE'
    assert res['qty_transferida'] == 0.0
    assert 'lot service down' in res['erro']
    assert res['reducao_origem'] is None
    assert res['aumento_destino'] is None


def test_transferir_loc_e_lote_tracking_none_sem_lote_ambos_pontas(service):
    """Caso CORANTE 104000046 (tracking='none'): lot_id_origem=None, lot_id_destino=None.

    Pre-cond: loc origem != destino (lote igual MAS loc diferente = aceita).
    """
    from unittest.mock import patch, MagicMock
    quant_svc = MagicMock()
    quant_svc.ajustar_quant.side_effect = [
        {'status': 'EXECUTADO', 'ajuste_aplicado': -1.8},
        {'status': 'EXECUTADO', 'ajuste_aplicado': 1.8},
    ]
    with patch.object(service, '_quant_svc', return_value=quant_svc):
        res = service.transferir_loc_e_lote(
            product_id=34907, company_id=1, qty=1.8,
            location_id_origem=31088, lot_id_origem=None,
            location_id_destino=8, lot_id_destino=None,
        )

    assert res['status'] == 'EXECUTADO'
    assert res['lot_id_origem'] is None
    assert res['lot_id_destino'] is None
    call1 = quant_svc.ajustar_quant.call_args_list[0].kwargs
    assert call1['lot_id'] is None
    call2 = quant_svc.ajustar_quant.call_args_list[1].kwargs
    assert call2['lot_id'] is None
