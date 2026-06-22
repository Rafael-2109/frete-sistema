"""Testes do disparo sob demanda de refresh da mv_pedidos (debounce + best-effort).

Contexto (2026-06-22): a lista_pedidos le da MV mv_pedidos, refreshed a cada ciclo
do scheduler (~30min). O `local_cd` propagado da Coleta CarVia ficava com lag de ate
1 ciclo. `solicitar_refresh_mv_pedidos` agenda um refresh assincrono, COALESCENDO
rajadas (vincular_lote de N NFs = 1 refresh) e nunca quebrando o fluxo de negocio.

Cobre a logica de debounce/best-effort SEM Redis/DB/worker reais (mocka a infra RQ).
"""
from __future__ import annotations

import types

import app.portal.workers as workers
from app.pedidos.services import mv_refresh_service as mv


class _FakeRedis:
    def __init__(self, set_result=True):
        self.set_result = set_result
        self.set_calls = []
        self.deleted = []

    def set(self, key, val, nx=False, ex=None):
        self.set_calls.append((key, nx, ex))
        return self.set_result

    def delete(self, key):
        self.deleted.append(key)
        return 1


def test_primeira_chamada_agenda_o_job(monkeypatch):
    fake = _FakeRedis(set_result=True)  # SET NX OK = ninguem agendou ainda
    enfileirados = []
    monkeypatch.setattr(workers, 'get_redis_connection', lambda: fake)
    monkeypatch.setattr(
        workers, 'enqueue_job',
        lambda func, **kw: enfileirados.append((func, kw)) or types.SimpleNamespace(id='job1'),
    )

    job = mv.solicitar_refresh_mv_pedidos()

    assert job is not None
    assert len(enfileirados) == 1
    func, kw = enfileirados[0]
    assert func is mv.refresh_mv_pedidos_job          # enfileira o job certo
    assert kw.get('queue_name') == 'default'          # fila processada pelo worker
    # Debounce gravado com NX + TTL de seguranca
    assert fake.set_calls == [(mv._FLAG_DEBOUNCE, True, mv._JANELA_DEBOUNCE_S)]


def test_debounce_nao_reagenda_na_mesma_janela(monkeypatch):
    fake = _FakeRedis(set_result=None)  # SET NX falsy = ja ha refresh agendado
    enfileirados = []
    monkeypatch.setattr(workers, 'get_redis_connection', lambda: fake)
    monkeypatch.setattr(workers, 'enqueue_job', lambda *a, **k: enfileirados.append(1))

    job = mv.solicitar_refresh_mv_pedidos()

    assert job is None
    assert enfileirados == []  # rajada coalescida: 0 novos jobs


def test_best_effort_quando_redis_indisponivel(monkeypatch):
    def boom():
        raise RuntimeError('sem redis')

    monkeypatch.setattr(workers, 'get_redis_connection', boom)

    # NUNCA propaga excecao para o fluxo de negocio (propagacao do local_cd)
    assert mv.solicitar_refresh_mv_pedidos() is None


def test_enqueue_falho_libera_a_flag_para_retry(monkeypatch):
    fake = _FakeRedis(set_result=True)

    def boom(*a, **k):
        raise RuntimeError('fila down')

    monkeypatch.setattr(workers, 'get_redis_connection', lambda: fake)
    monkeypatch.setattr(workers, 'enqueue_job', boom)

    assert mv.solicitar_refresh_mv_pedidos() is None
    # Falha no enqueue libera a flag (nao espera o TTL) p/ a proxima propagacao tentar
    assert mv._FLAG_DEBOUNCE in fake.deleted
