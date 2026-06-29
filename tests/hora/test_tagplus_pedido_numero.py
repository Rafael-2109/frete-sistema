"""Fase 1 da sync HORA<->TagPlus: numero VISIVEL do pedido (tagplus_pedido_numero).

Cobre a captura do numero visivel do pedido TagPlus (pedido['numero'] /
pedido_os_vinculada.numero) no webhook nfe_aprovada, no backfill de
enriquecimento e no backfill historico do JSONB; e a logica de exibicao.
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

from app import db as _db
from app.hora.models.tagplus import (
    HoraTagPlusConta, HoraTagPlusNfeEmissao, NFE_STATUS_ENVIADA_SEFAZ,
)
from app.hora.models.venda import HoraVenda, VENDA_STATUS_CONFIRMADO
from app.hora.services.tagplus import pedido_backfill_service
from app.hora.services.tagplus.webhook_handler import (
    WebhookHandler, _extrair_pedido_id_numero,
)


# --------------------------------------------------------------------------
# Helper puro de extracao (id, numero)
# --------------------------------------------------------------------------
def test_extrai_id_e_numero_do_pedido_vinculado():
    detalhes = {'pedido_os_vinculada': {'id': 5, 'numero': 941, 'tipo': 'P'}}
    assert _extrair_pedido_id_numero(detalhes) == (5, 941)


def test_extrai_none_quando_sem_pedido_vinculado():
    assert _extrair_pedido_id_numero({}) == (None, None)
    assert _extrair_pedido_id_numero({'pedido_os_vinculada': None}) == (None, None)
    assert _extrair_pedido_id_numero({'pedido_os_vinculada': {'id': 5}}) == (5, None)


# --------------------------------------------------------------------------
# Webhook nfe_aprovada grava o numero visivel na venda
# --------------------------------------------------------------------------
def _conta():
    c = HoraTagPlusConta(
        client_id='cid', client_secret_encrypted='x', webhook_secret='s',
    )
    _db.session.add(c)
    _db.session.flush()
    return c


def test_webhook_aprovada_grava_numero_visivel_na_venda(db):
    conta = _conta()
    venda = HoraVenda(
        cpf_cliente='12345678901', nome_cliente='Cli',
        valor_total=Decimal('100.00'), status=VENDA_STATUS_CONFIRMADO,
    )
    _db.session.add(venda)
    _db.session.flush()
    emissao = HoraTagPlusNfeEmissao(
        venda_id=venda.id, conta_id=conta.id, status=NFE_STATUS_ENVIADA_SEFAZ,
        tagplus_nfe_id=99,
    )
    _db.session.add(emissao)
    _db.session.flush()

    detalhes = {
        'numero': 1234, 'serie': 1, 'chave_acesso': '4' * 44,
        'pedido_os_vinculada': {'id': 5, 'numero': 941, 'tipo': 'P'},
    }
    with patch.object(WebhookHandler, '_buscar_detalhes', return_value=detalhes):
        WebhookHandler._handle_aprovada(emissao, client=None, tagplus_nfe_id=99)

    assert emissao.tagplus_pedido_id == 5
    assert venda.tagplus_pedido_numero == 941


# --------------------------------------------------------------------------
# Backfill de enriquecimento grava o numero a partir de GET /pedidos/{id}
# --------------------------------------------------------------------------
def test_backfill_enriquecimento_grava_numero(db, monkeypatch):
    venda = HoraVenda(
        cpf_cliente='12345678901', nome_cliente='Cli',
        valor_total=Decimal('100.00'),
    )
    _db.session.add(venda)
    _db.session.flush()

    pedido = {'id': 5, 'numero': 777, 'status': 'B'}
    monkeypatch.setattr(
        pedido_backfill_service.pedido_service, 'importar_pedido',
        lambda api, pid: pedido,
    )

    res = pedido_backfill_service._aplicar_pedido_em_venda(
        api=MagicMock(), venda=venda, pedido_id_tp=5, operador='tester',
    )

    assert res['status'] == 'enriquecida'
    assert venda.tagplus_pedido_numero == 777
