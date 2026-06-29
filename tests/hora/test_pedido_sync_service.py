"""Fase 2a da sync HORA->TagPlus: pedido_sync_service (push de pedido).

Parte SEGURA: mapeamento de status, montagem de payload de identidade e os
verbos POST/PATCH atras de flag (HORA_TAGPLUS_PUSH_PEDIDO, default OFF) com
dry-run. NAO toca o caminho fiscal (to_nfe) nem o ciclo de vida da venda —
isso e Fase 2b (gated nas verificacoes de API). Testes puros (api mockada).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

import app.hora.services.tagplus.pedido_sync_service as svc


def _venda(**kw):
    base = dict(id=940, status='COTACAO', observacoes=None)
    base.update(kw)
    return SimpleNamespace(**base)


def test_mapear_status():
    assert svc.mapear_status('INCOMPLETO') == 'A'
    assert svc.mapear_status('COTACAO') == 'A'
    assert svc.mapear_status('CONFIRMADO') == 'B'
    assert svc.mapear_status('FATURADO') == 'B'
    assert svc.mapear_status('CANCELADO') == 'C'
    assert svc.mapear_status('XPTO') == 'A'


def test_montar_payload_identidade_e_status():
    p = svc.montar_payload_pedido(_venda(id=940, status='CONFIRMADO', observacoes='obs'))
    assert p['codigo_externo'] == '940'
    assert p['status'] == 'B'
    assert p['integracao'] == svc.INTEGRACAO_TAG
    assert p['observacoes'] == 'obs'


def test_push_desabilitado_por_default(monkeypatch):
    monkeypatch.delenv('HORA_TAGPLUS_PUSH_PEDIDO', raising=False)
    assert svc.push_habilitado() is False


def test_criar_pedido_dry_run_nao_chama_api():
    api = MagicMock()
    res = svc.criar_pedido(api, _venda(id=940, status='COTACAO'), dry_run=True)
    assert res['dry_run'] is True
    assert res['payload']['codigo_externo'] == '940'
    api.post.assert_not_called()


def test_criar_pedido_flag_off_mantem_dry_mesmo_com_dry_run_false():
    api = MagicMock()
    res = svc.criar_pedido(api, _venda(), dry_run=False)
    assert res['dry_run'] is True
    api.post.assert_not_called()


def test_criar_pedido_real_quando_flag_on(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    api = MagicMock()
    api.post.return_value = SimpleNamespace(status_code=201, json=lambda: {'id': 7, 'numero': 941})
    res = svc.criar_pedido(api, _venda(id=940, status='COTACAO'), dry_run=False)
    assert res['dry_run'] is False
    assert res['tagplus_pedido_id'] == 7
    assert res['tagplus_pedido_numero'] == 941
    api.post.assert_called_once()
    args, kwargs = api.post.call_args
    assert args[0] == '/pedidos'
    assert kwargs['json']['codigo_externo'] == '940'


def test_atualizar_status_real(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    api = MagicMock()
    api.patch.return_value = SimpleNamespace(status_code=200, json=lambda: {})
    res = svc.atualizar_status_pedido(api, 7, 'B', dry_run=False)
    assert res['dry_run'] is False
    assert res['status_code'] == 200
    api.patch.assert_called_once_with('/pedidos/7', json={'status': 'B'})


def test_cancelar_pedido_usa_patch_status_c(monkeypatch):
    monkeypatch.setenv('HORA_TAGPLUS_PUSH_PEDIDO', '1')
    api = MagicMock()
    api.patch.return_value = SimpleNamespace(status_code=200, json=lambda: {})
    svc.cancelar_pedido(api, 7, dry_run=False)
    api.patch.assert_called_once_with('/pedidos/7', json={'status': 'C'})


def test_scope_default_inclui_pedidos():
    from app.hora.models.tagplus import HoraTagPlusConta
    default = HoraTagPlusConta.__table__.c.scope_contratado.default.arg
    assert 'write:pedidos' in default
    assert 'read:pedidos' in default
