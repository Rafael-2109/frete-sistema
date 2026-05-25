"""Tests para `StockInternalTransferService.distribuir_para_indisponivel`.

Helper de alto nivel sobre `transferir_para_indisponivel` (modo C).
Cobre algoritmo de distribuicao greedy entre quants + politicas de ordem.

Mocka `_listar_quants_origem` e `transferir_para_indisponivel` para focar
no algoritmo de distribuicao (atomos sao testados em outro suite).

Capinagem 2026-05-25 (v10 — demanda real 158 cods FB).
"""
from unittest.mock import MagicMock, patch

import pytest

from app.odoo.estoque.scripts.transfer import (
    POLITICA_FIFO,
    POLITICA_MAIOR_SALDO,
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


def _mk_quant(qid, lot_id, lote_nome, loc_id, qty, reserved=0.0):
    """Helper para criar dict de quant retornado por _listar_quants_origem."""
    return {
        'id': qid,
        'lot_id': lot_id,
        '_lote_name': lote_nome,
        'location_id': loc_id,
        'quantity': qty,
        'reserved_quantity': reserved,
        'available': max(0.0, qty - reserved),
    }


def _mk_transfer_ok(qty):
    """Resultado DRY_RUN_OK de transferir_para_indisponivel."""
    return {
        'status': 'DRY_RUN_OK',
        'qty_transferida': qty,
        'reducao_origem': {'status': 'DRY_RUN_OK'},
        'aumento_destino_migracao': {'status': 'DRY_RUN_OK'},
        'tempo_ms': 1,
    }


def _mk_transfer_executado(qty):
    """Resultado EXECUTADO (real, nao dry-run) de transferir_para_indisponivel."""
    return {
        'status': 'EXECUTADO',
        'qty_transferida': qty,
        'reducao_origem': {'status': 'EXECUTADO'},
        'aumento_destino_migracao': {'status': 'EXECUTADO'},
        'tempo_ms': 1,
    }


# ============================================================
# Politica MIGRACAO_FIRST_FIFO + casos felizes
# ============================================================

def test_distribui_migracao_primeiro_depois_fifo(service):
    """MIGRACAO drenado antes de lotes reais; entre reais, ordem alfabetica.

    NB: 'MIGRACAO' (sem cedilha) ordena lex ANTES de 'MIGRAÇÃO' (ASCII puro
    < 'Ã'), entao o sem-cedilha vem primeiro entre as variantes MIGRACAO.
    """
    quants = [
        _mk_quant(101, 60001, '027-098/26', 8, 100),
        _mk_quant(102, 60002, 'MIGRAÇÃO', 8, 50),
        _mk_quant(103, 60003, '139/26', 8, 200),
        _mk_quant(104, 60004, 'MIGRACAO', 8, 30),  # variante sem cedilha
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.side_effect = [
            _mk_transfer_ok(30),    # MIGRACAO sem cedilha (lex menor) 30 un
            _mk_transfer_ok(50),    # MIGRAÇÃO com cedilha 50 un
            _mk_transfer_ok(100),   # 027-098/26 (FIFO depois das MIGRACAO)
            _mk_transfer_ok(20),    # 139/26 parcial 20 un
        ]
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=200, dry_run=True,
        )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_movida'] == 200
    assert res['qty_nao_movida'] == 0
    # Ordem das chamadas: MIGRACAO sem cedilha primeiro (lex 'MIGRACAO' < 'MIGRAÇÃO'),
    # depois MIGRAÇÃO com cedilha, depois 027-098/26, depois 139/26
    chamadas = mk_t.call_args_list
    assert len(chamadas) == 4
    assert chamadas[0].kwargs['lot_id_origem'] == 60004  # 'MIGRACAO' (sem cedilha)
    assert chamadas[1].kwargs['lot_id_origem'] == 60002  # 'MIGRAÇÃO' (com cedilha)
    assert chamadas[2].kwargs['lot_id_origem'] == 60001  # '027-098/26' lex antes
    assert chamadas[3].kwargs['lot_id_origem'] == 60003  # '139/26' (parcial 20 un)
    assert chamadas[3].kwargs['qty'] == 20


def test_distribui_qty_exata_em_1_lote(service):
    """qty_solicitada cabe em 1 lote — usa so esse, demais ficam intactos."""
    quants = [
        _mk_quant(101, 60001, '027-098/26', 8, 500),
        _mk_quant(102, 60002, '139/26', 8, 300),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_ok(200)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=200, dry_run=True,
        )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_movida'] == 200
    assert len(res['transferencias']) == 1  # so 1 chamada
    assert mk_t.call_count == 1


# ============================================================
# Saldo insuficiente / parciais
# ============================================================

def test_distribui_qty_maior_que_total_disponivel_parcial(service):
    """Solicita mais do que tem -> EXECUTADO_PARCIAL com qty_movida=saldo."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, 30),
        _mk_quant(102, 60002, 'B', 8, 40),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.side_effect = [_mk_transfer_ok(30), _mk_transfer_ok(40)]
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=True,
        )
    # so movemos 70 (todo o saldo); falta 30
    assert res['status'] == 'DRY_RUN_PARCIAL'
    assert res['qty_movida'] == 70
    assert res['qty_nao_movida'] == 30
    assert len(res['transferencias']) == 2


def test_distribui_sem_quants_falha(service):
    """Sem quants origem -> FALHA_SEM_QUANT (sem chamadas internas)."""
    with patch.object(service, '_listar_quants_origem', return_value=[]), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=True,
        )
    assert res['status'] == 'FALHA_SEM_QUANT'
    assert res['qty_movida'] == 0
    assert res['qty_nao_movida'] == 100
    assert mk_t.call_count == 0
    assert 'Sem quants' in res['erro']


def test_distribui_tolerar_parcial_false_falha_explicita(service):
    """tolerar_parcial=False + nao deu total -> FALHA_PARCIAL_NAO_TOLERADO."""
    quants = [_mk_quant(101, 60001, 'A', 8, 50)]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_executado(50)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=False,
            tolerar_parcial=False,
        )
    assert res['status'] == 'FALHA_PARCIAL_NAO_TOLERADO'
    assert res['qty_movida'] == 50
    assert res['qty_nao_movida'] == 50


# ============================================================
# Reserva ativa + resetar
# ============================================================

def test_distribui_respeita_reserved_quando_nao_reseta(service):
    """reserved>0 reduz qty_disponivel se resetar_reserva_origem=False (default)."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, qty=100, reserved=40),  # available=60
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_ok(60)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=True,
            resetar_reserva_origem=False,
        )
    # so 60 movidos (respeita reserva); falta 40
    assert res['status'] == 'DRY_RUN_PARCIAL'
    assert res['qty_movida'] == 60
    assert res['qty_nao_movida'] == 40
    # chamada internal usa qty=60
    assert mk_t.call_args.kwargs['qty'] == 60


def test_distribui_usa_quantity_total_quando_reseta(service):
    """resetar_reserva=True ignora reserved (usa quantity completa)."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, qty=100, reserved=40),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_ok(100)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=True,
            resetar_reserva_origem=True,
        )
    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_movida'] == 100
    # chamada usa qty_completa 100 e propaga resetar_reserva_origem=True
    assert mk_t.call_args.kwargs['qty'] == 100
    assert mk_t.call_args.kwargs['resetar_reserva_origem'] is True


def test_distribui_pula_quant_zerado_apos_reserva(service):
    """Quant 100% reservado vira available=0 e e pulado (sem chamar atomo)."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, qty=10, reserved=10),  # available=0
        _mk_quant(102, 60002, 'B', 8, qty=100),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_ok(50)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=50, dry_run=True,
        )
    assert res['status'] == 'DRY_RUN_OK'
    assert mk_t.call_count == 1  # so 1 quant utilizado
    assert mk_t.call_args.kwargs['lot_id_origem'] == 60002
    # quant pulado registrado
    assert len(res['quants_pulados']) == 1
    assert res['quants_pulados'][0]['quant_id'] == 101


# ============================================================
# Politicas alternativas
# ============================================================

def test_distribui_politica_fifo_pura(service):
    """POLITICA_FIFO ignora MIGRACAO — so ordena por nome de lote."""
    quants = [
        _mk_quant(101, 60001, 'MIGRAÇÃO', 8, 100),
        _mk_quant(102, 60002, '027-098/26', 8, 50),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.side_effect = [_mk_transfer_ok(50), _mk_transfer_ok(50)]
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=True,
            politica_ordem=POLITICA_FIFO,
        )
    # FIFO puro: '027-098/26' (lex antes) primeiro, depois MIGRAÇÃO
    chamadas = mk_t.call_args_list
    assert chamadas[0].kwargs['lot_id_origem'] == 60002  # '027-098/26'
    assert chamadas[1].kwargs['lot_id_origem'] == 60001  # 'MIGRAÇÃO'


def test_distribui_politica_maior_saldo(service):
    """POLITICA_MAIOR_SALDO drena lotes grandes primeiro."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, 50),
        _mk_quant(102, 60002, 'B', 8, 200),
        _mk_quant(103, 60003, 'C', 8, 100),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.return_value = _mk_transfer_ok(150)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=150, dry_run=True,
            politica_ordem=POLITICA_MAIOR_SALDO,
        )
    # 1a chamada = lote B (200 un) — maior saldo
    assert mk_t.call_args_list[0].kwargs['lot_id_origem'] == 60002


def test_distribui_politica_invalida_raise(service):
    """politica desconhecida -> ValueError."""
    with pytest.raises(ValueError, match='politica_ordem'):
        service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=10,
            politica_ordem='POLITICA_QUE_NAO_EXISTE',
        )


# ============================================================
# Pre-condicoes invalidas
# ============================================================

def test_distribui_qty_zero_raise(service):
    with pytest.raises(ValueError, match='qty_solicitada deve ser > 0'):
        service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=0,
        )


def test_distribui_qty_negativa_raise(service):
    with pytest.raises(ValueError, match='qty_solicitada deve ser > 0'):
        service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=-5,
        )


def test_distribui_company_sem_default_raise(service):
    """company sem entrada em LOCS_ORIGEM_INTERNAS_POR_COMPANY -> ValueError."""
    with pytest.raises(ValueError, match='sem locs default'):
        service.distribuir_para_indisponivel(
            product_id=1, company_id=999, qty_solicitada=10,
        )


def test_distribui_locs_origem_override_respeitada(service):
    """locs_origem custom eh passada para _listar_quants_origem."""
    with patch.object(service, '_listar_quants_origem', return_value=[]) as mk_l:
        service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=10,
            locs_origem=[8, 4067],  # custom: so 2 locs
        )
    assert mk_l.call_args.kwargs['locs_origem'] == [8, 4067]


# ============================================================
# Comportamento em FALHAS de transferencias internas
# ============================================================

def test_distribui_value_error_atomo_pula_quant_e_continua(service):
    """ValueError do atomo (ex.: lote origem == destino MIGRACAO) -> pula quant
    e continua greedy.

    Caso real 2026-05-25 v10 (cod 4310176): lote MIGRAÇÃO em FB/Estoque tem
    o MESMO stock.lot.id que o MIGRAÇÃO destino em FB/Indisponivel — o atomo
    `transferir_para_indisponivel` levanta ValueError pre-cond. O helper
    NAO deve quebrar o cod inteiro; deve pular esse quant e tentar outros.
    """
    quants = [
        _mk_quant(101, 30544, 'MIGRAÇÃO', 8, 1),       # caso bugado
        _mk_quant(102, 60002, '138/26', 8, 742),
        _mk_quant(103, 60003, '139/26', 8, 351),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        # 1a chamada levanta ValueError (pre-cond)
        # 2a e 3a chamadas executam OK
        mk_t.side_effect = [
            ValueError(
                'lot_id_origem == lot_id_destino MIGRACAO (30544) do '
                'produto 29716 — ja consolidado; nada a mover'
            ),
            _mk_transfer_ok(742),
            _mk_transfer_ok(351),
        ]
        res = service.distribuir_para_indisponivel(
            product_id=29716, company_id=1, qty_solicitada=1094, dry_run=True,
        )
    assert res['status'] == 'DRY_RUN_PARCIAL'
    assert res['qty_movida'] == 1093.0  # 742 + 351
    assert res['qty_nao_movida'] == 1.0
    # Quant 101 (MIGRACAO origem==destino) pulado
    assert len(res['quants_pulados']) == 1
    pulado = res['quants_pulados'][0]
    assert pulado['quant_id'] == 101
    assert pulado['lote_nome'] == 'MIGRAÇÃO'
    assert 'ValueError' in pulado['motivo']
    # Loop seguiu com os outros 2 quants -> 2 transferencias OK
    assert len(res['transferencias']) == 2


def test_distribui_falha_aumento_em_meio_continua_tentando_outros(service):
    """Se 1 transferencia falha (FALHA_AUMENTO), greedy continua nos demais."""
    quants = [
        _mk_quant(101, 60001, 'A', 8, 50),
        _mk_quant(102, 60002, 'B', 8, 80),
    ]
    falha = {
        'status': 'FALHA_AUMENTO',
        'qty_transferida': 0.0,
        'qty_reduzida_origem': 50.0,
        'erro': 'erro forjado',
        'tempo_ms': 1,
    }
    ok = _mk_transfer_executado(50)
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t:
        mk_t.side_effect = [falha, ok]
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=100, dry_run=False,
        )
    # 1a falha (qty=0 movida); 2a OK (qty=50 movida)
    # qty_falta inicia 100 -> apos falha continua 100 -> apos ok 50
    assert res['qty_movida'] == 50.0
    assert res['qty_nao_movida'] == 50.0
    assert res['status'] == 'EXECUTADO_PARCIAL'
    assert mk_t.call_count == 2
    # Transferencia 1 com status FALHA_AUMENTO presente
    assert res['transferencias'][0]['status'] == 'FALHA_AUMENTO'
    assert res['transferencias'][1]['status'] == 'EXECUTADO'
