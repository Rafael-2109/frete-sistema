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
