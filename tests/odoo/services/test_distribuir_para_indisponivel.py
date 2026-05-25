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

def test_distribui_value_error_atomo_lote_destino_pula_quant_e_continua(service):
    """ValueError do atomo (lote origem inexistente em modo C) -> pula quant
    e continua greedy.

    Esse teste cobre o caso GENERICO: ValueError do atomo que NAO eh por
    `lot_id_origem == lot_id_destino` — pula sem tentar fallback Modo B.
    """
    quants = [
        _mk_quant(101, 30544, 'MIGRAÇÃO', 8, 1),       # caso fallback (testado em outro test)
        _mk_quant(102, 60002, '138/26', 8, 742),
        _mk_quant(103, 60003, '139/26', 8, 351),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b:
        # 1a chamada modo C: ValueError generico (NAO lot_id_origem==destino)
        # 2a e 3a OK
        mk_t.side_effect = [
            ValueError('algum outro erro de pre-cond do atomo'),
            _mk_transfer_ok(742),
            _mk_transfer_ok(351),
        ]
        res = service.distribuir_para_indisponivel(
            product_id=29716, company_id=1, qty_solicitada=1094, dry_run=True,
        )
    # Fallback Modo B NAO deve ter sido chamado (msg generica nao matches)
    assert mk_b.call_count == 0
    assert res['status'] == 'DRY_RUN_PARCIAL'
    assert res['qty_movida'] == 1093.0  # 742 + 351 (quant 101 pulado)
    assert res['qty_nao_movida'] == 1.0
    assert len(res['quants_pulados']) == 1
    pulado = res['quants_pulados'][0]
    assert pulado['quant_id'] == 101
    assert 'ValueError' in pulado['motivo']
    assert len(res['transferencias']) == 2


def test_distribui_fallback_modo_b_quando_lote_origem_eq_destino(service):
    """S1 v12: fallback automatico Modo B quando origem == destino MIGRACAO.

    Caso real 2026-05-25 v10/v11 (cod 4310176): quant com lote MIGRACAO em
    FB/Estoque (loc=8) — seu lot_id eh o MESMO do MIGRACAO destino em
    FB/Indisp (loc=31088), pois `stock.lot` eh por produto (G031). O modo C
    levanta `ValueError('lot_id_origem == lot_id_destino...')`. O helper
    detecta a mensagem e tenta MODO B (`transferir_entre_locations`)
    mantendo o mesmo lote — move loc=8 -> loc=31088 (Indisp) sem renomear.
    """
    quants = [
        _mk_quant(101, 30544, 'MIGRAÇÃO', 8, 1),       # caso fallback
        _mk_quant(102, 60002, '138/26', 8, 742),
        _mk_quant(103, 60003, '139/26', 8, 351),
    ]
    res_modo_b_ok = {
        'status': 'DRY_RUN_OK',
        'qty_transferida': 1.0,
        'reducao_origem': {'status': 'DRY_RUN_OK'},
        'aumento_destino': {'status': 'DRY_RUN_OK'},
        'location_id_origem': 8,
        'location_id_destino': 31088,
        'lot_id': 30544,
        'tempo_ms': 1,
    }
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b:
        mk_t.side_effect = [
            ValueError(
                'lot_id_origem == lot_id_destino MIGRACAO (30544) do '
                'produto 29716 — ja consolidado; nada a mover'
            ),
            _mk_transfer_ok(742),
            _mk_transfer_ok(351),
        ]
        mk_b.return_value = res_modo_b_ok
        res = service.distribuir_para_indisponivel(
            product_id=29716, company_id=1, qty_solicitada=1094, dry_run=True,
        )
    # Fallback Modo B foi chamado com args corretos
    assert mk_b.call_count == 1
    call_kwargs = mk_b.call_args.kwargs
    assert call_kwargs['product_id'] == 29716
    assert call_kwargs['company_id'] == 1
    assert call_kwargs['lot_id'] == 30544
    assert call_kwargs['location_id_origem'] == 8
    assert call_kwargs['location_id_destino'] == 31088  # FB/Indisp
    assert call_kwargs['qty'] == 1.0
    # Cobertura total: 1 (fallback) + 742 + 351 = 1094
    assert res['status'] == 'DRY_RUN_OK'
    assert res['qty_movida'] == 1094.0
    assert res['qty_nao_movida'] == 0.0
    # Quant 101 NAO foi pulado — foi atendido pelo fallback
    assert len(res['quants_pulados']) == 0
    # 3 transferencias registradas (1a com flag _fallback_modo_b)
    assert len(res['transferencias']) == 3
    transf_fallback = res['transferencias'][0]
    assert transf_fallback['lot_id_origem'] == 30544
    resultado_fallback = transf_fallback['resultado']
    assert resultado_fallback.get('_fallback_modo_b') is True
    assert 'fallback Modo B' in resultado_fallback.get('_fallback_motivo', '')


def test_distribui_fallback_modo_b_NAO_aplicado_se_lote_nao_eh_migracao(service):
    """S1-pre-mortem mitigation v12: deteccao DUPLA — msg match AND lote eh MIGRACAO.

    Sem o filtro semantico (lote MIGRACAO), uma mensagem 'lot_id_origem ==
    lot_id_destino' vinda de OUTRO contexto (ex.: bug futuro do atomo)
    aplicaria fallback Modo B em quant errado e moveria o produto pra Indisp
    indevidamente. Filtro adicional `is_migracao(lote_name)` impede.
    """
    quants = [
        _mk_quant(101, 60001, '139/26', 8, 10),  # LOTE REAL, NAO migracao
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b:
        # Atomo levanta mensagem com substring que casa, MAS lote NAO eh MIGRACAO
        mk_t.side_effect = ValueError(
            'lot_id_origem == lot_id_destino (mensagem fake nao-MIGRACAO)'
        )
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=10, dry_run=True,
        )
    # Fallback Modo B NAO foi tentado (lote nao eh MIGRACAO)
    assert mk_b.call_count == 0
    # Quant 101 pulado normalmente
    assert len(res['quants_pulados']) == 1
    assert 'ValueError' in res['quants_pulados'][0]['motivo']


def test_distribui_fallback_modo_b_falha_pula_quant(service):
    """S1 v12: se fallback Modo B tambem falhar (exception), pula quant com motivo composto."""
    quants = [
        _mk_quant(101, 30544, 'MIGRAÇÃO', 8, 1),
        _mk_quant(102, 60002, '138/26', 8, 1093),
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b:
        mk_t.side_effect = [
            ValueError('lot_id_origem == lot_id_destino MIGRACAO (30544)'),
            _mk_transfer_ok(1093),
        ]
        mk_b.side_effect = RuntimeError('reservada > saldo restante')
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=1094, dry_run=True,
        )
    assert mk_b.call_count == 1
    assert res['status'] == 'DRY_RUN_PARCIAL'
    assert res['qty_movida'] == 1093.0
    assert res['qty_nao_movida'] == 1.0
    assert len(res['quants_pulados']) == 1
    pulado = res['quants_pulados'][0]
    assert 'modo C + fallback Modo B falharam' in pulado['motivo']
    assert 'B (exception)' in pulado['motivo']
    assert 'reservada' in pulado['motivo']


def test_distribui_fallback_modo_b_retorna_falha_dict_pula_quant(service):
    """F1 v12-CR: Modo B retorna {'status': 'FALHA_AUMENTO'} sem exception.

    Este eh o caso critico do code-review: Modo B pode retornar dict de
    falha em vez de levantar exception. ANTES do fix, esse dict era
    tratado como sucesso (fallback_aplicado=True) e o quant aparecia em
    `transferencias` com qty_movida=0 mas o `quants_pulados` ficava vazio
    — operador nao percebe que houve estado parcial em PROD (origem JA
    reduzida, destino nao creditado).

    APOS o fix: status nao OK em res_b -> pular quant com motivo composto
    + reportar qty_reduzida_origem_modo_b.
    """
    quants = [
        _mk_quant(101, 30544, 'MIGRAÇÃO', 8, 1),
    ]
    res_b_falha = {
        'status': 'FALHA_AUMENTO',
        'qty_transferida': 0.0,
        'qty_reduzida_origem': 1.0,  # PROD: origem ja foi reduzida em 1 un
        'reducao_origem': {'status': 'EXECUTADO'},
        'aumento_destino': {'status': 'FALHA_QUANT_VAZIO'},
        'location_id_origem': 8,
        'location_id_destino': 31088,
        'lot_id': 30544,
        'erro': 'destino nao creditado por X',
        'tempo_ms': 100,
    }
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b:
        mk_t.side_effect = ValueError(
            'lot_id_origem == lot_id_destino MIGRACAO (30544)'
        )
        mk_b.return_value = res_b_falha
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=1, qty_solicitada=1, dry_run=False,
        )
    assert mk_b.call_count == 1
    # quant 101 deve estar em quants_pulados (NAO em transferencias)
    assert len(res['transferencias']) == 0
    assert len(res['quants_pulados']) == 1
    pulado = res['quants_pulados'][0]
    assert 'modo C + fallback Modo B falharam' in pulado['motivo']
    assert "'FALHA_AUMENTO'" in pulado['motivo']
    assert pulado.get('qty_reduzida_origem_modo_b') == 1.0
    # qty_movida total deve ser 0 (nada moveu)
    assert res['qty_movida'] == 0
    assert res['qty_nao_movida'] == 1
    assert res['status'] == 'EXECUTADO_PARCIAL'


def test_distribui_fallback_NAO_tentado_se_company_sem_indisp(service):
    """F4 v12-CR: company_id sem entrada em LOCAIS_INDISPONIVEL ->
    motivo distinto de erro generico do atomo C.

    Antes do fix: silencio (cai no caminho generico com motivo 'atomo
    levantou ValueError') — operador nao sabia que nao tentamos fallback.

    Apos fix: motivo distinto reporta o gap de mapeamento.
    """
    quants = [
        _mk_quant(101, 999, 'MIGRAÇÃO', 100, 1),  # lote MIGRACAO, mas company=99 (nao mapeada)
    ]
    with patch.object(service, '_listar_quants_origem', return_value=quants), \
         patch.object(service, 'transferir_para_indisponivel') as mk_t, \
         patch.object(service, 'transferir_entre_locations') as mk_b, \
         patch.object(service, '_locs_default_origem' if False else '_ordenar_quants_origem', return_value=quants):
        mk_t.side_effect = ValueError(
            'lot_id_origem == lot_id_destino MIGRACAO (999)'
        )
        # company_id=99 nao esta em LOCAIS_INDISPONIVEL (FB=1, SC=3, CD=4, LF=5)
        res = service.distribuir_para_indisponivel(
            product_id=1, company_id=99, qty_solicitada=1, dry_run=True,
            locs_origem=[100],  # custom — company 99 nao tem default
        )
    # Fallback Modo B NAO foi chamado (loc_indisp == None)
    assert mk_b.call_count == 0
    # Quant 101 pulado com motivo F4 distinto
    assert len(res['quants_pulados']) == 1
    pulado = res['quants_pulados'][0]
    assert 'sem entrada em LOCAIS_INDISPONIVEL' in pulado['motivo']
    assert 'company_id=99' in pulado['motivo']


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
